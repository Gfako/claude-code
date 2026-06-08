#!/usr/bin/env python3
"""
batch_dub.py — Batch dub all approved SaaS company videos.

Reads approved companies from data/review_decisions.json,
downloads each video, trims to the specified range, uploads to Synthesia,
starts dubbing with lip sync, polls for completion, sets visibility to public,
and saves share links back to the decisions file.

Usage:
    python3 batch_dub.py
    python3 batch_dub.py --dry-run
    python3 batch_dub.py --limit 5      # Only dub first 5
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime

import requests

# Reuse dubbing functions from the YouTube outreach project
YT_OUTREACH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Youtube outreach")
sys.path.insert(0, YT_OUTREACH)

from dub import (
    download_youtube_video, trim_video, upload_to_synthesia,
    start_dubbing, check_dubbing_status, _cleanup_temp,
)
from utils import load_config

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DECISIONS_FILE = os.path.join(DATA_DIR, "review_decisions.json")
VIDEOS_DIR = os.path.join(DATA_DIR, "videos")


def load_decisions():
    with open(DECISIONS_FILE) as f:
        return json.load(f)


def save_decisions(decisions):
    with open(DECISIONS_FILE, 'w') as f:
        json.dump(decisions, f, indent=2)


def detect_language(video_url):
    """Try to detect video language by scraping the YouTube page."""
    if 'youtube.com' not in video_url and 'youtu.be' not in video_url:
        return 'en'  # Default to English for non-YouTube

    try:
        from utils import get_http_session
        session = get_http_session()

        # Extract video ID
        m = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)', video_url)
        if not m:
            return 'en'

        vid_id = m.group(1)
        resp = session.get(f'https://www.youtube.com/watch?v={vid_id}', timeout=15)

        # Look for defaultAudioLanguage in player response
        lang_match = re.search(r'"defaultAudioLanguage"\s*:\s*"([^"]+)"', resp.text)
        if lang_match:
            return lang_match.group(1)

        # Fallback: check the page language
        lang_match = re.search(r'"lang"\s*:\s*"([^"]+)"', resp.text)
        if lang_match:
            return lang_match.group(1)
    except Exception:
        pass

    return 'en'


def determine_target_lang(source_lang):
    """English → Spanish, everything else → English."""
    if source_lang and source_lang.lower().startswith('en'):
        return 'es'
    return 'en'


def download_video(video_url, output_dir):
    """Download a YouTube or Vimeo video. Returns path or None."""
    os.makedirs(output_dir, exist_ok=True)

    # Extract video ID for filename
    m = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)', video_url)
    if m:
        vid_id = m.group(1)
    else:
        m = re.search(r'vimeo\.com/(\d+)', video_url)
        vid_id = m.group(1) if m else f"video_{int(time.time())}"

    output_template = os.path.join(output_dir, f"{vid_id}.%(ext)s")

    import yt_dlp
    ydl_opts = {
        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]/best",
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
            if not filename.endswith(".mp4"):
                filename = os.path.splitext(filename)[0] + ".mp4"

        if os.path.exists(filename):
            size_mb = os.path.getsize(filename) / (1024 * 1024)
            print(f"    Downloaded: {os.path.basename(filename)} ({size_mb:.1f} MB)")
            return filename
    except Exception as e:
        print(f"    Download failed: {e}")

    return None


def run_batch(dry_run=False, limit=None, only_domains=None):
    config = load_config()
    api_key = config['synthesia_api_key']
    if not api_key:
        print("ERROR: No SYNTHESIA_API_KEY in .env")
        sys.exit(1)

    decisions = load_decisions()
    approved = {k: v for k, v in decisions.items()
                if v.get('status') == 'approved'
                and v.get('selected_video_url')
                and not v.get('synthesia_share_link')}  # Skip already dubbed

    # Filter to specific domains if provided
    if only_domains:
        approved = {k: v for k, v in approved.items() if k in only_domains}

    if not approved:
        print("No videos to dub (all approved companies already dubbed or have no video URL).")
        return

    items = list(approved.items())
    if limit:
        items = items[:limit]

    print(f"\n  {len(items)} videos to dub:\n")
    for domain, data in items:
        src_lang = detect_language(data['selected_video_url']) if not dry_run else '?'
        tgt = determine_target_lang(src_lang) if not dry_run else '?'
        start = data.get('trim_start', 0)
        end = data.get('trim_end', 30)
        print(f"  {data.get('name','')[:35]:<36} {start // 60}:{start % 60:02d}-{end // 60}:{end % 60:02d}  {data['selected_video_url'][:50]}")

    if dry_run:
        print(f"\n  Dry run — nothing dubbed.")
        return

    print(f"\n{'='*60}")
    print(f"  Starting batch dubbing ({len(items)} videos)...")
    print(f"{'='*60}\n")

    # Phase 1: Download, trim, upload, start dubbing
    jobs = []

    for i, (domain, data) in enumerate(items):
        name = data.get('name', domain)
        video_url = data['selected_video_url']
        start = data.get('trim_start', 0)
        end = data.get('trim_end', 30)

        print(f"[{i+1}/{len(items)}] {name[:40]}")

        # Detect language
        src_lang = detect_language(video_url)
        src_lang_short = src_lang.split('-')[0]
        tgt_lang = determine_target_lang(src_lang)
        print(f"    Language: {src_lang} → {tgt_lang}")

        # Download
        video_path = download_video(video_url, VIDEOS_DIR)
        if not video_path:
            print(f"    SKIP: download failed\n")
            decisions[domain]['dub_error'] = 'download_failed'
            continue

        # Trim
        if end > start:
            trimmed_path = trim_video(video_path, start_seconds=start, end_seconds=end)
        else:
            trimmed_path = video_path

        # Upload
        asset_id = upload_to_synthesia(api_key, trimmed_path)
        if not asset_id:
            print(f"    SKIP: upload failed\n")
            _cleanup_temp(video_path)
            if trimmed_path != video_path:
                _cleanup_temp(trimmed_path)
            decisions[domain]['dub_error'] = 'upload_failed'
            continue

        # Start dubbing
        project_id = start_dubbing(
            api_key, asset_id, tgt_lang,
            source_language=src_lang_short,
            title=f"{name} — dubbed to {tgt_lang}",
            lipsync=True,
        )

        # Cleanup local files
        _cleanup_temp(video_path)
        if trimmed_path != video_path:
            _cleanup_temp(trimmed_path)

        if project_id:
            jobs.append({
                'domain': domain,
                'name': name,
                'project_id': project_id,
                'target_lang': tgt_lang,
            })
            decisions[domain]['synthesia_project_id'] = project_id
            decisions[domain]['dubbed_to'] = tgt_lang
            print(f"    Dubbing started: {project_id}\n")
        else:
            print(f"    SKIP: dubbing start failed\n")
            decisions[domain]['dub_error'] = 'dubbing_start_failed'

        # Save progress after each video
        save_decisions(decisions)

    if not jobs:
        print("No dubbing jobs started.")
        return

    # Phase 2: Poll all jobs for completion
    print(f"\n{'='*60}")
    print(f"  {len(jobs)} dubbing jobs running. Polling...")
    print(f"{'='*60}\n")

    pending = list(jobs)
    completed = []
    failed = []
    max_wait = 2400  # 40 min (lip sync is slow)
    elapsed = 0
    poll_interval = 20

    while pending and elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval

        still_pending = []
        for job in pending:
            data = check_dubbing_status(api_key, job['project_id'])
            if not data:
                still_pending.append(job)
                continue

            status = data.get('status', '').lower()
            if status == 'complete':
                assets = data.get('dubbedAssets', [])
                asset_ready = any(a.get('status') == 'complete' for a in assets)
                if asset_ready:
                    asset = next(a for a in assets if a.get('status') == 'complete')
                    asset_id = asset['id']
                    job['asset_id'] = asset_id
                    completed.append(job)
                    print(f"  ✓ {job['name'][:35]} — complete!")
                else:
                    still_pending.append(job)
            elif status == 'error':
                failed.append(job)
                error_code = data.get('errorCode', '?')
                print(f"  ✗ {job['name'][:35]} — failed: {error_code}")
                decisions[job['domain']]['dub_error'] = error_code
            else:
                still_pending.append(job)

        pending = still_pending
        if pending:
            print(f"  [{elapsed}s] {len(pending)} processing, {len(completed)} done, {len(failed)} failed")

        # Save progress periodically
        save_decisions(decisions)

    # Phase 3: Set visibility to public and get share links
    print(f"\n{'='*60}")
    print(f"  Setting visibility to public...")
    print(f"{'='*60}\n")

    for job in completed:
        asset_id = job['asset_id']
        try:
            r = requests.patch(
                f'https://api.synthesia.io/v2/videos/{asset_id}',
                headers={'Authorization': api_key, 'Content-Type': 'application/json'},
                json={'visibility': 'public'},
                timeout=30,
            )
            if r.status_code == 200:
                share_link = f"https://share.synthesia.io/{asset_id}"
                gif_url = f"https://synthesia-ttv-data.s3.amazonaws.com/video_data/{asset_id}/transfers/rendered_video.gif"
                job['share_link'] = share_link
                decisions[job['domain']]['synthesia_share_link'] = share_link
                decisions[job['domain']]['synthesia_asset_id'] = asset_id
                decisions[job['domain']]['synthesia_gif_url'] = gif_url
                print(f"  {job['name'][:35]:<36} {share_link}")
                print(f"  {'':36} GIF: {gif_url}")
            else:
                print(f"  {job['name'][:35]:<36} publish failed ({r.status_code})")
        except Exception as e:
            print(f"  {job['name'][:35]:<36} error: {e}")

        time.sleep(0.3)

    # Final save
    save_decisions(decisions)

    # Summary
    print(f"\n{'='*60}")
    print(f"  BATCH DUBBING COMPLETE")
    print(f"  Completed: {len(completed)}")
    print(f"  Failed:    {len(failed)}")
    print(f"  Timeout:   {len(pending)}")
    print(f"{'='*60}\n")

    # Export updated CSV
    _export_with_share_links(decisions)


def _export_with_share_links(decisions):
    """Export approved companies with share links to CSV."""
    import csv
    approved = {k: v for k, v in decisions.items() if v.get('status') == 'approved'}
    output_path = os.path.join(DATA_DIR, "approved_for_lusha.csv")

    fieldnames = [
        "Company Name", "Domain", "Website", "Category", "Domain Rating",
        "Organic Traffic", "Organic Keywords", "YouTube Channel",
        "Selected Video URL", "Video Source", "Page URL", "Trim Start", "Trim End",
        "Dubbed To", "Synthesia Share Link", "Synthesia GIF URL",
        "Outreach Status", "Matched Customer", "Customer Lifecycle", "Match Type",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for domain, d in sorted(approved.items(), key=lambda x: x[1].get('domain_rating') or 0, reverse=True):
            start = d.get('trim_start', 0)
            end = d.get('trim_end', 30)
            writer.writerow({
                "Company Name": d.get('name', ''),
                "Domain": domain,
                "Website": d.get('website_url', ''),
                "Category": d.get('category', ''),
                "Domain Rating": d.get('domain_rating', ''),
                "Organic Traffic": d.get('org_traffic', ''),
                "Organic Keywords": d.get('org_keywords', ''),
                "YouTube Channel": d.get('youtube_channel_url', ''),
                "Selected Video URL": d.get('selected_video_url', ''),
                "Video Source": d.get('video_source', ''),
                "Page URL": d.get('page_url', ''),
                "Trim Start": f"{start // 60}:{start % 60:02d}" if isinstance(start, int) else start,
                "Trim End": f"{end // 60}:{end % 60:02d}" if isinstance(end, int) else end,
                "Dubbed To": d.get('dubbed_to', ''),
                "Synthesia Share Link": d.get('synthesia_share_link', ''),
                "Synthesia GIF URL": d.get('synthesia_gif_url', ''),
                "Outreach Status": d.get('outreach_status', ''),
                "Matched Customer": d.get('matched_customer', ''),
                "Customer Lifecycle": d.get('customer_lifecycle', ''),
                "Match Type": d.get('match_type', ''),
            })

    print(f"Exported to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Batch dub approved SaaS company videos")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, help="Only dub first N videos")
    parser.add_argument("--domains", type=str, help="Comma-separated list of domains to dub")
    args = parser.parse_args()

    os.environ['PATH'] = os.path.expanduser('~/bin') + ':' + os.environ.get('PATH', '')
    run_batch(dry_run=args.dry_run, limit=args.limit, only_domains=args.domains.split(',') if args.domains else None)


if __name__ == "__main__":
    main()
