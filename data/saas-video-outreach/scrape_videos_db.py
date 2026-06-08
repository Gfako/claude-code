#!/usr/bin/env python3
"""
scrape_videos_db.py — Scrape company websites for embedded videos.

Reads companies from the SQLite DB, visits their website URLs,
extracts YouTube/Vimeo/Wistia embeds, and saves videos back to DB.

For YouTube embeds found on a page, optionally verifies the video's
channel belongs to the company (requires YouTube API quota).

Usage:
    python3 scrape_videos_db.py                # All unchecked companies
    python3 scrape_videos_db.py --limit 200    # First N
    python3 scrape_videos_db.py --verify-yt    # Also verify YT embed ownership
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from urllib.parse import urlparse

import requests

import db
from utils import load_config, log, clean_domain

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def extract_videos_from_html(html):
    """Extract YouTube, Vimeo, and Wistia video URLs from HTML."""
    videos = []
    seen = set()

    # YouTube embeds: iframe src="https://www.youtube.com/embed/VIDEO_ID"
    for m in re.finditer(r'youtube\.com/embed/([\w-]{11})', html):
        vid_id = m.group(1)
        if vid_id not in seen:
            seen.add(vid_id)
            videos.append({
                'url': f'https://www.youtube.com/watch?v={vid_id}',
                'type': 'youtube_embed',
                'video_id': vid_id,
            })

    # YouTube watch links
    for m in re.finditer(r'youtube\.com/watch\?v=([\w-]{11})', html):
        vid_id = m.group(1)
        if vid_id not in seen:
            seen.add(vid_id)
            videos.append({
                'url': f'https://www.youtube.com/watch?v={vid_id}',
                'type': 'youtube_embed',
                'video_id': vid_id,
            })

    # youtu.be short links
    for m in re.finditer(r'youtu\.be/([\w-]{11})', html):
        vid_id = m.group(1)
        if vid_id not in seen:
            seen.add(vid_id)
            videos.append({
                'url': f'https://www.youtube.com/watch?v={vid_id}',
                'type': 'youtube_embed',
                'video_id': vid_id,
            })

    # Vimeo embeds
    for m in re.finditer(r'player\.vimeo\.com/video/(\d+)', html):
        vid_id = m.group(1)
        if vid_id not in seen:
            seen.add(vid_id)
            videos.append({
                'url': f'https://vimeo.com/{vid_id}',
                'type': 'vimeo',
                'video_id': vid_id,
            })

    # Vimeo links
    for m in re.finditer(r'vimeo\.com/(\d{6,})', html):
        vid_id = m.group(1)
        if vid_id not in seen:
            seen.add(vid_id)
            videos.append({
                'url': f'https://vimeo.com/{vid_id}',
                'type': 'vimeo',
                'video_id': vid_id,
            })

    # Wistia embeds
    for m in re.finditer(r'wistia\.(?:com|net)/(?:medias|embed/iframe)/([\w]+)', html):
        vid_id = m.group(1)
        if vid_id not in seen:
            seen.add(vid_id)
            videos.append({
                'url': f'https://fast.wistia.net/embed/iframe/{vid_id}',
                'type': 'wistia',
                'video_id': vid_id,
            })

    # Wistia async embed
    for m in re.finditer(r'wistia_async_([\w]+)', html):
        vid_id = m.group(1)
        if vid_id not in seen:
            seen.add(vid_id)
            videos.append({
                'url': f'https://fast.wistia.net/embed/iframe/{vid_id}',
                'type': 'wistia',
                'video_id': vid_id,
            })

    # Vidyard embeds
    for m in re.finditer(r'play\.vidyard\.com/(?:embed/)?(\w+)', html):
        vid_id = m.group(1)
        if vid_id not in seen:
            seen.add(vid_id)
            videos.append({
                'url': f'https://play.vidyard.com/{vid_id}',
                'type': 'vidyard',
                'video_id': vid_id,
            })

    # Loom embeds
    for m in re.finditer(r'loom\.com/(?:share|embed)/([\w]+)', html):
        vid_id = m.group(1)
        if vid_id not in seen:
            seen.add(vid_id)
            videos.append({
                'url': f'https://www.loom.com/share/{vid_id}',
                'type': 'loom',
                'video_id': vid_id,
            })

    return videos


def verify_youtube_ownership(youtube_api, video_id, company_domain):
    """
    Check if a YouTube video belongs to the company by verifying
    the video's channel links back to the company domain.
    Returns True if verified or if we can't determine (benefit of doubt for non-YT).
    """
    try:
        from googleapiclient.discovery import build as yt_build
        # Get video details to find channel
        vid_resp = youtube_api.videos().list(
            id=video_id,
            part="snippet",
        ).execute()

        items = vid_resp.get("items", [])
        if not items:
            return False

        channel_id = items[0]["snippet"]["channelId"]

        # Get channel details
        ch_resp = youtube_api.channels().list(
            id=channel_id,
            part="snippet,brandingSettings",
        ).execute()

        for ch in ch_resp.get("items", []):
            description = ch.get("snippet", {}).get("description", "")
            branding = ch.get("brandingSettings", {}).get("channel", {})
            keywords = branding.get("keywords", "")
            check_text = f"{description} {keywords}"

            # Extract domain from company
            domain_parts = company_domain.lower().split(".")
            root_domain = ".".join(domain_parts[-2:]) if len(domain_parts) >= 2 else company_domain.lower()

            # Check URLs in channel info
            urls = re.findall(r'https?://[^\s<>"\']+', check_text)
            for url in urls:
                try:
                    parsed = urlparse(url)
                    host = parsed.hostname or ""
                    host_parts = host.lower().split(".")
                    host_root = ".".join(host_parts[-2:]) if len(host_parts) >= 2 else host.lower()
                    if host_root == root_domain:
                        return True
                except Exception:
                    continue

            # Also check if channel title matches company domain root
            channel_title = ch.get("snippet", {}).get("title", "").lower()
            domain_name = domain_parts[0] if domain_parts else ""
            if domain_name and len(domain_name) > 3 and domain_name in channel_title:
                return True

        return False
    except Exception as e:
        log.warning("    YT verify error: %s", e)
        return None  # Can't determine, skip verification


def scrape_companies(limit=None, verify_yt=False):
    """Scrape company websites for video embeds."""
    config = load_config()

    youtube_api = None
    if verify_yt:
        api_key = config.get("youtube_api_key", "")
        if api_key:
            from googleapiclient.discovery import build as yt_build
            youtube_api = yt_build("youtube", "v3", developerKey=api_key)
            log.info("YouTube ownership verification enabled")

    # Get companies that haven't been scraped for website videos
    with db.get_conn() as conn:
        rows = conn.execute("""
            SELECT domain, name, website_url FROM companies
            WHERE has_website_videos = 0
            ORDER BY domain_rating DESC NULLS LAST, name
        """).fetchall()

    companies = [dict(r) for r in rows]
    if limit:
        companies = companies[:limit]

    if not companies:
        log.info("No companies to scrape.")
        return

    log.info("Scraping %d company websites for videos...", len(companies))

    session = requests.Session()
    session.headers.update(HEADERS)

    found_count = 0
    scraped = 0
    errors = 0

    for i, comp in enumerate(companies, 1):
        domain = comp["domain"]
        name = comp["name"]
        url = comp["website_url"]

        if not url or not url.startswith("http"):
            continue

        if i % 50 == 0:
            log.info("  Progress: %d/%d (found videos: %d, errors: %d)",
                     i, len(companies), found_count, errors)

        try:
            resp = session.get(url, timeout=10, allow_redirects=True)
            if resp.status_code != 200:
                errors += 1
                continue

            videos = extract_videos_from_html(resp.text)

            if videos:
                # If verify_yt is on, filter YouTube videos by ownership
                if verify_yt and youtube_api:
                    verified_videos = []
                    for vid in videos:
                        if vid['type'] == 'youtube_embed':
                            owned = verify_youtube_ownership(youtube_api, vid['video_id'], domain)
                            if owned is False:
                                log.info("  [%d] %s — rejected YT video %s (not owned)", i, name, vid['video_id'])
                                continue
                        verified_videos.append(vid)
                    videos = verified_videos

                if videos:
                    platforms = set(v['type'] for v in videos)
                    with db.get_conn() as conn:
                        db.upsert_company(
                            domain, conn=conn,
                            has_website_videos=1,
                            website_video_platforms=",".join(platforms),
                            website_video_count=len(videos),
                        )
                        for vid in videos:
                            db.add_video(
                                domain, vid['type'], vid['url'],
                                "website_scrape", conn=conn,
                                video_id=vid.get('video_id'),
                                page_found_on=resp.url,
                            )

                    found_count += 1
                    log.info("  [%d] %s — %d video(s) [%s]",
                             i, name, len(videos), ", ".join(platforms))

        except requests.exceptions.Timeout:
            errors += 1
        except requests.exceptions.ConnectionError:
            errors += 1
        except Exception as e:
            errors += 1
            if i <= 10:  # Only log first few errors in detail
                log.warning("  [%d] %s — error: %s", i, name, str(e)[:80])

        scraped += 1
        time.sleep(0.5)  # Be polite

    log.info("=" * 60)
    log.info("  Website scraping complete!")
    log.info("  Scraped:      %d", scraped)
    log.info("  Found videos: %d", found_count)
    log.info("  Errors:       %d", errors)
    log.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Scrape company websites for videos")
    parser.add_argument("--limit", type=int, help="Max companies to scrape")
    parser.add_argument("--verify-yt", action="store_true",
                        help="Verify YouTube embed ownership via API (uses quota)")
    args = parser.parse_args()

    scrape_companies(limit=args.limit, verify_yt=args.verify_yt)


if __name__ == "__main__":
    main()
