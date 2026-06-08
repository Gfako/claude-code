#!/usr/bin/env python3
"""
detect_video.py — Video detection for SaaS companies.

Two-tier approach:
  1. YouTube Data API — search for company's official YouTube channel
  2. Google Video Search (via search provider) — fallback for companies
     without YouTube channels, finds embedded videos on their website

Usage:
    python3 detect_video.py                    # Both tiers
    python3 detect_video.py --youtube-only     # YouTube API only
    python3 detect_video.py --google-only      # Google Video search only
    python3 detect_video.py --limit 100        # Process first N companies
"""

import argparse
import re
import sys
import time
from urllib.parse import urlparse

from googleapiclient.discovery import build as yt_build

import db
from utils import load_config, clean_domain, log

# YouTube video URL pattern
YT_VIDEO_RE = re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]{11})")
YT_CHANNEL_RE = re.compile(r"youtube\.com/(?:channel/|c/|@)([\w-]+)")


def _get_search_provider(config):
    """Get the configured search provider instance."""
    provider_name = config.get("video_detection", {}).get("search_provider", "serper")

    if provider_name == "serper":
        api_key = config.get("serper_api_key", "")
        if not api_key:
            log.warning("No serper_api_key configured. Google Video search disabled.")
            return None
        from search_serper import SerperProvider
        return SerperProvider(api_key)
    else:
        log.warning("Unknown search provider: %s", provider_name)
        return None


# ============================================================
# Tier 1: YouTube Data API
# ============================================================

def detect_youtube_channels(config, limit=None):
    """
    For each discovered company, search YouTube for their official channel.
    Verify by checking if the channel's linked website matches the company domain.
    """
    api_key = config.get("youtube_api_key", "")
    if not api_key:
        log.error("No youtube_api_key configured. Set YOUTUBE_API_KEY in .env")
        return

    youtube = yt_build("youtube", "v3", developerKey=api_key)
    yt_delay = config.get("rate_limits", {}).get("youtube_api_delay", 0.5)
    max_results = config.get("video_detection", {}).get("youtube_max_results", 5)
    recent_videos = config.get("video_detection", {}).get("youtube_recent_videos", 5)

    # Get companies that haven't been video-checked yet
    companies = db.get_companies_by_status("discovered")
    if limit:
        companies = companies[:limit]

    if not companies:
        log.info("No companies to check for YouTube channels.")
        return

    log.info("Checking %d companies for YouTube channels...", len(companies))

    found_count = 0
    checked_count = 0

    for i, comp in enumerate(companies, 1):
        domain = comp["domain"]
        name = comp["name"]

        log.info("[%d/%d] %s (%s)", i, len(companies), name, domain)

        try:
            channel = _find_youtube_channel(youtube, name, domain, max_results)
        except Exception as e:
            log.warning("  YouTube API error: %s", e)
            time.sleep(yt_delay)
            continue

        if channel:
            log.info("  Found YouTube channel: %s (%s subs)",
                     channel["title"], channel.get("subscriber_count", "?"))

            # Get recent videos
            try:
                videos = _get_channel_videos(youtube, channel["channel_id"], recent_videos)
            except Exception as e:
                log.warning("  Error fetching videos: %s", e)
                videos = []

            with db.get_conn() as conn:
                db.upsert_company(
                    domain, conn=conn,
                    has_youtube_channel=1,
                    youtube_channel_id=channel["channel_id"],
                    youtube_channel_url=channel["channel_url"],
                    youtube_subscriber_count=channel.get("subscriber_count"),
                    youtube_video_count=channel.get("video_count"),
                )
                for vid in videos:
                    db.add_video(
                        domain, "youtube_channel", vid["url"],
                        "youtube_api", conn=conn,
                        video_id=vid["video_id"], title=vid["title"],
                    )

            found_count += 1
        else:
            log.info("  No matching YouTube channel found")

        checked_count += 1
        time.sleep(yt_delay)

    log.info("YouTube channel detection complete: %d/%d found channels", found_count, checked_count)


def _find_youtube_channel(youtube, company_name, company_domain, max_results=5):
    """
    Search YouTube for a company's official channel.
    Verify by checking channel description/links for the company domain.
    """
    # Search for the company name
    search_resp = youtube.search().list(
        q=company_name,
        type="channel",
        part="snippet",
        maxResults=max_results,
    ).execute()

    for item in search_resp.get("items", []):
        channel_id = item["snippet"]["channelId"]
        channel_title = item["snippet"]["title"]

        # Get channel details to check linked website
        channel_resp = youtube.channels().list(
            id=channel_id,
            part="snippet,statistics,brandingSettings",
        ).execute()

        for ch in channel_resp.get("items", []):
            stats = ch.get("statistics", {})
            branding = ch.get("brandingSettings", {}).get("channel", {})
            description = ch.get("snippet", {}).get("description", "")

            # Check if company domain appears in channel description or keywords
            linked_domain = _extract_domain_from_channel(branding, description)

            # Only match if the channel's linked website matches the company domain.
            # Name-only matching produces too many false positives.
            if linked_domain and _domains_match(linked_domain, company_domain):
                custom_url = ch.get("snippet", {}).get("customUrl", "")
                channel_url = f"https://www.youtube.com/{custom_url}" if custom_url else f"https://www.youtube.com/channel/{channel_id}"

                return {
                    "channel_id": channel_id,
                    "title": channel_title,
                    "channel_url": channel_url,
                    "subscriber_count": _safe_int(stats.get("subscriberCount")),
                    "video_count": _safe_int(stats.get("videoCount")),
                }

    return None


def _extract_domain_from_channel(branding, description):
    """Extract website domain from channel branding settings or description."""
    # Check unsubscribedTrailer or other branding links
    # Check description for URLs
    urls = re.findall(r'https?://[^\s<>"\']+', description)
    for url in urls:
        domain = clean_domain(url)
        if domain:
            return domain

    # Check branding keywords (sometimes contains website)
    keywords = branding.get("keywords", "")
    urls = re.findall(r'https?://[^\s<>"\']+', keywords)
    for url in urls:
        domain = clean_domain(url)
        if domain:
            return domain

    return None


def _domains_match(domain1, domain2):
    """Check if two domains match (ignoring www, subdomains)."""
    if not domain1 or not domain2:
        return False
    # Extract root domain (last two parts)
    parts1 = domain1.lower().split(".")
    parts2 = domain2.lower().split(".")
    root1 = ".".join(parts1[-2:]) if len(parts1) >= 2 else domain1
    root2 = ".".join(parts2[-2:]) if len(parts2) >= 2 else domain2
    return root1 == root2


def _names_match(channel_name, company_name):
    """Check if a YouTube channel name closely matches a company name."""
    cn = channel_name.lower().strip()
    comp = company_name.lower().strip()
    # Exact match or one contains the other
    if cn == comp:
        return True
    if cn in comp or comp in cn:
        return True
    # Remove common suffixes
    for suffix in [" official", " hq", " software", " app", " inc", " ltd"]:
        cn = cn.replace(suffix, "")
        comp = comp.replace(suffix, "")
    return cn.strip() == comp.strip()


def _get_channel_videos(youtube, channel_id, max_videos=5):
    """Get recent videos from a YouTube channel."""
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


# ============================================================
# Tier 2: Google Video Search (fallback)
# ============================================================

def detect_website_videos(config, limit=None):
    """
    For companies WITHOUT a YouTube channel, search Google Video
    for videos on their actual website domain.
    """
    provider = _get_search_provider(config)
    if not provider:
        log.error("No search provider available. Configure serper_api_key in .env")
        return

    search_delay = config.get("rate_limits", {}).get("search_delay", 1.0)

    # Get companies that have been checked but have no YouTube channel
    with db.get_conn() as conn:
        rows = conn.execute("""
            SELECT domain, name, website_url FROM companies
            WHERE has_youtube_channel = 0
              AND has_website_videos = 0
              AND status = 'discovered'
            ORDER BY domain
        """).fetchall()
    companies = [dict(r) for r in rows]

    if limit:
        companies = companies[:limit]

    if not companies:
        log.info("No companies need Google Video search.")
        return

    log.info("Running Google Video search for %d companies...", len(companies))

    found_count = 0
    for i, comp in enumerate(companies, 1):
        domain = comp["domain"]
        name = comp["name"]

        log.info("[%d/%d] %s (%s)", i, len(companies), name, domain)

        # Search for videos on this company's domain
        query = f"site:{domain}"
        try:
            results = provider.video_search(query, num_results=10)
        except Exception as e:
            log.warning("  Search error: %s", e)
            time.sleep(search_delay)
            continue

        if results:
            log.info("  Found %d video results", len(results))
            video_count = 0
            platforms = set()

            with db.get_conn() as conn:
                for result in results:
                    url = result.get("url", "")
                    title = result.get("title", "")
                    video_type = _detect_video_platform(url)
                    platforms.add(video_type)

                    db.add_video(
                        domain, video_type, url,
                        "google_video_search", conn=conn,
                        page_found_on=url, title=title,
                    )
                    video_count += 1

                db.upsert_company(
                    domain, conn=conn,
                    has_website_videos=1,
                    website_video_platforms=",".join(platforms),
                    website_video_count=video_count,
                )

            found_count += 1
        else:
            log.info("  No videos found on website")

        time.sleep(search_delay)

    log.info("Google Video search complete: %d/%d companies had videos", found_count, len(companies))


def _detect_video_platform(url):
    """Detect the video platform from a URL."""
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube_embed"
    elif "vimeo.com" in url_lower:
        return "vimeo"
    elif "wistia.com" in url_lower or "wistia.net" in url_lower:
        return "wistia"
    elif "vidyard.com" in url_lower:
        return "vidyard"
    elif "loom.com" in url_lower:
        return "loom"
    return "unknown"


# ============================================================
# Combined detection
# ============================================================

def run_video_detection(config, youtube_only=False, google_only=False, limit=None):
    """Run both tiers of video detection."""
    if not google_only:
        detect_youtube_channels(config, limit=limit)

    if not youtube_only:
        detect_website_videos(config, limit=limit)

    # Update status for all checked companies
    with db.get_conn() as conn:
        conn.execute("""
            UPDATE companies
            SET status = 'video_checked', updated_at = datetime('now')
            WHERE status = 'discovered'
              AND (has_youtube_channel = 1 OR has_website_videos = 1)
        """)
        updated = conn.execute("SELECT changes()").fetchone()[0]
        log.info("Updated %d companies to 'video_checked' status", updated)


def _safe_int(val):
    try:
        return int(val) if val else None
    except (ValueError, TypeError):
        return None


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Video Detection for SaaS Companies")
    parser.add_argument("--youtube-only", action="store_true", help="Only check YouTube API")
    parser.add_argument("--google-only", action="store_true", help="Only check Google Video search")
    parser.add_argument("--limit", type=int, help="Max companies to process")
    args = parser.parse_args()

    config = load_config()
    run_video_detection(config, youtube_only=args.youtube_only,
                        google_only=args.google_only, limit=args.limit)


if __name__ == "__main__":
    main()
