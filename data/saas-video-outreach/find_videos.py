#!/usr/bin/env python3
"""
find_videos.py — Find real websites and video content for SaaS companies.

Uses Firecrawl search API to:
  1. Search "{company name} software demo video"
  2. Extract real website domain from results
  3. Detect video URLs (YouTube, Vimeo, Wistia, etc.)

Usage:
    python3 find_videos.py                # All unprocessed companies
    python3 find_videos.py --limit 100    # First N companies
    python3 find_videos.py --dry-run      # Preview without saving
"""

import argparse
import json
import re
import sys
import time
from urllib.parse import urlparse

import requests

import db
from utils import load_config, clean_domain, log

FIRECRAWL_SEARCH_URL = "https://api.firecrawl.dev/v1/search"

# Video platform patterns
VIDEO_PATTERNS = {
    "youtube_embed": re.compile(r"youtube\.com|youtu\.be", re.I),
    "vimeo": re.compile(r"vimeo\.com", re.I),
    "wistia": re.compile(r"wistia\.(com|net)", re.I),
    "vidyard": re.compile(r"vidyard\.com", re.I),
    "loom": re.compile(r"loom\.com", re.I),
}

# Words that indicate video content
VIDEO_KEYWORDS = re.compile(r"\b(demo|video|watch|webinar|tutorial|walkthrough|product tour|overview video)\b", re.I)

# Domains to skip when identifying a company's website
SKIP_DOMAINS = {
    "youtube.com", "youtu.be", "vimeo.com", "wistia.com", "wistia.net",
    "vidyard.com", "loom.com", "linkedin.com", "twitter.com", "x.com",
    "facebook.com", "instagram.com", "reddit.com", "quora.com",
    "wikipedia.org", "crunchbase.com", "g2.com", "capterra.com",
    "trustradius.com", "gartner.com", "forbes.com", "techcrunch.com",
    "bloomberg.com", "google.com", "github.com", "medium.com",
    "getapp.com", "softwareadvice.com", "trustpilot.com",
}


def _detect_video_type(url):
    """Detect video platform from URL."""
    for vtype, pattern in VIDEO_PATTERNS.items():
        if pattern.search(url):
            return vtype
    return None


def _extract_company_domain(results, company_name):
    """Extract the most likely company domain from search results."""
    company_slug = company_name.lower().replace(" ", "").replace("-", "").replace(".", "")

    for result in results:
        url = result.get("url", "")
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")

        # Skip known non-company domains
        if any(domain.endswith(skip) for skip in SKIP_DOMAINS):
            continue

        # Check if domain looks like it belongs to this company
        domain_base = domain.split(".")[0].replace("-", "")
        if (company_slug in domain_base or domain_base in company_slug
                or company_name.lower().split()[0] in domain_base):
            return domain, url

    # Fallback: first non-skip domain
    for result in results:
        url = result.get("url", "")
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")
        if domain and not any(domain.endswith(skip) for skip in SKIP_DOMAINS):
            return domain, url

    return None, None


def _extract_videos(results):
    """Extract video URLs from search results."""
    videos = []
    seen_urls = set()

    for result in results:
        url = result.get("url", "")
        title = result.get("title", "")
        description = result.get("description", "")

        if url in seen_urls:
            continue

        # Check if URL is a video platform
        vtype = _detect_video_type(url)
        if vtype:
            videos.append({
                "video_type": vtype,
                "video_url": url,
                "title": title[:200],
            })
            seen_urls.add(url)
            continue

        # Check if the result mentions video/demo content
        text = f"{title} {description}"
        if VIDEO_KEYWORDS.search(text) and "/video" in url.lower() or "/demo" in url.lower():
            videos.append({
                "video_type": "unknown",
                "video_url": url,
                "title": title[:200],
            })
            seen_urls.add(url)

    return videos


def search_company(api_key, company_name, timeout=15):
    """Search for a company's website and video content."""
    query = f'"{company_name}" software demo video'

    try:
        resp = requests.post(
            FIRECRAWL_SEARCH_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"query": query, "limit": 5},
            timeout=timeout,
        )

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 30))
            return {"rate_limited": True, "retry_after": retry_after}

        if resp.status_code != 200:
            return {"error": f"{resp.status_code}: {resp.text[:100]}"}

        data = resp.json()
        results = data.get("data", [])
        if not results:
            # Try alternate format
            results = data.get("web", [])

        return {"results": results}

    except requests.RequestException as e:
        return {"error": str(e)}


def run_video_finder(limit=None, dry_run=False):
    """Find websites and videos for all unprocessed companies."""
    config = load_config()
    api_key = config.get("firecrawl_api_key", "")
    if not api_key:
        log.error("No firecrawl_api_key configured. Set FIRECRAWL_API_KEY in .env")
        sys.exit(1)

    # Get companies that haven't been video-checked
    with db.get_conn() as conn:
        rows = conn.execute("""
            SELECT domain, name FROM companies
            WHERE has_youtube_channel = 0
              AND has_website_videos = 0
              AND status = 'discovered'
            ORDER BY name
        """).fetchall()

    companies = [dict(r) for r in rows]
    if limit:
        companies = companies[:limit]

    if not companies:
        log.info("No companies to check for videos.")
        return

    log.info("Searching for videos: %d companies...", len(companies))

    found_videos = 0
    found_website = 0
    errors = 0
    rate_limited_count = 0

    for i, comp in enumerate(companies, 1):
        name = comp["name"]
        old_domain = comp["domain"]

        if i % 50 == 0:
            log.info("  Progress: %d/%d (videos: %d, websites: %d, errors: %d)",
                     i, len(companies), found_videos, found_website, errors)

        result = search_company(api_key, name)

        if result.get("rate_limited"):
            wait = result.get("retry_after", 30)
            rate_limited_count += 1
            if rate_limited_count > 5:
                log.error("  Too many rate limits. Stopping.")
                break
            log.warning("  Rate limited. Waiting %ds...", wait)
            time.sleep(wait)
            result = search_company(api_key, name)

        if result.get("error"):
            log.debug("  [%d] %s — error: %s", i, name, result["error"])
            errors += 1
            time.sleep(1)
            continue

        results = result.get("results", [])
        if not results:
            time.sleep(0.5)
            continue

        # Extract company domain
        real_domain, website_url = _extract_company_domain(results, name)

        # Extract videos
        videos = _extract_videos(results)

        if dry_run:
            log.info("  [%d] %s → domain: %s, videos: %d",
                     i, name, real_domain or "?", len(videos))
            time.sleep(0.3)
            continue

        # Update database
        if real_domain and real_domain != old_domain:
            # Check if new domain already exists
            existing = db.get_company(real_domain)
            if existing:
                # Domain collision — just update videos on existing entry
                if videos:
                    with db.get_conn() as conn:
                        db.upsert_company(real_domain, conn=conn,
                                          has_website_videos=1,
                                          website_video_count=len(videos))
                        for v in videos:
                            db.add_video(real_domain, v["video_type"], v["video_url"],
                                         "google_video_search", conn=conn, title=v["title"])
                    found_videos += 1
                # Delete the placeholder (cascade related records)
                with db.get_conn() as conn:
                    conn.execute("DELETE FROM company_videos WHERE domain = ?", (old_domain,))
                    conn.execute("DELETE FROM contacts WHERE domain = ?", (old_domain,))
                    conn.execute("DELETE FROM discovery_sources WHERE domain = ?", (old_domain,))
                    conn.execute("DELETE FROM companies WHERE domain = ?", (old_domain,))
            else:
                # Migrate to real domain
                with db.get_conn() as conn:
                    old_data = conn.execute("SELECT * FROM companies WHERE domain = ?",
                                           (old_domain,)).fetchone()
                    if old_data:
                        # Delete old placeholder and related records
                        conn.execute("DELETE FROM company_videos WHERE domain = ?", (old_domain,))
                        conn.execute("DELETE FROM contacts WHERE domain = ?", (old_domain,))
                        conn.execute("DELETE FROM discovery_sources WHERE domain = ?", (old_domain,))
                        conn.execute("DELETE FROM companies WHERE domain = ?", (old_domain,))
                        db.upsert_company(real_domain, conn=conn,
                                          name=name,
                                          website_url=website_url or f"https://{real_domain}",
                                          category_source=dict(old_data).get("category_source", ""),
                                          has_website_videos=1 if videos else 0,
                                          website_video_count=len(videos))
                        for v in videos:
                            db.add_video(real_domain, v["video_type"], v["video_url"],
                                         "google_video_search", conn=conn, title=v["title"])
                found_website += 1
                if videos:
                    found_videos += 1
        elif videos:
            # Same domain, just add videos
            with db.get_conn() as conn:
                db.upsert_company(old_domain, conn=conn,
                                  has_website_videos=1,
                                  website_video_count=len(videos))
                for v in videos:
                    db.add_video(old_domain, v["video_type"], v["video_url"],
                                 "google_video_search", conn=conn, title=v["title"])
            found_videos += 1

        # Be gentle — 1 request per second
        time.sleep(1)

    log.info("=" * 60)
    log.info("  Video finder complete!")
    log.info("  Checked:         %d", min(i, len(companies)))
    log.info("  Websites found:  %d", found_website)
    log.info("  With videos:     %d", found_videos)
    log.info("  Errors:          %d", errors)


def main():
    parser = argparse.ArgumentParser(description="Find SaaS company websites and videos")
    parser.add_argument("--limit", type=int, help="Max companies to process")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    args = parser.parse_args()

    run_video_finder(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
