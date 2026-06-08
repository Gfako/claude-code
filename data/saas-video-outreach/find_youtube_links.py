#!/usr/bin/env python3
"""
find_youtube_links.py — Scrape homepage for YouTube channel links.

Checks each company's homepage for links to youtube.com/channel/,
youtube.com/@, youtube.com/c/, youtube.com/user/ etc.
Much cheaper than YouTube API — just HTTP requests.
"""

import re
import sqlite3
import sys
import time
import argparse
import requests
from urllib.parse import urlparse

DB_PATH = "data/saas_outreach.db"

YOUTUBE_CHANNEL_PATTERNS = [
    r'https?://(?:www\.)?youtube\.com/@[\w.-]+',
    r'https?://(?:www\.)?youtube\.com/channel/[\w-]+',
    r'https?://(?:www\.)?youtube\.com/c/[\w.-]+',
    r'https?://(?:www\.)?youtube\.com/user/[\w.-]+',
]

COMBINED_PATTERN = re.compile('|'.join(YOUTUBE_CHANNEL_PATTERNS), re.IGNORECASE)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
})


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def find_youtube_on_page(url, timeout=10):
    """Fetch a URL and extract YouTube channel links."""
    try:
        resp = SESSION.get(url, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        matches = COMBINED_PATTERN.findall(resp.text)
        # Deduplicate and clean
        seen = set()
        result = []
        for m in matches:
            clean = m.rstrip('/')
            if clean not in seen:
                seen.add(clean)
                result.append(clean)
        return result
    except Exception as e:
        return []


def run(limit=None, delay=0.5):
    conn = get_conn()
    
    # Get companies that haven't been checked and have no videos
    rows = conn.execute('''
        SELECT c.domain, c.name, c.website_url 
        FROM companies c
        WHERE c.status = 'discovered'
          AND c.has_youtube_channel = 0
          AND c.domain NOT IN (SELECT DISTINCT domain FROM company_videos)
        ORDER BY c.domain_rating DESC NULLS LAST
    ''').fetchall()
    
    companies = [dict(r) for r in rows]
    if limit:
        companies = companies[:limit]
    
    print(f"Scraping {len(companies)} homepages for YouTube links...\n")
    
    found_count = 0
    checked = 0
    errors = 0
    
    for i, comp in enumerate(companies, 1):
        domain = comp['domain']
        name = comp['name'] or domain
        url = comp['website_url'] or f'https://{domain}'
        
        if i % 100 == 0:
            print(f"  Progress: {i}/{len(companies)} (found: {found_count}, errors: {errors})")
        
        yt_links = find_youtube_on_page(url)
        checked += 1
        
        if yt_links:
            yt_url = yt_links[0]  # Take the first one
            print(f"  [{i}] {name:35s} → {yt_url}")
            
            conn.execute('''
                UPDATE companies SET 
                    has_youtube_channel = 1,
                    youtube_channel_url = ?
                WHERE domain = ?
            ''', (yt_url, domain))
            conn.commit()
            found_count += 1
        
        time.sleep(delay)
    
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"  Scraping complete!")
    print(f"  Checked:  {checked}")
    print(f"  Found:    {found_count}")
    print(f"  Errors:   {errors}")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Max companies to check")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay between requests")
    args = parser.parse_args()
    run(limit=args.limit, delay=args.delay)
