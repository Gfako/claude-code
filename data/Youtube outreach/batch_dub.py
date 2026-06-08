#!/usr/bin/env python3
"""
batch_dub.py — Batch dub all approved videos.

Downloads, trims, uploads to Synthesia, starts all dubbing jobs,
then polls them all for completion.

Usage:
    python3 batch_dub.py
    python3 batch_dub.py --dry-run    # Show what would be dubbed without doing it
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

import db
from utils import load_config, log, VIDEOS_DIR
from dub import (
    download_youtube_video, trim_video, upload_to_synthesia,
    start_dubbing, check_dubbing_status, _cleanup_temp,
)


def get_approved_videos():
    """Get all approved videos with their trim ranges."""
    with db.get_conn() as conn:
        rows = conn.execute('''
            SELECT v.video_id, v.title, v.duration_seconds, v.default_audio_language,
                   v.review_note, v.channel_id,
                   c.name as channel_name,
                   ct.website_url
            FROM videos v
            JOIN channels c ON v.channel_id = c.channel_id
            LEFT JOIN contacts ct ON c.channel_id = ct.channel_id
            WHERE v.review_status = 'approved' AND v.selected_for_dubbing = 1
            ORDER BY ct.website_dr DESC NULLS LAST
        ''').fetchall()
    return [dict(r) for r in rows]


def determine_target_lang(source_lang):
    """If English, dub to Spanish. Otherwise dub to English."""
    if source_lang and source_lang.startswith('en'):
        return 'es'
    return 'en'


def run_batch(dry_run=False):
    config = load_config()
    api_key = config['synthesia_api_key']
    if not api_key:
        log.error("No SYNTHESIA_API_KEY in .env")
        sys.exit(1)

    videos = get_approved_videos()
    if not videos:
        print("No approved videos to dub.")
        return

    print(f"\n  {len(videos)} videos to dub:\n")
    for v in videos:
        note = json.loads(v['review_note']) if v['review_note'] else {}
        start = note.get('start', 0)
        end = note.get('end', 30)
        src = v.get('default_audio_language', '?')
        tgt = determine_target_lang(src)
        print(f"  {v['channel_name'][:35]:<36} {src:>5}→{tgt}  {start//60}:{start%60:02d}-{end//60}:{end%60:02d}  {v['title'][:40]}")

    if dry_run:
        print("\n  Dry run — nothing dubbed.")
        return

    print(f"\n{'='*60}")
    print(f"  Starting batch dubbing...")
    print(f"{'='*60}\n")

    # Phase 1: Download, trim, upload, start dubbing for each video
    jobs = []  # list of {video_id, channel_name, project_id, target_lang}

    for i, v in enumerate(videos):
        note = json.loads(v['review_note']) if v['review_note'] else {}
        start = note.get('start', 0)
        end = note.get('end', 30)
        src_lang = (v.get('default_audio_language') or 'en').split('-')[0]
        tgt_lang = determine_target_lang(v.get('default_audio_language', 'en'))
        vid_id = v['video_id']

        print(f"[{i+1}/{len(videos)}] {v['channel_name'][:30]} — {v['title'][:40]}")

        # Download
        video_path = download_youtube_video(vid_id)
        if not video_path:
            log.error("  Download failed, skipping")
            continue

        # Trim
        trimmed_path = trim_video(video_path, start_seconds=start, end_seconds=end)

        # Upload
        asset_id = upload_to_synthesia(api_key, trimmed_path)
        if not asset_id:
            log.error("  Upload failed, skipping")
            _cleanup_temp(video_path)
            if trimmed_path != video_path:
                _cleanup_temp(trimmed_path)
            continue

        # Start dubbing
        project_id = start_dubbing(
            api_key, asset_id, tgt_lang,
            source_language=src_lang,
            title=f"{v['channel_name']} — {v['title'][:50]}",
            lipsync=True,
        )

        # Cleanup local files
        _cleanup_temp(video_path)
        if trimmed_path != video_path:
            _cleanup_temp(trimmed_path)

        if project_id:
            jobs.append({
                'video_id': vid_id,
                'channel_name': v['channel_name'],
                'project_id': project_id,
                'target_lang': tgt_lang,
            })
            print(f"  → Dubbing started: {project_id}\n")
        else:
            log.error("  Dubbing start failed, skipping\n")

    if not jobs:
        print("No dubbing jobs started.")
        return

    # Phase 2: Poll all jobs for completion
    print(f"\n{'='*60}")
    print(f"  {len(jobs)} dubbing jobs running. Polling for completion...")
    print(f"{'='*60}\n")

    pending = list(jobs)
    completed = []
    failed = []
    max_wait = 1800  # 30 min
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
                # Check if dubbed asset is also ready
                assets = data.get('dubbedAssets', [])
                asset_ready = any(a.get('status') == 'complete' and a.get('download') for a in assets)
                if asset_ready:
                    download_url = next(a['download'] for a in assets if a.get('status') == 'complete' and a.get('download'))
                    job['download_url'] = download_url
                    job['synthesia_id'] = next((a['id'] for a in assets if a.get('status') == 'complete'), '')
                    completed.append(job)
                    print(f"  ✓ {job['channel_name'][:30]} — complete!")
                else:
                    still_pending.append(job)  # asset still rendering
            elif status == 'error':
                failed.append(job)
                print(f"  ✗ {job['channel_name'][:30]} — failed: {data.get('errorCode', '?')}")
            else:
                still_pending.append(job)

        pending = still_pending
        if pending:
            print(f"  [{elapsed}s] {len(pending)} still processing, {len(completed)} done, {len(failed)} failed")

    # Summary
    print(f"\n{'='*60}")
    print(f"  BATCH DUBBING COMPLETE")
    print(f"  Completed: {len(completed)}")
    print(f"  Failed:    {len(failed)}")
    print(f"  Timeout:   {len(pending)}")
    print(f"{'='*60}\n")

    if completed:
        print("  Completed videos:\n")
        for job in completed:
            print(f"  {job['channel_name'][:35]:<36} {job['target_lang']}  {job['project_id']}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Batch dub all approved videos")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be dubbed")
    args = parser.parse_args()

    os.environ['PATH'] = os.path.expanduser('~/bin') + ':' + os.environ.get('PATH', '')
    run_batch(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
