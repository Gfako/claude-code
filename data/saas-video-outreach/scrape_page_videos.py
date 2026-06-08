#!/usr/bin/env python3
"""
scrape_page_videos.py — Scrape the actual website pages to find current videos.

Visits each company's website URL, extracts YouTube/Vimeo embeds,
and saves results to data/page_videos.json.

Usage:
    python3 scrape_page_videos.py
"""

import csv
import json
import os
import re
import sys
import time
import requests

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CSV_PATH = os.path.join(DATA_DIR, "saas_300_outreach_ready.csv")
OUTPUT_PATH = os.path.join(DATA_DIR, "page_videos.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def extract_videos_from_html(html):
    """Extract YouTube and Vimeo video URLs from HTML."""
    videos = []
    seen = set()

    # YouTube embeds: iframe src="https://www.youtube.com/embed/VIDEO_ID"
    for m in re.finditer(r'youtube\.com/embed/([\w-]+)', html):
        vid_id = m.group(1)
        if vid_id not in seen:
            seen.add(vid_id)
            videos.append({
                'url': f'https://www.youtube.com/watch?v={vid_id}',
                'type': 'youtube_embed',
                'video_id': vid_id,
            })

    # YouTube watch links in href or src
    for m in re.finditer(r'youtube\.com/watch\?v=([\w-]+)', html):
        vid_id = m.group(1)
        if vid_id not in seen:
            seen.add(vid_id)
            videos.append({
                'url': f'https://www.youtube.com/watch?v={vid_id}',
                'type': 'youtube_embed',
                'video_id': vid_id,
            })

    # youtu.be short links
    for m in re.finditer(r'youtu\.be/([\w-]+)', html):
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

    # Wistia - various embed patterns
    for m in re.finditer(r'wistia\.(?:com|net)/(?:medias|embed/iframe)/([\w]+)', html):
        vid_id = m.group(1)
        if vid_id not in seen:
            seen.add(vid_id)
            videos.append({
                'url': f'https://fast.wistia.net/embed/iframe/{vid_id}',
                'type': 'wistia',
                'video_id': vid_id,
            })

    # Wistia async embed: class="wistia_embed wistia_async_VIDEOID"
    for m in re.finditer(r'wistia_async_([\w]+)', html):
        vid_id = m.group(1)
        if vid_id not in seen:
            seen.add(vid_id)
            videos.append({
                'url': f'https://fast.wistia.net/embed/iframe/{vid_id}',
                'type': 'wistia',
                'video_id': vid_id,
            })

    return videos


def main():
    # Load existing results to resume
    results = {}
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH) as f:
            results = json.load(f)

    with open(CSV_PATH, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    safe_rows = [r for r in rows if r.get('Outreach Status') == 'SAFE']
    print(f"Scraping {len(safe_rows)} SAFE company pages for videos...\n")

    session = requests.Session()
    session.headers.update(HEADERS)

    scraped = 0
    found = 0
    errors = 0

    for i, r in enumerate(safe_rows):
        domain = r.get('Domain', '')
        url = r.get('Website URL', '')

        if domain in results:
            continue  # already scraped

        if not url.startswith('http'):
            continue

        print(f"  [{i+1}/{len(safe_rows)}] {r['Company Name'][:30]:<31} {url[:50]}", end="", flush=True)

        try:
            resp = session.get(url, timeout=10, allow_redirects=True)
            if resp.status_code == 200:
                videos = extract_videos_from_html(resp.text)
                results[domain] = {
                    'page_url': url,
                    'final_url': resp.url,
                    'videos': videos,
                }
                if videos:
                    found += 1
                    print(f"  → {len(videos)} video(s)")
                else:
                    print(f"  → no videos")
            else:
                results[domain] = {'page_url': url, 'error': f'HTTP {resp.status_code}', 'videos': []}
                print(f"  → HTTP {resp.status_code}")
                errors += 1
        except Exception as e:
            results[domain] = {'page_url': url, 'error': str(e)[:100], 'videos': []}
            print(f"  → error: {str(e)[:50]}")
            errors += 1

        scraped += 1

        # Save every 10 pages
        if scraped % 10 == 0:
            with open(OUTPUT_PATH, 'w') as f:
                json.dump(results, f, indent=2)

        time.sleep(1)

    # Final save
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nDone! Scraped: {scraped}, Found videos: {found}, Errors: {errors}")
    print(f"Results saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
