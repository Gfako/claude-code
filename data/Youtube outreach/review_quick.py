#!/usr/bin/env python3
"""
review_quick.py — Quick video review: opens each video in browser, approve/reject from terminal.

Only shows channels that have a website. Approved videos go to the outreach spreadsheet.
Rejected videos are removed from the pipeline.

Usage:
    python3 review_quick.py              # Start reviewing
    python3 review_quick.py --skip-to N  # Skip to channel N (1-indexed)
"""

import argparse
import subprocess
import sys
import webbrowser
from collections import OrderedDict

import db
from utils import log


def get_reviewable_channels():
    """Get channels with website + pending dubbed videos, sorted by DR desc."""
    with db.get_conn() as conn:
        rows = conn.execute('''
            SELECT c.channel_id, c.name, c.subscriber_count,
                   ct.website_url, ct.website_dr, ct.website_traffic
            FROM channels c
            JOIN contacts ct ON c.channel_id = ct.channel_id
            WHERE c.has_dubbing = 1
              AND ct.website_url IS NOT NULL AND ct.website_url != ''
              AND c.channel_id IN (
                  SELECT DISTINCT channel_id FROM videos
                  WHERE has_auto_dub = 1 AND review_status = 'pending'
              )
            ORDER BY ct.website_dr DESC NULLS LAST, c.subscriber_count DESC
        ''').fetchall()
    return [dict(r) for r in rows]


def get_pending_videos(channel_id):
    """Get pending dubbed videos for a channel, shortest first."""
    with db.get_conn() as conn:
        rows = conn.execute('''
            SELECT video_id, title, duration_seconds, default_audio_language
            FROM videos
            WHERE channel_id = ? AND has_auto_dub = 1 AND review_status = 'pending'
            ORDER BY duration_seconds ASC
        ''', (channel_id,)).fetchall()
    return [dict(r) for r in rows]


def run_review(skip_to=0):
    channels = get_reviewable_channels()
    if not channels:
        print("No channels to review.")
        return

    print(f"\n  {len(channels)} channels to review (website + dubbed videos)\n")
    print("  Commands:")
    print("    a = approve this video (picks it for dubbing, moves to next channel)")
    print("    r = reject this video (shows next video from same channel)")
    print("    R = reject ALL videos for this channel (skip to next channel)")
    print("    s = skip this video (leave pending)")
    print("    q = quit\n")

    approved_count = 0
    rejected_count = 0

    for ch_idx, ch in enumerate(channels):
        if ch_idx < skip_to:
            continue

        dr = ch.get("website_dr") or 0
        traffic = ch.get("website_traffic") or 0
        videos = get_pending_videos(ch["channel_id"])
        if not videos:
            continue

        print(f"\n{'='*70}")
        print(f"  Channel {ch_idx + 1}/{len(channels)}: {ch['name']}")
        print(f"  {ch['subscriber_count']:,} subs | DR: {dr:.0f} | Traffic: {traffic:,}/mo")
        print(f"  Website: {ch['website_url']}")
        print(f"  {len(videos)} video(s) to review")
        print(f"{'='*70}")

        skip_channel = False

        for vid_idx, vid in enumerate(videos):
            if skip_channel:
                break

            duration = vid.get("duration_seconds") or 0
            mins = duration // 60
            secs = duration % 60
            lang = vid.get("default_audio_language") or "?"

            print(f"\n  [{vid_idx + 1}/{len(videos)}] \"{vid['title'][:60]}\"")
            print(f"  Duration: {mins}:{secs:02d} | Language: {lang}")

            # Open in browser
            url = f"https://www.youtube.com/watch?v={vid['video_id']}"
            webbrowser.open(url)

            # Wait for input
            while True:
                try:
                    action = input("  [a]pprove / [r]eject / [R]eject channel / [s]kip / [q]uit > ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nQuitting.")
                    _print_summary(approved_count, rejected_count)
                    return

                if action == "a":
                    db.update_video_review(vid["video_id"], "approved", selected=True)
                    _maybe_advance_channel(vid["video_id"])
                    approved_count += 1
                    # Reject remaining videos — we only need one per channel
                    for v in videos[vid_idx + 1:]:
                        db.update_video_review(v["video_id"], "rejected")
                    print(f"  ✓ Approved — moving to next channel")
                    skip_channel = True
                    break
                elif action == "r":
                    db.update_video_review(vid["video_id"], "rejected")
                    rejected_count += 1
                    print("  ✗ Rejected")
                    break
                elif action == "R":
                    # Reject all remaining videos for this channel
                    for v in videos[vid_idx:]:
                        db.update_video_review(v["video_id"], "rejected")
                        rejected_count += 1
                    print(f"  ✗ Rejected all {len(videos) - vid_idx} remaining videos")
                    skip_channel = True
                    break
                elif action == "s":
                    print("  — Skipped")
                    break
                elif action == "q":
                    print("Quitting.")
                    _print_summary(approved_count, rejected_count)
                    return
                else:
                    print("  Invalid. Use: a, r, A, R, s, q")

    _print_summary(approved_count, rejected_count)


def _maybe_advance_channel(video_id):
    """Advance channel status to approved if it has approved videos."""
    from datetime import datetime
    with db.get_conn() as conn:
        row = conn.execute("SELECT channel_id FROM videos WHERE video_id = ?", (video_id,)).fetchone()
        if not row:
            return
        ch_id = row["channel_id"]
        approved = conn.execute(
            "SELECT COUNT(*) FROM videos WHERE channel_id = ? AND review_status = 'approved'",
            (ch_id,),
        ).fetchone()[0]
        if approved > 0:
            current = conn.execute("SELECT status FROM channels WHERE channel_id = ?", (ch_id,)).fetchone()
            if current and current["status"] in ("discovered", "enriched", "reviewed"):
                conn.execute(
                    "UPDATE channels SET status = 'approved', updated_at = ? WHERE channel_id = ?",
                    (datetime.now().isoformat(), ch_id),
                )


def _print_summary(approved, rejected):
    print(f"\n{'='*40}")
    print(f"  Review summary:")
    print(f"  Approved: {approved}")
    print(f"  Rejected: {rejected}")
    print(f"{'='*40}\n")


def main():
    parser = argparse.ArgumentParser(description="Quick Video Review")
    parser.add_argument("--skip-to", type=int, default=0, help="Skip to channel N (0-indexed)")
    args = parser.parse_args()
    run_review(skip_to=args.skip_to)


if __name__ == "__main__":
    main()
