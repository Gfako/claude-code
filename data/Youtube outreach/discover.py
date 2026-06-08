#!/usr/bin/env python3
"""
discover.py — YouTube Channel Discovery & Dubbing Detection

Finds YouTube channels in the 5K-50K subscriber range that use
YouTube's auto-dubbing feature. Scores channels for likelihood
of being an individual creator (vs. organization).

Usage:
    python3 discover.py                          # Run full discovery
    python3 discover.py --check-only             # Only check dubbing on undiscovered channels
    python3 discover.py --stats                  # Show current stats
    python3 discover.py --country ES             # Only search in Spain
    python3 discover.py --keyword "tutorial" --language es
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime

import db
from utils import load_config, get_http_session, retry, log

# Lazy-import YouTube client
_youtube_client = None


def get_youtube_client(api_key):
    global _youtube_client
    if _youtube_client is None:
        from googleapiclient.discovery import build
        _youtube_client = build("youtube", "v3", developerKey=api_key)
    return _youtube_client


# ============================================================
# 1. CHANNEL SEARCH — YouTube Data API
# ============================================================

def search_channels(youtube, keyword, region_code, relevance_language, max_results=50):
    """Search for channels matching a keyword in a specific region."""
    results = []
    page_token = None

    while len(results) < max_results:
        request = youtube.search().list(
            part="snippet",
            q=keyword,
            type="channel",
            regionCode=region_code,
            relevanceLanguage=relevance_language,
            maxResults=min(50, max_results - len(results)),
            pageToken=page_token,
        )
        response = request.execute()

        for item in response.get("items", []):
            results.append({
                "channel_id": item["snippet"]["channelId"],
                "name": item["snippet"]["title"],
                "description": item["snippet"].get("description", ""),
            })

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return results


def get_channel_details(youtube, channel_ids):
    """Batch fetch channel details (up to 50 IDs per call)."""
    details = []
    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i:i + 50]
        request = youtube.channels().list(
            part="snippet,statistics,brandingSettings,topicDetails",
            id=",".join(batch),
        )
        response = request.execute()

        for item in response.get("items", []):
            stats = item.get("statistics", {})
            snippet = item.get("snippet", {})
            branding = item.get("brandingSettings", {}).get("channel", {})
            topics = item.get("topicDetails", {})

            sub_count = int(stats.get("subscriberCount", 0))
            hidden = stats.get("hiddenSubscriberCount", False)

            details.append({
                "channel_id": item["id"],
                "name": snippet.get("title", ""),
                "custom_url": snippet.get("customUrl", ""),
                "description": snippet.get("description", ""),
                "country": snippet.get("country", branding.get("country", "")),
                "default_language": snippet.get("defaultLanguage", ""),
                "subscriber_count": sub_count,
                "hidden_subscribers": hidden,
                "view_count": int(stats.get("viewCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
                "topic_categories": json.dumps(topics.get("topicCategories", [])),
            })

    return details


def get_recent_video_ids(youtube, channel_id, max_videos=10):
    """
    Get video IDs for a channel using the uploads playlist (1 unit/call)
    instead of search (100 units/call). Also fetches popular videos by
    sorting the channel's videos by viewCount using the search API as fallback.
    """
    ids = []

    # Method 1: Use uploads playlist (MUCH cheaper — 1 unit vs 100)
    # The uploads playlist ID is "UU" + channel_id[2:]
    uploads_playlist = "UU" + channel_id[2:]
    try:
        request = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist,
            maxResults=max_videos,
        )
        response = request.execute()
        for item in response.get("items", []):
            vid = item.get("contentDetails", {}).get("videoId")
            if vid and vid not in ids:
                ids.append(vid)
    except Exception as e:
        log.debug("Playlist fetch failed for %s: %s, falling back to search", channel_id, e)
        # Fallback to search API if playlist fails
        try:
            request = youtube.search().list(
                part="id",
                channelId=channel_id,
                type="video",
                order="date",
                maxResults=max_videos,
            )
            response = request.execute()
            for item in response.get("items", []):
                vid = item["id"].get("videoId")
                if vid and vid not in ids:
                    ids.append(vid)
        except Exception:
            pass

    return ids[:max_videos]


# ============================================================
# 2. CREATOR SCORING — Heuristic Classification
# ============================================================

def score_creator(channel, config):
    """Score a channel 0-100 on likelihood of being an individual creator."""
    score = 50
    name = (channel.get("name") or "").lower()
    desc = (channel.get("description") or "").lower()
    text = f"{name} {desc}"

    org_words = config["discovery"]["org_indicators"]
    creator_words = config["discovery"]["creator_indicators"]

    for word in org_words:
        if word.lower() in text:
            score -= 8

    for word in creator_words:
        if word.lower() in desc:
            score += 6

    name_parts = channel.get("name", "").strip().split()
    if 2 <= len(name_parts) <= 3 and all(p[0].isupper() for p in name_parts if p):
        score += 15

    video_count = channel.get("video_count", 0)
    if video_count < 200:
        score += 5
    elif video_count > 1000:
        score -= 10

    if channel.get("custom_url"):
        score += 5

    return max(0, min(100, score))


# ============================================================
# 3. DUBBING DETECTION — InnerTube (ytInitialPlayerResponse)
# ============================================================

@retry(max_attempts=3, delay=2)
def check_video_dubbing(video_id):
    """
    Check if a YouTube video has auto-dubbed audio tracks.
    Scrapes ytInitialPlayerResponse JSON from the watch page.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    session = get_http_session()

    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    html = resp.text

    match = re.search(
        r"ytInitialPlayerResponse\s*=\s*(\{.+?\})\s*;\s*(?:var|</script>)",
        html, re.DOTALL,
    )
    if not match:
        log.debug("Could not extract player response for %s", video_id)
        return None

    try:
        player = json.loads(match.group(1))
    except json.JSONDecodeError:
        log.debug("JSON parse error for %s", video_id)
        return None

    adaptive = player.get("streamingData", {}).get("adaptiveFormats", [])
    audio_tracks = {}

    for fmt in adaptive:
        at = fmt.get("audioTrack")
        if not at:
            continue
        tid = at.get("id", "")
        if not tid or tid in audio_tracks:
            continue

        display_name = at.get("displayName", "")
        is_auto = at.get("isAutoDubbed", False)
        is_original = "original" in display_name.lower() or ".original" in tid
        lang = tid.split(".")[0] if "." in tid else tid

        audio_tracks[tid] = {
            "id": tid,
            "language": lang,
            "displayName": display_name,
            "is_original": is_original,
            "is_auto_dubbed": is_auto,
            "is_creator_dubbed": not is_original and not is_auto and len(tid) > 0,
            "audioIsDefault": at.get("audioIsDefault", False),
        }

    unique_languages = set(t["language"] for t in audio_tracks.values())
    has_auto_dub = any(t["is_auto_dubbed"] for t in audio_tracks.values())
    has_creator_dub = any(t["is_creator_dubbed"] for t in audio_tracks.values())
    auto_dub_langs = [t["language"] for t in audio_tracks.values() if t["is_auto_dubbed"]]

    original_lang = next(
        (t["language"] for t in audio_tracks.values() if t["is_original"]),
        player.get("videoDetails", {}).get("shortDescription", "")[:2] or "unknown",
    )

    title = player.get("videoDetails", {}).get("title", "")
    duration = int(player.get("videoDetails", {}).get("lengthSeconds", 0))
    published = player.get("microformat", {}).get("playerMicroformatRenderer", {}).get("publishDate", "")

    return {
        "video_id": video_id,
        "title": title,
        "duration": duration,
        "published_at": published,
        "has_multiple_tracks": len(unique_languages) > 1,
        "has_auto_dub": has_auto_dub,
        "has_creator_dub": has_creator_dub,
        "original_language": original_lang,
        "auto_dub_languages": auto_dub_langs,
        "tracks": list(audio_tracks.values()),
    }


# ============================================================
# 4. MAIN PIPELINE
# ============================================================

def discover_channels(config, country_filter=None, keyword_filter=None, language_filter=None):
    """Run the full discovery pipeline."""
    api_key = config["youtube_api_key"]
    if not api_key:
        log.error("No youtube_api_key configured. Set YOUTUBE_API_KEY in .env")
        sys.exit(1)

    youtube = get_youtube_client(api_key)
    disc = config["discovery"]
    sub_min = disc["subscriber_min"]
    sub_max = disc["subscriber_max"]
    videos_to_check = disc["videos_to_check"]
    api_delay = config["rate_limits"]["youtube_api_delay"]
    ytdlp_delay = config["rate_limits"]["ytdlp_delay"]

    targets = disc["targets"]
    if country_filter:
        targets = [t for t in targets if t["country"] == country_filter.upper()]

    total_new = 0
    total_dubbed = 0

    for target in targets:
        country = target["country"]
        lang = target["language"]
        label = target["label"]

        keywords = disc["niche_keywords"].get(lang, [])
        if keyword_filter:
            keywords = [k for k in keywords if keyword_filter.lower() in k.lower()]
        if language_filter and lang != language_filter:
            continue

        log.info("=" * 60)
        log.info("  Searching: %s (%s/%s) — %d keywords", label, country, lang, len(keywords))

        for keyword in keywords:
            log.info("  >> Keyword: \"%s\"", keyword)

            try:
                results = search_channels(youtube, keyword, country, lang, max_results=50)
            except Exception as e:
                log.warning("  API error: %s", e)
                time.sleep(api_delay)
                continue

            if not results:
                log.info("    No channels found.")
                time.sleep(api_delay)
                continue

            new_ids = [r["channel_id"] for r in results if not db.channel_exists(r["channel_id"])]
            log.info("    Found %d channels, %d new", len(results), len(new_ids))

            if not new_ids:
                time.sleep(api_delay)
                continue

            time.sleep(api_delay)
            try:
                details = get_channel_details(youtube, new_ids)
            except Exception as e:
                log.warning("    API error getting details: %s", e)
                continue

            qualified = [
                ch for ch in details
                if not ch["hidden_subscribers"]
                and sub_min <= ch["subscriber_count"] <= sub_max
            ]
            log.info("    %d channels in %s-%s subscriber range", len(qualified), f"{sub_min:,}", f"{sub_max:,}")

            # Score and save
            with db.get_conn() as conn:
                for ch in qualified:
                    creator_score = score_creator(ch, config)
                    db.upsert_channel(
                        ch["channel_id"], conn=conn,
                        name=ch["name"],
                        custom_url=ch["custom_url"],
                        description=ch["description"],
                        country=ch["country"],
                        default_language=ch["default_language"],
                        subscriber_count=ch["subscriber_count"],
                        view_count=ch["view_count"],
                        video_count=ch["video_count"],
                        topic_categories=ch["topic_categories"],
                        creator_score=creator_score,
                        discovered_via=f"{keyword} ({country}/{lang})",
                    )
                    total_new += 1

            # Check dubbing on qualified channels
            for ch in qualified:
                log.info("    Checking dubbing: %s (%s subs)", ch["name"], f"{ch['subscriber_count']:,}")
                time.sleep(api_delay)

                try:
                    video_ids = get_recent_video_ids(youtube, ch["channel_id"], videos_to_check)
                except Exception as e:
                    log.warning("      Could not get videos: %s", e)
                    continue

                if not video_ids:
                    log.info("      No videos found")
                    continue

                channel_has_dubbing = False
                channel_dubbed_langs = set()

                with db.get_conn() as conn:
                    for vid_id in video_ids:
                        time.sleep(ytdlp_delay)
                        try:
                            result = check_video_dubbing(vid_id)
                        except Exception as e:
                            log.warning("      Dubbing check failed for %s: %s", vid_id, e)
                            continue
                        if result is None:
                            continue

                        db.upsert_video(
                            vid_id, conn=conn,
                            channel_id=ch["channel_id"],
                            title=result["title"],
                            published_at=result.get("published_at", ""),
                            duration_seconds=result["duration"],
                            default_audio_language=result["original_language"],
                            audio_tracks=json.dumps(result["tracks"]),
                            has_auto_dub=1 if result["has_auto_dub"] else 0,
                            has_creator_dub=1 if result["has_creator_dub"] else 0,
                        )

                        if result["has_auto_dub"]:
                            channel_has_dubbing = True
                            channel_dubbed_langs.update(result["auto_dub_languages"])
                            log.info("      [+] DUBBED: %s -> %s", result["title"][:50], result["auto_dub_languages"])
                        else:
                            track_count = len(set(t["language"] for t in result["tracks"]))
                            log.debug("      [-] No dubbing: %s (%d track(s))", result["title"][:50], track_count)

                    if channel_has_dubbing:
                        db.upsert_channel(
                            ch["channel_id"], conn=conn,
                            has_dubbing=1,
                            dubbed_languages=json.dumps(sorted(channel_dubbed_langs)),
                        )
                        total_dubbed += 1
                        log.info("      >>> QUALIFIED: %s — dubbed in %s", ch["name"], sorted(channel_dubbed_langs))

            time.sleep(api_delay)

    return total_new, total_dubbed


def check_dubbing_only(config):
    """Re-check dubbing on channels already in the DB that haven't been checked."""
    ytdlp_delay = config["rate_limits"]["ytdlp_delay"]
    api_key = config["youtube_api_key"]
    if not api_key:
        log.error("No youtube_api_key configured.")
        sys.exit(1)

    youtube = get_youtube_client(api_key)
    videos_to_check = config["discovery"]["videos_to_check"]

    with db.get_conn() as conn:
        rows = conn.execute("""
            SELECT c.channel_id, c.name, c.subscriber_count
            FROM channels c
            LEFT JOIN videos v ON c.channel_id = v.channel_id
            WHERE v.video_id IS NULL
            ORDER BY c.subscriber_count DESC
        """).fetchall()

    log.info("Found %d channels to check for dubbing.", len(rows))
    total_dubbed = 0

    for row in rows:
        ch_id = row["channel_id"]
        name = row["name"]
        subs = row["subscriber_count"]
        log.info("  Checking: %s (%s subs)", name, f"{subs:,}")

        try:
            video_ids = get_recent_video_ids(youtube, ch_id, videos_to_check)
        except Exception as e:
            log.warning("    Could not get videos: %s", e)
            continue

        channel_has_dubbing = False
        channel_dubbed_langs = set()

        with db.get_conn() as conn:
            for vid_id in video_ids:
                time.sleep(ytdlp_delay)
                try:
                    result = check_video_dubbing(vid_id)
                except Exception as e:
                    log.warning("    Dubbing check failed for %s: %s", vid_id, e)
                    continue
                if result is None:
                    continue

                db.upsert_video(
                    vid_id, conn=conn,
                    channel_id=ch_id,
                    title=result["title"],
                    published_at=result.get("published_at", ""),
                    duration_seconds=result["duration"],
                    default_audio_language=result["original_language"],
                    audio_tracks=json.dumps(result["tracks"]),
                    has_auto_dub=1 if result["has_auto_dub"] else 0,
                    has_creator_dub=1 if result["has_creator_dub"] else 0,
                )

                if result["has_auto_dub"]:
                    channel_has_dubbing = True
                    channel_dubbed_langs.update(result["auto_dub_languages"])

            if channel_has_dubbing:
                db.upsert_channel(ch_id, conn=conn, has_dubbing=1, dubbed_languages=json.dumps(sorted(channel_dubbed_langs)))
                total_dubbed += 1
                log.info("    [+] DUBBED in: %s", sorted(channel_dubbed_langs))
            else:
                log.info("    [-] No dubbing detected")

    log.info("Done. %d new dubbed channels found.", total_dubbed)


def print_stats():
    """Print database statistics."""
    stats = db.get_stats()
    print(f"""
Youtube Outreach — Pipeline Stats
{'='*40}
  Total channels discovered:  {stats['total_channels']:,}
  Channels with dubbing:      {stats['dubbed_channels']:,}
  Enriched channels:          {stats['enriched_channels']:,}
  Approved channels:          {stats['approved_channels']:,}
  Channels with email:        {stats['channels_with_email']:,}
  Channels with website:      {stats['channels_with_website']:,}
  Total videos checked:       {stats['total_videos_checked']:,}
  Videos pending review:      {stats['videos_pending_review']:,}
  Videos approved:            {stats['videos_approved']:,}
  Dub jobs completed:         {stats['dub_jobs_complete']:,}
{'='*40}
    """)


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="YouTube Channel Discovery & Dubbing Detection")
    parser.add_argument("--stats", action="store_true", help="Show current stats")
    parser.add_argument("--check-only", action="store_true", help="Only check dubbing on undiscovered channels")
    parser.add_argument("--country", type=str, help="Filter by country code (e.g. ES, BR, IT)")
    parser.add_argument("--keyword", type=str, help="Filter by keyword")
    parser.add_argument("--language", type=str, help="Filter by language code (e.g. es, pt, it)")
    args = parser.parse_args()

    config = load_config()

    if args.stats:
        print_stats()
        return

    if args.check_only:
        check_dubbing_only(config)
        return

    log.info("Starting discovery at %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    total_new, total_dubbed = discover_channels(
        config,
        country_filter=args.country,
        keyword_filter=args.keyword,
        language_filter=args.language,
    )
    log.info("=" * 60)
    log.info("  Discovery complete! New: %d, Dubbed: %d", total_new, total_dubbed)
    print_stats()


if __name__ == "__main__":
    main()
