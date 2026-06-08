#!/usr/bin/env python3
"""
detect_youtube.py — Find YouTube channels for SaaS companies.

Searches YouTube by company name, gets channel details (subscribers, video count),
and stores recent videos. Does NOT need the company's website URL — just the name.

Usage:
    python3 detect_youtube.py                # All companies
    python3 detect_youtube.py --limit 100    # First N companies
    python3 detect_youtube.py --min-subs 100 # Skip tiny channels
"""

import argparse
import sys
import time
from datetime import datetime

from googleapiclient.discovery import build as yt_build
from googleapiclient.errors import HttpError

import db
from utils import load_config, log


def run_youtube_detection(config, limit=None, min_subs=100):
    """Search YouTube for each company's official channel."""
    api_key = config.get("youtube_api_key", "")
    if not api_key:
        log.error("No youtube_api_key configured. Set YOUTUBE_API_KEY in .env")
        sys.exit(1)

    youtube = yt_build("youtube", "v3", developerKey=api_key)
    delay = config.get("rate_limits", {}).get("youtube_api_delay", 0.5)
    max_videos = config.get("video_detection", {}).get("youtube_recent_videos", 5)

    # Get companies that haven't been checked yet
    with db.get_conn() as conn:
        rows = conn.execute("""
            SELECT domain, name FROM companies
            WHERE has_youtube_channel = 0
              AND status = 'discovered'
            ORDER BY name
        """).fetchall()

    companies = [dict(r) for r in rows]
    if limit:
        companies = companies[:limit]

    if not companies:
        log.info("No companies to check.")
        return

    log.info("Searching YouTube for %d companies (min subs: %d)...", len(companies), min_subs)

    found_count = 0
    checked = 0
    errors = 0

    for i, comp in enumerate(companies, 1):
        name = comp["name"]
        domain = comp["domain"]

        if i % 100 == 0:
            log.info("  Progress: %d/%d (found: %d, errors: %d)",
                     i, len(companies), found_count, errors)

        try:
            channel = _find_channel(youtube, name, domain, min_subs)
        except HttpError as e:
            if "quotaExceeded" in str(e):
                log.error("YouTube API quota exceeded at company %d/%d. Resume tomorrow.", i, len(companies))
                break
            log.warning("  [%d] %s — API error: %s", i, name, e)
            errors += 1
            time.sleep(delay)
            continue
        except Exception as e:
            log.warning("  [%d] %s — error: %s", i, name, e)
            errors += 1
            time.sleep(delay)
            continue

        if channel:
            log.info("  [%d] %s → %s (%s subs, %s videos)",
                     i, name, channel["title"],
                     f"{channel['subscriber_count']:,}" if channel['subscriber_count'] else "?",
                     channel.get("video_count", "?"))

            # Get recent videos
            try:
                videos = _get_recent_videos(youtube, channel["channel_id"], max_videos)
            except Exception:
                videos = []

            with db.get_conn() as conn:
                db.upsert_company(
                    domain, conn=conn,
                    has_youtube_channel=1,
                    youtube_channel_id=channel["channel_id"],
                    youtube_channel_url=channel["channel_url"],
                    youtube_subscriber_count=channel["subscriber_count"],
                    youtube_video_count=channel["video_count"],
                )
                for vid in videos:
                    db.add_video(
                        domain, "youtube_channel", vid["url"],
                        "youtube_api", conn=conn,
                        video_id=vid["video_id"], title=vid["title"],
                    )

            found_count += 1

        checked += 1
        time.sleep(delay)

    log.info("=" * 60)
    log.info("  YouTube detection complete!")
    log.info("  Checked:  %d", checked)
    log.info("  Found:    %d", found_count)
    log.info("  Errors:   %d", errors)


def _find_channel(youtube, company_name, company_domain, min_subs=100):
    """
    Search YouTube for a company's channel.
    Requires domain verification — the channel's linked website or description
    must contain the company domain. Name-only matching is too unreliable.
    Returns channel dict or None.
    """
    import re
    # Search for channels matching the company name
    search_resp = youtube.search().list(
        q=company_name,
        type="channel",
        part="snippet",
        maxResults=5,
    ).execute()

    candidates = []
    for item in search_resp.get("items", []):
        channel_id = item["snippet"]["channelId"]
        channel_title = item["snippet"]["title"]

        # Quick name match filter — channel title should resemble the company name
        if not _name_matches(channel_title, company_name):
            continue

        candidates.append(channel_id)

    if not candidates:
        return None

    # Get details for matching candidates — include brandingSettings for domain check
    details_resp = youtube.channels().list(
        id=",".join(candidates[:3]),
        part="snippet,statistics,brandingSettings",
    ).execute()

    best = None
    best_subs = 0

    # Extract root domain for comparison
    domain_parts = company_domain.lower().split(".")
    root_domain = ".".join(domain_parts[-2:]) if len(domain_parts) >= 2 else company_domain.lower()

    for ch in details_resp.get("items", []):
        stats = ch.get("statistics", {})
        subs = _safe_int(stats.get("subscriberCount", 0))
        video_count = _safe_int(stats.get("videoCount", 0))

        # Must meet minimum subscribers
        if subs < min_subs:
            continue

        # Must have at least a few videos
        if video_count < 3:
            continue

        # Domain verification: check description and branding for company domain
        description = ch.get("snippet", {}).get("description", "")
        branding = ch.get("brandingSettings", {}).get("channel", {})
        keywords = branding.get("keywords", "")
        check_text = f"{description} {keywords}"

        # Extract all URLs from the channel text
        urls = re.findall(r'https?://[^\s<>"\']+', check_text)
        domain_matched = False
        for url in urls:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                host = parsed.hostname or ""
                host_parts = host.lower().split(".")
                host_root = ".".join(host_parts[-2:]) if len(host_parts) >= 2 else host.lower()
                if host_root == root_domain:
                    domain_matched = True
                    break
            except Exception:
                continue

        if not domain_matched:
            continue

        # Pick the one with most subscribers
        if subs > best_subs:
            custom_url = ch.get("snippet", {}).get("customUrl", "")
            channel_url = (f"https://www.youtube.com/{custom_url}" if custom_url
                          else f"https://www.youtube.com/channel/{ch['id']}")

            best = {
                "channel_id": ch["id"],
                "title": ch["snippet"]["title"],
                "channel_url": channel_url,
                "subscriber_count": subs,
                "video_count": video_count,
            }
            best_subs = subs

    return best


def _name_matches(channel_title, company_name):
    """Check if channel title plausibly matches the company name."""
    ct = channel_title.lower().strip()
    cn = company_name.lower().strip()

    # Exact match
    if ct == cn:
        return True

    # One contains the other
    if cn in ct or ct in cn:
        return True

    # Remove common suffixes and compare
    for suffix in [" official", " hq", " software", " app", " inc", " ltd",
                   " platform", " cloud", " labs", " ai", " io"]:
        ct = ct.replace(suffix, "")
        cn = cn.replace(suffix, "")

    if ct.strip() == cn.strip():
        return True

    # First word matches (for multi-word names)
    ct_first = ct.split()[0] if ct.split() else ""
    cn_first = cn.split()[0] if cn.split() else ""
    if ct_first and cn_first and ct_first == cn_first and len(ct_first) > 3:
        return True

    return False


def _get_recent_videos(youtube, channel_id, max_videos=5):
    """Get recent videos from a channel."""
    search_resp = youtube.search().list(
        channelId=channel_id,
        type="video",
        part="snippet",
        order="date",
        maxResults=max_videos,
    ).execute()

    videos = []
    for item in search_resp.get("items", []):
        video_id = item["id"]["videoId"]
        videos.append({
            "video_id": video_id,
            "title": item["snippet"]["title"],
            "url": f"https://www.youtube.com/watch?v={video_id}",
        })
    return videos


def _safe_int(val):
    try:
        return int(val) if val else 0
    except (ValueError, TypeError):
        return 0


def main():
    parser = argparse.ArgumentParser(description="YouTube Channel Detection")
    parser.add_argument("--limit", type=int, help="Max companies to check")
    parser.add_argument("--min-subs", type=int, default=100, help="Minimum subscriber count")
    args = parser.parse_args()

    config = load_config()
    run_youtube_detection(config, limit=args.limit, min_subs=args.min_subs)


if __name__ == "__main__":
    main()
