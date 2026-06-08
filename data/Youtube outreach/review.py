#!/usr/bin/env python3
"""
review.py — Video Review Workflow

Lets you approve/reject/select dubbed videos before sending them
to Synthesia for dubbing. This is the gate between discovery and
dubbing — only approved + selected videos get dubbed.

Interactive mode:
    python3 review.py                      # Interactive review
    python3 review.py --list               # List all pending videos

Non-interactive:
    python3 review.py --approve-all        # Approve + select all pending
    python3 review.py --approve VIDEO_ID   # Approve a specific video
    python3 review.py --reject VIDEO_ID    # Reject a specific video
    python3 review.py --select VIDEO_ID    # Mark video for dubbing
"""

import argparse
from collections import defaultdict
from datetime import datetime

import db
from utils import log


# ============================================================
# Listing
# ============================================================

def list_pending():
    """List all pending videos grouped by channel."""
    videos = db.get_videos_pending_review()
    if not videos:
        print("No videos pending review.")
        return []

    by_channel = defaultdict(list)
    for v in videos:
        by_channel[v["channel_id"]].append(v)

    print(f"\n{'='*70}")
    print(f"  Videos pending review: {len(videos)} across {len(by_channel)} channels")
    print(f"{'='*70}\n")

    for ch_id, ch_videos in by_channel.items():
        first = ch_videos[0]
        subs = first.get("subscriber_count", 0)
        name = first.get("channel_name", ch_id)
        print(f"  {name} ({subs:,} subs) — {len(ch_videos)} dubbed video(s)")

        for v in ch_videos:
            duration = v.get("duration_seconds", 0)
            mins = duration // 60
            secs = duration % 60
            status = v.get("review_status", "pending").upper()
            selected = " [SELECTED]" if v.get("selected_for_dubbing") else ""
            print(f"    {v['video_id']}  \"{(v.get('title') or '')[:55]}\"  ({mins}:{secs:02d})  — {status}{selected}")

        print()

    return videos


def list_all():
    """List all videos with their review status."""
    with db.get_conn() as conn:
        rows = conn.execute("""
            SELECT v.*, c.name as channel_name, c.subscriber_count
            FROM videos v
            JOIN channels c ON v.channel_id = c.channel_id
            WHERE v.has_auto_dub = 1
            ORDER BY c.subscriber_count DESC, v.duration_seconds ASC
        """).fetchall()

    if not rows:
        print("No dubbed videos found.")
        return

    by_channel = defaultdict(list)
    for r in rows:
        by_channel[r["channel_id"]].append(dict(r))

    for ch_id, ch_videos in by_channel.items():
        first = ch_videos[0]
        name = first.get("channel_name", ch_id)
        subs = first.get("subscriber_count", 0)
        print(f"\n  {name} ({subs:,} subs)")

        for v in ch_videos:
            duration = v.get("duration_seconds", 0)
            mins = duration // 60
            secs = duration % 60
            status = v.get("review_status", "pending").upper()
            selected = " *" if v.get("selected_for_dubbing") else ""
            print(f"    [{status:>8}] {v['video_id']}  \"{(v.get('title') or '')[:50]}\"  ({mins}:{secs:02d}){selected}")

    print(f"\n  * = selected for dubbing\n")


# ============================================================
# Non-interactive actions
# ============================================================

def approve_video(video_id, select=True):
    """Approve a video and optionally select it for dubbing."""
    db.update_video_review(video_id, "approved", selected=select)
    _maybe_advance_channel(video_id)
    log.info("Approved video %s (selected=%s)", video_id, select)


def reject_video(video_id, note=None):
    """Reject a video."""
    db.update_video_review(video_id, "rejected", review_note=note)
    log.info("Rejected video %s", video_id)


def select_video(video_id):
    """Mark an approved video for dubbing."""
    with db.get_conn() as conn:
        row = conn.execute("SELECT review_status FROM videos WHERE video_id = ?", (video_id,)).fetchone()
        if not row:
            log.error("Video %s not found", video_id)
            return
        if row["review_status"] != "approved":
            # Auto-approve if selecting
            db.update_video_review(video_id, "approved", selected=True)
        else:
            conn.execute(
                "UPDATE videos SET selected_for_dubbing = 1 WHERE video_id = ?",
                (video_id,),
            )
    _maybe_advance_channel(video_id)
    log.info("Selected video %s for dubbing", video_id)


def approve_all():
    """Approve and select all pending videos."""
    videos = db.get_videos_pending_review()
    if not videos:
        print("No videos pending review.")
        return

    count = 0
    for v in videos:
        db.update_video_review(v["video_id"], "approved", selected=True)
        _maybe_advance_channel(v["video_id"])
        count += 1

    log.info("Approved and selected %d videos", count)


def _maybe_advance_channel(video_id):
    """If a channel has at least one approved video, advance its status to 'approved'."""
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
            current = conn.execute(
                "SELECT status FROM channels WHERE channel_id = ?", (ch_id,)
            ).fetchone()
            if current and current["status"] in ("discovered", "enriched", "reviewed"):
                conn.execute(
                    "UPDATE channels SET status = 'approved', updated_at = ? WHERE channel_id = ?",
                    (datetime.now().isoformat(), ch_id),
                )


# ============================================================
# Interactive review
# ============================================================

def interactive_review():
    """Interactive review loop."""
    videos = db.get_videos_pending_review()
    if not videos:
        print("No videos pending review.")
        return

    by_channel = defaultdict(list)
    for v in videos:
        by_channel[v["channel_id"]].append(v)

    channel_list = list(by_channel.items())
    idx = 0

    while idx < len(channel_list):
        ch_id, ch_videos = channel_list[idx]
        first = ch_videos[0]
        name = first.get("channel_name", ch_id)
        subs = first.get("subscriber_count", 0)

        print(f"\n{'='*70}")
        print(f"  [{idx + 1}/{len(channel_list)}] {name} ({subs:,} subs) — {len(ch_videos)} dubbed video(s)")
        print(f"  https://www.youtube.com/channel/{ch_id}")
        print(f"{'='*70}")

        for j, v in enumerate(ch_videos):
            duration = v.get("duration_seconds", 0)
            mins = duration // 60
            secs = duration % 60
            letter = chr(ord("a") + j) if j < 26 else str(j)
            print(f"    [{letter}] {v['video_id']}  \"{(v.get('title') or '')[:55]}\"  ({mins}:{secs:02d})")
            print(f"        https://www.youtube.com/watch?v={v['video_id']}")

        print(f"\n  Action? [A]pprove all / [S]elect specific / [R]eject all / [N]ext / [Q]uit")
        try:
            action = input("  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting review.")
            return

        if action == "q":
            print("Exiting review.")
            return
        elif action == "n":
            idx += 1
            continue
        elif action == "a":
            for v in ch_videos:
                approve_video(v["video_id"], select=True)
            print(f"  Approved and selected {len(ch_videos)} video(s)")
            idx += 1
        elif action == "r":
            for v in ch_videos:
                reject_video(v["video_id"])
            print(f"  Rejected {len(ch_videos)} video(s)")
            idx += 1
        elif action == "s":
            print("  Enter video letters to select (e.g. 'a c'), or 'all':")
            try:
                sel = input("  > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                continue

            if sel == "all":
                for v in ch_videos:
                    approve_video(v["video_id"], select=True)
                print(f"  Selected all {len(ch_videos)} video(s)")
            else:
                selected_letters = sel.split()
                for letter in selected_letters:
                    j = ord(letter) - ord("a") if len(letter) == 1 and letter.isalpha() else -1
                    if 0 <= j < len(ch_videos):
                        approve_video(ch_videos[j]["video_id"], select=True)
                        print(f"  Selected: {ch_videos[j]['title'][:50]}")
                    else:
                        print(f"  Invalid: {letter}")
                # Reject the rest
                for j, v in enumerate(ch_videos):
                    letter = chr(ord("a") + j)
                    if letter not in selected_letters:
                        reject_video(v["video_id"])
            idx += 1
        else:
            print(f"  Unknown action: {action}")

    print(f"\nReview complete!")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Video Review Workflow")
    parser.add_argument("--list", action="store_true", help="List pending videos")
    parser.add_argument("--list-all", action="store_true", help="List all videos with review status")
    parser.add_argument("--approve-all", action="store_true", help="Approve and select all pending videos")
    parser.add_argument("--approve", type=str, metavar="VIDEO_ID", help="Approve a specific video")
    parser.add_argument("--reject", type=str, metavar="VIDEO_ID", help="Reject a specific video")
    parser.add_argument("--select", type=str, metavar="VIDEO_ID", help="Select a video for dubbing")
    args = parser.parse_args()

    if args.list:
        list_pending()
        return

    if args.list_all:
        list_all()
        return

    if args.approve_all:
        approve_all()
        return

    if args.approve:
        approve_video(args.approve)
        return

    if args.reject:
        reject_video(args.reject)
        return

    if args.select:
        select_video(args.select)
        return

    # Default: interactive review
    interactive_review()


if __name__ == "__main__":
    main()
