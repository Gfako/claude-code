#!/usr/bin/env python3
"""
dub.py — Synthesia Video Dubbing

Downloads a YouTube video and dubs it using the Synthesia API.
Only dubs videos that have been approved via review.py and
marked as selected_for_dubbing.

Usage:
    python3 dub.py --video VIDEO_ID --target-lang es
    python3 dub.py --channel CHANNEL_ID              # Auto-pick best approved video
    python3 dub.py --status PROJECT_ID               # Check dubbing status
    python3 dub.py --list-jobs                        # List all dubbing jobs
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

import requests
import yt_dlp

import db
from utils import load_config, retry, log, VIDEOS_DIR

SYNTHESIA_BASE = "https://api.synthesia.io"


# ============================================================
# 1. DOWNLOAD YouTube Video
# ============================================================

def download_youtube_video(video_id, output_dir=VIDEOS_DIR):
    """Download a YouTube video in best MP4 format. Returns path or None."""
    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, f"{video_id}.%(ext)s")

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "quiet": False,
        "no_warnings": True,
        "format_sort": ["+lang:original"],
    }

    url = f"https://www.youtube.com/watch?v={video_id}"
    log.info("Downloading video %s...", video_id)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if not filename.endswith(".mp4"):
            filename = os.path.splitext(filename)[0] + ".mp4"

    if os.path.exists(filename):
        size_mb = os.path.getsize(filename) / (1024 * 1024)
        log.info("Downloaded: %s (%.1f MB)", filename, size_mb)
        return filename
    else:
        log.error("Download failed — file not found at %s", filename)
        return None


def trim_video(video_path, start_seconds=0, end_seconds=None, duration_seconds=None):
    """Trim a video using ffmpeg. Supports start/end or just duration. Returns trimmed path."""
    import subprocess
    if end_seconds is not None:
        label = f"{start_seconds}s-{end_seconds}s"
        dur = end_seconds - start_seconds
    elif duration_seconds is not None:
        label = f"{duration_seconds}s"
        dur = duration_seconds
    else:
        return video_path

    trimmed_path = video_path.replace(".mp4", f"_trim.mp4")
    cmd = ["ffmpeg", "-y", "-i", video_path, "-ss", str(start_seconds), "-t", str(dur), "-c", "copy", trimmed_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and os.path.exists(trimmed_path):
        size_mb = os.path.getsize(trimmed_path) / (1024 * 1024)
        log.info("Trimmed to %s: %s (%.1f MB)", label, trimmed_path, size_mb)
        return trimmed_path
    else:
        log.error("Trim failed: %s", result.stderr[-200:] if result.stderr else "unknown")
        return video_path


# ============================================================
# 2. UPLOAD to Synthesia
# ============================================================

def upload_to_synthesia(api_key, video_path):
    """
    Upload a video file to Synthesia. Uses the large-file S3 upload
    for files > 10MB, direct upload for smaller files.
    Returns asset ID or None.
    """
    log.info("Uploading to Synthesia (%s)...", os.path.basename(video_path))
    file_size = os.path.getsize(video_path)
    log.info("File size: %.1f MB", file_size / (1024 * 1024))

    # Always use S3 upload — direct upload has a very low size limit
    return _upload_via_s3(api_key, video_path)


@retry(max_attempts=2, delay=10, exceptions=(requests.RequestException,))
def _upload_direct(api_key, video_path):
    """Direct upload for files under 10MB."""
    with open(video_path, "rb") as f:
        resp = requests.post(
            f"{SYNTHESIA_BASE}/v2/assets",
            headers={"Authorization": api_key, "Content-Type": "video/mp4"},
            data=f,
            timeout=300,
        )
    if resp.status_code not in (200, 201):
        log.error("Upload failed (%d): %s", resp.status_code, resp.text)
        return None
    asset_id = resp.json().get("id")
    log.info("Uploaded (direct). Asset ID: %s", asset_id)
    return asset_id


def _upload_via_s3(api_key, video_path):
    """Large file upload via temporary S3 credentials."""
    import boto3

    # Step 1: Create asset and get S3 credentials
    resp = requests.post(
        f"{SYNTHESIA_BASE}/v2/assets",
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        json={
            "contentType": "video/mp4",
            "configuration": {"name": "dubbing", "detectLanguage": True},
            "title": os.path.splitext(os.path.basename(video_path))[0],
        },
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        log.error("Asset creation failed (%d): %s", resp.status_code, resp.text)
        return None

    data = resp.json()
    asset_id = data.get("id")
    creds = data.get("uploadCredentials", {})
    bucket = creds.get("bucket")
    key = creds.get("key")
    region = creds.get("region", "eu-west-1")

    if not all([bucket, key, creds.get("accessKeyId")]):
        log.error("Missing S3 upload info in response: %s", data)
        return None

    log.info("Uploading to S3 (bucket=%s, key=%s)...", bucket, key)

    # Step 2: Upload to S3
    s3 = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=creds["accessKeyId"],
        aws_secret_access_key=creds["secretAccessKey"],
        aws_session_token=creds.get("sessionToken"),
    )

    file_size = os.path.getsize(video_path)
    from boto3.s3.transfer import TransferConfig
    config = TransferConfig(multipart_threshold=10 * 1024 * 1024)

    s3.upload_file(video_path, bucket, key, Config=config)
    log.info("Uploaded to S3. Asset ID: %s", asset_id)
    return asset_id


# ============================================================
# 3. START Dubbing Job
# ============================================================

@retry(max_attempts=2, delay=5, exceptions=(requests.RequestException,))
def start_dubbing(api_key, asset_id, target_languages, source_language="en", title="", lipsync=True):
    """Start a Synthesia dubbing job. Returns project ID or None."""
    log.info("Starting dubbing: %s → %s (lip-sync: %s)", source_language, target_languages, lipsync)

    body = {
        "sourceAssetId": asset_id,
        "sourceLanguage": source_language,
        "targetLanguages": target_languages if isinstance(target_languages, list) else [target_languages],
        "title": title or f"Dub {asset_id[:8]}",
        "lipsyncEnabled": lipsync,
    }

    resp = requests.post(
        f"{SYNTHESIA_BASE}/v2/dubbing",
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        json=body,
        timeout=30,
    )

    if resp.status_code not in (200, 201, 202):
        log.error("Dubbing start failed (%d): %s", resp.status_code, resp.text)
        return None

    data = resp.json()
    # The API may return the project ID in different fields
    project_id = (
        data.get("projectId")
        or data.get("id")
        or data.get("createdImportedAsset", {}).get("id")
    )
    log.info("Dubbing started. Project ID: %s (response: %s)", project_id, data)
    return project_id


# ============================================================
# 4. POLL for Completion
# ============================================================

def check_dubbing_status(api_key, project_id):
    resp = requests.get(
        f"{SYNTHESIA_BASE}/v2/dubbing/{project_id}",
        headers={"Authorization": api_key},
        timeout=30,
    )
    if resp.status_code != 200:
        log.warning("Status check failed (%d): %s", resp.status_code, resp.text)
        return None
    return resp.json()


def wait_for_dubbing(api_key, project_id, poll_interval=15, max_wait=1800):
    """Poll until dubbing completes or fails."""
    log.info("Waiting for dubbing (polling every %ds)...", poll_interval)
    elapsed = 0

    while elapsed < max_wait:
        data = check_dubbing_status(api_key, project_id)
        if data is None:
            time.sleep(poll_interval)
            elapsed += poll_interval
            continue

        status = data.get("status", "").lower()
        log.info("  [%ds] Status: %s", elapsed, status)

        if status == "complete":
            return data
        elif status == "error":
            error = data.get("errorCode", "unknown")
            log.error("Dubbing failed: %s", error)
            return data

        for asset in data.get("dubbedAssets", []):
            log.debug("    %s: %s", asset.get("language", "?"), asset.get("status", "?"))

        time.sleep(poll_interval)
        elapsed += poll_interval

    log.error("Timed out after %ds", max_wait)
    return None


# ============================================================
# 5. DOWNLOAD Dubbed Video
# ============================================================

def download_dubbed_video(download_url, output_path):
    log.info("Downloading dubbed video...")
    resp = requests.get(download_url, timeout=300, stream=True)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    log.info("Saved: %s (%.1f MB)", output_path, size_mb)
    return output_path


# ============================================================
# 6. REVIEW GATE — only dub approved + selected videos
# ============================================================

def pick_best_video(channel_id):
    """
    Pick the best video for dubbing from a channel.
    ONLY considers videos with review_status='approved' AND selected_for_dubbing=1.
    Falls back to any approved video if none are explicitly selected.
    """
    videos = db.get_videos_for_channel(channel_id)

    # First: approved + selected
    selected = [v for v in videos if v.get("review_status") == "approved" and v.get("selected_for_dubbing")]
    if not selected:
        # Fallback: any approved video
        selected = [v for v in videos if v.get("review_status") == "approved"]
    if not selected:
        log.warning("No approved videos for channel %s. Run 'python3 review.py' first.", channel_id)
        return None

    # Prefer shorter (cheaper) but at least 30s
    candidates = [v for v in selected if (v.get("duration_seconds") or 0) >= 30]
    if not candidates:
        candidates = selected

    candidates.sort(key=lambda v: v.get("duration_seconds") or 9999)
    best = candidates[0]
    log.info("Selected video: %s (%ds)", best["title"][:60], best.get("duration_seconds", 0))
    return best["video_id"]


def _check_review_gate(video_id):
    """Verify a video is approved for dubbing. Returns True if OK."""
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT review_status, selected_for_dubbing FROM videos WHERE video_id = ?",
            (video_id,),
        ).fetchone()

    if not row:
        log.error("Video %s not found in database.", video_id)
        return False

    if row["review_status"] != "approved":
        log.error(
            "Video %s has review_status='%s'. Must be 'approved'. Run 'python3 review.py --approve %s'",
            video_id, row["review_status"], video_id,
        )
        return False

    return True


# ============================================================
# 7. FULL PIPELINE
# ============================================================

def dub_video(video_id, target_lang, config, channel_id=None, max_duration=None):
    """Full pipeline: review gate -> download -> trim -> upload -> dub -> poll -> download result."""
    api_key = config["synthesia_api_key"]
    if not api_key:
        log.error("No synthesia_api_key configured. Set SYNTHESIA_API_KEY in .env")
        sys.exit(1)

    # Review gate
    if not _check_review_gate(video_id):
        return None

    lipsync = config["synthesia"].get("lipsync_enabled", True)

    # Get source language
    source_lang = None
    video_data = None
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM videos WHERE video_id = ?", (video_id,)).fetchone()
        if row:
            video_data = dict(row)
            source_lang = video_data.get("default_audio_language", "en")

    db_job_id = db.create_dub_job(
        channel_id=channel_id or (video_data or {}).get("channel_id"),
        source_video_id=video_id,
        source_language=source_lang or "unknown",
        target_language=target_lang,
    )

    # Step 1: Download
    db.update_dub_job(db_job_id, status="downloading")
    video_path = download_youtube_video(video_id)
    if not video_path:
        db.update_dub_job(db_job_id, status="failed", error_message="Download failed")
        return None

    # Step 1b: Trim if max_duration set
    original_path = video_path
    if max_duration:
        video_path = trim_video(video_path, max_duration)

    # Step 2: Upload
    db.update_dub_job(db_job_id, status="uploading")
    asset_id = upload_to_synthesia(api_key, video_path)
    if not asset_id:
        db.update_dub_job(db_job_id, status="failed", error_message="Upload failed")
        _cleanup_temp(video_path)
        return None

    db.update_dub_job(db_job_id, synthesia_asset_id=asset_id)

    # Step 3: Start dubbing
    db.update_dub_job(db_job_id, status="dubbing")
    video_title = (video_data or {}).get("title", video_id)
    # Normalize language codes: "en-US" → "en", "es-US" → "es"
    src_lang_short = (source_lang or "en").split("-")[0]
    project_id = start_dubbing(
        api_key, asset_id, target_lang,
        source_language=src_lang_short,
        title=video_title,
        lipsync=lipsync,
    )
    if not project_id:
        db.update_dub_job(db_job_id, status="failed", error_message="Dubbing start failed")
        _cleanup_temp(video_path)
        return None

    db.update_dub_job(db_job_id, synthesia_job_id=project_id)

    # Step 4: Wait
    result = wait_for_dubbing(api_key, project_id)
    if result is None or result.get("status", "").lower() != "complete":
        error_msg = result.get("errorCode", "timeout") if result else "timeout"
        db.update_dub_job(db_job_id, status="failed", error_message=str(error_msg))
        _cleanup_temp(video_path)
        return None

    # Step 5: Download dubbed videos
    output_paths = []
    for asset in result.get("dubbedAssets", []):
        if asset.get("status", "").upper() == "COMPLETE" and asset.get("downloadUrl"):
            lang = asset.get("language", target_lang)
            out_path = os.path.join(VIDEOS_DIR, f"{video_id}_dubbed_{lang}.mp4")
            download_dubbed_video(asset["downloadUrl"], out_path)
            output_paths.append(out_path)

    if output_paths:
        db.update_dub_job(
            db_job_id,
            status="complete",
            output_path=output_paths[0],
            completed_at=datetime.now().isoformat(),
        )
        # Advance channel status
        ch = channel_id or (video_data or {}).get("channel_id")
        if ch:
            db.upsert_channel(ch, status="dubbed")
        log.info("Dubbing complete! Output: %s", output_paths)
    else:
        db.update_dub_job(db_job_id, status="failed", error_message="No dubbed assets in result")
        log.error("No dubbed assets found in result")

    # Cleanup source download
    _cleanup_temp(video_path)
    return output_paths


def _cleanup_temp(video_path):
    """Remove the downloaded source video to save disk space."""
    if video_path and os.path.exists(video_path):
        try:
            os.remove(video_path)
            log.debug("Cleaned up temp file: %s", video_path)
        except OSError as e:
            log.warning("Could not clean up %s: %s", video_path, e)


def list_jobs():
    """List all dubbing jobs."""
    with db.get_conn() as conn:
        rows = conn.execute("""
            SELECT dj.*, c.name as channel_name
            FROM dub_jobs dj
            LEFT JOIN channels c ON dj.channel_id = c.channel_id
            ORDER BY dj.created_at DESC
        """).fetchall()

    if not rows:
        print("No dubbing jobs found.")
        return

    print(f"\n{'ID':<5} {'Channel':<30} {'Video':<15} {'Lang':<8} {'Status':<12} {'Created':<20}")
    print("-" * 90)
    for row in rows:
        r = dict(row)
        print(f"{r['id']:<5} {(r.get('channel_name') or '?')[:29]:<30} "
              f"{r['source_video_id'][:14]:<15} {r['target_language']:<8} "
              f"{r['status']:<12} {r['created_at'][:19]:<20}")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Synthesia Video Dubbing")
    parser.add_argument("--video", type=str, help="YouTube video ID to dub")
    parser.add_argument("--channel", type=str, help="Channel ID — auto-pick best approved video")
    parser.add_argument("--target-lang", type=str, default="en", help="Target language (e.g. es, pt-BR)")
    parser.add_argument("--no-lipsync", action="store_true", help="Disable lip-sync")
    parser.add_argument("--duration", type=int, help="Only dub first N seconds of the video")
    parser.add_argument("--status", type=str, help="Check Synthesia dubbing project status")
    parser.add_argument("--list-jobs", action="store_true", help="List all dubbing jobs")
    args = parser.parse_args()

    config = load_config()

    if args.list_jobs:
        list_jobs()
        return

    if args.status:
        api_key = config["synthesia_api_key"]
        data = check_dubbing_status(api_key, args.status)
        if data:
            print(json.dumps(data, indent=2))
        return

    if args.no_lipsync:
        config["synthesia"]["lipsync_enabled"] = False

    video_id = args.video
    channel_id = args.channel

    if channel_id and not video_id:
        video_id = pick_best_video(channel_id)
        if not video_id:
            log.error("Could not auto-pick a video. Use --video to specify one.")
            sys.exit(1)

    if not video_id:
        print("Please provide --video VIDEO_ID or --channel CHANNEL_ID")
        parser.print_help()
        sys.exit(1)

    dub_video(video_id, args.target_lang, config, channel_id=channel_id, max_duration=args.duration)


if __name__ == "__main__":
    main()
