#!/usr/bin/env python3
"""
discover_scrape.py — Discover YouTube channels via web scraping (no API quota needed)

Searches YouTube directly via HTTP, extracts channel IDs, then uses the
cheap channels.list API (1 unit) for details and web scraping for dubbing detection.

This bypasses the expensive search API (100 units/call) which quickly exhausts
the daily quota.

Usage:
    python3 discover_scrape.py --country ES --keyword "tutorial"
    python3 discover_scrape.py --all           # Run all countries/keywords
    python3 discover_scrape.py --all --skip-dubbing  # Just discover, check dubbing later
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime

import db
from utils import load_config, get_http_session, retry, log
from discover import score_creator, check_video_dubbing


def _get_youtube_client(api_key):
    from googleapiclient.discovery import build
    return build("youtube", "v3", developerKey=api_key)


@retry(max_attempts=3, delay=3)
def scrape_youtube_search(keyword, region_code, language):
    """
    Search YouTube via web scraping to find channel IDs.
    Returns list of channel IDs found in the search results.
    """
    session = get_http_session()
    # Search for channels
    url = f"https://www.youtube.com/results?search_query={keyword}&sp=EgIQAg%3D%3D"  # sp filter = channels only
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    html = resp.text

    # Extract ytInitialData
    match = re.search(r"var ytInitialData\s*=\s*({.+?})\s*;\s*</script>", html, re.DOTALL)
    if not match:
        match = re.search(r"ytInitialData\s*=\s*({.+?})\s*;\s*(?:var|window)", html, re.DOTALL)
    if not match:
        log.warning("Could not extract ytInitialData from search results")
        return []

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        log.warning("JSON parse error in search results")
        return []

    # Extract channel IDs from search results
    channel_ids = set()
    _find_channel_ids(data, channel_ids)

    return list(channel_ids)


def _find_channel_ids(obj, ids, depth=0):
    """Recursively find channel IDs in ytInitialData."""
    if depth > 30:
        return
    if isinstance(obj, dict):
        # Look for channelRenderer which contains channel search results
        if "channelRenderer" in obj:
            cr = obj["channelRenderer"]
            ch_id = cr.get("channelId")
            if ch_id:
                ids.add(ch_id)
        # Also look for browseId in navigationEndpoint
        for key, val in obj.items():
            if key == "channelId" and isinstance(val, str) and val.startswith("UC"):
                ids.add(val)
            elif key == "browseId" and isinstance(val, str) and val.startswith("UC"):
                ids.add(val)
            else:
                _find_channel_ids(val, ids, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _find_channel_ids(item, ids, depth + 1)


@retry(max_attempts=2, delay=3)
def scrape_youtube_video_search(keyword, region_code=""):
    """
    Search YouTube for videos (not channels) to discover more channel IDs.
    Videos matching the keyword likely belong to relevant channels.
    """
    session = get_http_session()
    url = f"https://www.youtube.com/results?search_query={keyword}"
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    html = resp.text

    match = re.search(r"var ytInitialData\s*=\s*({.+?})\s*;\s*</script>", html, re.DOTALL)
    if not match:
        match = re.search(r"ytInitialData\s*=\s*({.+?})\s*;\s*(?:var|window)", html, re.DOTALL)
    if not match:
        return []

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []

    # Find unique channel IDs from video results
    channel_ids = set()
    _find_video_owners(data, channel_ids)
    return list(channel_ids)


def _find_video_owners(obj, ids, depth=0):
    """Find channel IDs from video search results."""
    if depth > 30:
        return
    if isinstance(obj, dict):
        if "videoRenderer" in obj:
            vr = obj["videoRenderer"]
            ch = vr.get("ownerText", {}).get("runs", [{}])[0]
            endpoint = ch.get("navigationEndpoint", {}).get("browseEndpoint", {})
            ch_id = endpoint.get("browseId", "")
            if ch_id and ch_id.startswith("UC"):
                ids.add(ch_id)
        for val in obj.values():
            _find_video_owners(val, ids, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _find_video_owners(item, ids, depth + 1)


def get_channel_details_api(youtube, channel_ids):
    """Use cheap channels.list API (1 unit per 50 channels)."""
    details = []
    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i:i + 50]
        try:
            request = youtube.channels().list(
                part="snippet,statistics,brandingSettings,topicDetails",
                id=",".join(batch),
            )
            response = request.execute()
        except Exception as e:
            log.warning("channels.list error: %s", e)
            continue

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
        time.sleep(0.3)

    return details


def get_video_ids_from_playlist(youtube, channel_id, max_videos=10):
    """Get video IDs using uploads playlist (1 unit)."""
    uploads_playlist = "UU" + channel_id[2:]
    try:
        request = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist,
            maxResults=max_videos,
        )
        response = request.execute()
        return [
            item.get("contentDetails", {}).get("videoId")
            for item in response.get("items", [])
            if item.get("contentDetails", {}).get("videoId")
        ]
    except Exception as e:
        log.debug("Playlist error for %s: %s", channel_id, e)
        return []


def run_scrape_discovery(config, country_filter=None, keyword_filter=None, language_filter=None, skip_dubbing=False):
    """Run discovery using web scraping for search + cheap API for details."""
    api_key = config["youtube_api_key"]
    youtube = _get_youtube_client(api_key)

    disc = config["discovery"]
    sub_min = disc["subscriber_min"]
    sub_max = disc["subscriber_max"]
    videos_to_check = disc["videos_to_check"]
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
            log.info("  >> Keyword: \"%s\" (web scrape)", keyword)

            # Scrape YouTube search for channels AND videos
            all_channel_ids = set()
            try:
                ch_ids = scrape_youtube_search(keyword, country, lang)
                all_channel_ids.update(ch_ids)
                log.info("    Channel search: %d channel IDs", len(ch_ids))
            except Exception as e:
                log.warning("    Channel scrape failed: %s", e)

            time.sleep(2)

            try:
                vid_ch_ids = scrape_youtube_video_search(f"{keyword} {lang}", country)
                all_channel_ids.update(vid_ch_ids)
                log.info("    Video search: %d additional channel IDs", len(vid_ch_ids - set(ch_ids if 'ch_ids' in dir() else [])))
            except Exception as e:
                log.warning("    Video scrape failed: %s", e)

            time.sleep(2)

            # Filter out already-known channels
            new_ids = [cid for cid in all_channel_ids if not db.channel_exists(cid)]
            log.info("    Total: %d channel IDs, %d new", len(all_channel_ids), len(new_ids))

            if not new_ids:
                continue

            # Get details via cheap API call
            details = get_channel_details_api(youtube, new_ids)

            qualified = [
                ch for ch in details
                if not ch["hidden_subscribers"]
                and sub_min <= ch["subscriber_count"] <= sub_max
            ]
            log.info("    %d in %s-%s subscriber range", len(qualified), f"{sub_min:,}", f"{sub_max:,}")

            # Save and score
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

            if skip_dubbing:
                log.info("    Skipping dubbing check (--skip-dubbing)")
                continue

            # Check dubbing
            for ch in qualified:
                log.info("    Checking dubbing: %s (%s subs)", ch["name"], f"{ch['subscriber_count']:,}")

                video_ids = get_video_ids_from_playlist(youtube, ch["channel_id"], videos_to_check)
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
                            log.warning("      Check failed for %s: %s", vid_id, e)
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

                    if channel_has_dubbing:
                        db.upsert_channel(
                            ch["channel_id"], conn=conn,
                            has_dubbing=1,
                            dubbed_languages=json.dumps(sorted(channel_dubbed_langs)),
                        )
                        total_dubbed += 1
                        log.info("      >>> QUALIFIED: %s — dubbed in %s", ch["name"], sorted(channel_dubbed_langs))

    return total_new, total_dubbed


def main():
    parser = argparse.ArgumentParser(description="YouTube Discovery via Web Scraping (no API quota)")
    parser.add_argument("--country", type=str, help="Filter by country code")
    parser.add_argument("--keyword", type=str, help="Filter by keyword")
    parser.add_argument("--language", type=str, help="Filter by language code")
    parser.add_argument("--all", action="store_true", help="Run all countries and keywords")
    parser.add_argument("--skip-dubbing", action="store_true", help="Skip dubbing check (faster)")
    args = parser.parse_args()

    config = load_config()

    if not args.all and not args.country and not args.keyword:
        print("Provide --country, --keyword, or --all")
        parser.print_help()
        sys.exit(1)

    log.info("Starting web-scrape discovery at %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    total_new, total_dubbed = run_scrape_discovery(
        config,
        country_filter=args.country,
        keyword_filter=args.keyword,
        language_filter=args.language,
        skip_dubbing=args.skip_dubbing,
    )
    log.info("Discovery complete! New: %d, Dubbed: %d", total_new, total_dubbed)

    from discover import print_stats
    print_stats()


if __name__ == "__main__":
    main()
