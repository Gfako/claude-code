#!/usr/bin/env python3
"""
pull_channel_videos.py — Get recent videos from YouTube channels we found via scraping.

Uses YouTube API efficiently:
- channels().list with batch of 50 IDs (1 unit per call)
- playlistItems().list for uploads playlist (1 unit per call)
Total cost: ~50 units for channels + 525 for playlists = ~575 units (well within 10k quota)
"""

import re
import sqlite3
import sys
import time
import argparse

from googleapiclient.discovery import build as yt_build
from googleapiclient.errors import HttpError

sys.path.insert(0, ".")
from utils import load_config

DB_PATH = "data/saas_outreach.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def extract_channel_identifier(url):
    """Extract channel ID, handle, or custom URL from a YouTube channel URL."""
    if not url:
        return None, None
    # /channel/UC...
    m = re.search(r'youtube\.com/channel/(UC[\w-]+)', url)
    if m:
        return 'id', m.group(1)
    # /@handle
    m = re.search(r'youtube\.com/@([\w.-]+)', url)
    if m:
        return 'handle', m.group(1)
    # /c/CustomName
    m = re.search(r'youtube\.com/c/([\w.-]+)', url)
    if m:
        return 'custom', m.group(1)
    # /user/Username
    m = re.search(r'youtube\.com/user/([\w.-]+)', url)
    if m:
        return 'user', m.group(1)
    return None, None


def resolve_channel_id(youtube, id_type, identifier):
    """Resolve a handle/custom/user to a channel ID."""
    if id_type == 'id':
        return identifier
    
    if id_type == 'handle':
        try:
            resp = youtube.channels().list(forHandle=identifier, part='id').execute()
            items = resp.get('items', [])
            if items:
                return items[0]['id']
        except Exception:
            pass
    
    if id_type in ('custom', 'user', 'handle'):
        # Fallback: search for the channel
        try:
            resp = youtube.search().list(q=identifier, type='channel', part='snippet', maxResults=1).execute()
            items = resp.get('items', [])
            if items:
                return items[0]['snippet']['channelId']
        except Exception:
            pass
    
    return None


def get_uploads_playlist(youtube, channel_ids):
    """Get uploads playlist IDs for a batch of channel IDs."""
    result = {}
    # Batch up to 50
    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i:i+50]
        try:
            resp = youtube.channels().list(
                id=','.join(batch),
                part='contentDetails,statistics'
            ).execute()
            for ch in resp.get('items', []):
                uploads = ch.get('contentDetails', {}).get('relatedPlaylists', {}).get('uploads')
                subs = int(ch.get('statistics', {}).get('subscriberCount', 0) or 0)
                vid_count = int(ch.get('statistics', {}).get('videoCount', 0) or 0)
                if uploads:
                    result[ch['id']] = {
                        'uploads_playlist': uploads,
                        'subscriber_count': subs,
                        'video_count': vid_count,
                    }
        except HttpError as e:
            if 'quotaExceeded' in str(e):
                print("  QUOTA EXCEEDED — stopping.")
                return result
            print(f"  API error on batch: {e}")
    return result


def get_recent_videos(youtube, playlist_id, max_results=5):
    """Get recent videos from an uploads playlist."""
    try:
        resp = youtube.playlistItems().list(
            playlistId=playlist_id,
            part='snippet',
            maxResults=max_results,
        ).execute()
        videos = []
        for item in resp.get('items', []):
            vid_id = item['snippet']['resourceId'].get('videoId')
            if vid_id:
                videos.append({
                    'video_id': vid_id,
                    'title': item['snippet'].get('title', ''),
                    'url': f'https://www.youtube.com/watch?v={vid_id}',
                })
        return videos
    except Exception as e:
        return []


def run(limit=None, max_videos=5):
    config = load_config()
    api_key = config.get('youtube_api_key', '')
    if not api_key:
        print("No YOUTUBE_API_KEY configured")
        sys.exit(1)

    youtube = yt_build('youtube', 'v3', developerKey=api_key)
    conn = get_conn()

    # Get companies with YouTube channel URLs but no videos yet
    rows = conn.execute('''
        SELECT c.domain, c.name, c.youtube_channel_url
        FROM companies c
        WHERE c.has_youtube_channel = 1
          AND c.youtube_channel_url IS NOT NULL
          AND c.youtube_channel_url != ''
          AND c.domain NOT IN (SELECT DISTINCT domain FROM company_videos)
        ORDER BY c.domain_rating DESC NULLS LAST
    ''').fetchall()

    companies = [dict(r) for r in rows]
    if limit:
        companies = companies[:limit]

    print(f"Pulling videos for {len(companies)} channels...\n")

    # Phase 1: Resolve all channel IDs
    print("Phase 1: Resolving channel IDs...")
    channel_map = {}  # domain -> channel_id
    for comp in companies:
        id_type, identifier = extract_channel_identifier(comp['youtube_channel_url'])
        if id_type == 'id':
            channel_map[comp['domain']] = identifier
        elif id_type and identifier:
            cid = resolve_channel_id(youtube, id_type, identifier)
            if cid:
                channel_map[comp['domain']] = cid
                # Save channel ID to DB
                conn.execute('UPDATE companies SET youtube_channel_id = ? WHERE domain = ?',
                             (cid, comp['domain']))
            time.sleep(0.1)

    print(f"  Resolved {len(channel_map)} channel IDs out of {len(companies)}")
    conn.commit()

    # Phase 2: Get uploads playlists in batches
    print("\nPhase 2: Getting uploads playlists...")
    all_channel_ids = list(set(channel_map.values()))
    playlist_info = get_uploads_playlist(youtube, all_channel_ids)
    print(f"  Got {len(playlist_info)} uploads playlists")

    # Phase 3: Get recent videos
    print(f"\nPhase 3: Pulling recent videos (max {max_videos} per channel)...")
    total_videos = 0
    companies_with_videos = 0

    # Build reverse map: channel_id -> domain(s)
    cid_to_domains = {}
    for domain, cid in channel_map.items():
        cid_to_domains.setdefault(cid, []).append(domain)

    for cid, info in playlist_info.items():
        videos = get_recent_videos(youtube, info['uploads_playlist'], max_videos)
        if videos:
            for domain in cid_to_domains.get(cid, []):
                name = next((c['name'] for c in companies if c['domain'] == domain), domain)
                # Update company stats
                conn.execute('''
                    UPDATE companies SET 
                        youtube_subscriber_count = ?,
                        youtube_video_count = ?,
                        status = 'video_checked'
                    WHERE domain = ?
                ''', (info['subscriber_count'], info['video_count'], domain))
                
                # Insert videos
                for vid in videos:
                    existing = conn.execute(
                        'SELECT 1 FROM company_videos WHERE domain = ? AND video_url = ?',
                        (domain, vid['url'])
                    ).fetchone()
                    if not existing:
                        conn.execute('''
                            INSERT INTO company_videos (domain, video_type, video_url, video_id, title, detection_method)
                            VALUES (?, 'youtube_channel', ?, ?, ?, 'youtube_api')
                        ''', (domain, vid['url'], vid['video_id'], vid['title']))
                        total_videos += 1
                
                companies_with_videos += 1
                if companies_with_videos % 50 == 0:
                    print(f"  Progress: {companies_with_videos} companies, {total_videos} videos")
                    conn.commit()
        
        time.sleep(0.1)

    # Also mark companies where we resolved channel but got no videos
    for domain, cid in channel_map.items():
        if cid not in playlist_info or not get_recent_videos(youtube, playlist_info.get(cid, {}).get('uploads_playlist', ''), 1):
            conn.execute("UPDATE companies SET status = 'video_checked' WHERE domain = ? AND status = 'discovered'", (domain,))

    conn.commit()
    conn.close()

    print(f"\n{'='*60}")
    print(f"  Complete!")
    print(f"  Channels processed: {len(channel_map)}")
    print(f"  Companies with videos: {companies_with_videos}")
    print(f"  Total videos added: {total_videos}")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    parser.add_argument("--max-videos", type=int, default=5)
    args = parser.parse_args()
    run(limit=args.limit, max_videos=args.max_videos)
