#!/usr/bin/env python3
"""
discover_noquota.py — Discover YouTube channels with ZERO API usage.

Uses only web scraping:
1. Scrapes YouTube search results to find channel IDs
2. Scrapes each channel page to get subscriber count, name, description
3. Scrapes videos to detect dubbing

No YouTube API quota is consumed at all.

Usage:
    python3 discover_noquota.py --country ES --keyword "tutorial"
    python3 discover_noquota.py --all
    python3 discover_noquota.py --all --skip-dubbing
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from urllib.parse import quote_plus

import db
from utils import load_config, get_http_session, retry, log
from discover import score_creator, check_video_dubbing


@retry(max_attempts=3, delay=3)
def scrape_channel_search(keyword, gl="", hl=""):
    """Search YouTube for channels via web scraping. gl=country, hl=language."""
    session = get_http_session()
    q = quote_plus(keyword)
    # sp=EgIQAg%3D%3D = filter for "Channels" only
    params = f"search_query={q}&sp=EgIQAg%3D%3D"
    if gl:
        params += f"&gl={gl}"
    if hl:
        params += f"&hl={hl}"
    url = f"https://www.youtube.com/results?{params}"

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

    channels = []
    _extract_channel_results(data, channels)
    return channels


def _extract_channel_results(obj, results, depth=0):
    """Extract channel info from search results ytInitialData."""
    if depth > 30:
        return
    if isinstance(obj, dict):
        if "channelRenderer" in obj:
            cr = obj["channelRenderer"]
            ch_id = cr.get("channelId", "")
            if not ch_id:
                return

            title = ""
            title_obj = cr.get("title", {})
            if isinstance(title_obj, dict):
                runs = title_obj.get("simpleText", "") or ""
                if not runs:
                    runs_list = title_obj.get("runs", [])
                    if runs_list:
                        runs = runs_list[0].get("text", "")
                title = runs

            # Subscriber count from subscriberCountText
            sub_text = ""
            sub_obj = cr.get("subscriberCountText", {})
            if isinstance(sub_obj, dict):
                sub_text = sub_obj.get("simpleText", "") or sub_obj.get("accessibility", {}).get("accessibilityData", {}).get("label", "")

            sub_count = _parse_subscriber_text(sub_text)

            desc = ""
            desc_obj = cr.get("descriptionSnippet", {})
            if isinstance(desc_obj, dict):
                for run in desc_obj.get("runs", []):
                    desc += run.get("text", "")

            results.append({
                "channel_id": ch_id,
                "name": title,
                "subscriber_count": sub_count,
                "description": desc,
            })
        else:
            for val in obj.values():
                _extract_channel_results(val, results, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _extract_channel_results(item, results, depth + 1)


def _parse_subscriber_text(text):
    """Parse '33.3K subscribers' or '1.2M subscribers' or '33,3 mil suscriptores' into integer."""
    if not text:
        return 0
    # Remove subscriber/suscriptores/inscritos/iscritti/abonnés and similar suffixes
    text = re.sub(r'\b(subscribers?|suscriptores?|inscritos?|iscritti|abonnés|abonné|subs)\b', '', text, flags=re.IGNORECASE)
    text = text.strip().rstrip(".")

    # Handle European decimal separator: "33,3" -> "33.3"
    # But first, check if comma is thousands separator (e.g. "1,200") vs decimal (e.g. "33,3")
    # European: "33,3 mil" or "5,4 K" — comma followed by 1 digit = decimal
    text = re.sub(r'(\d),(\d)(?!\d\d)', r'\1.\2', text)
    # Remove remaining commas (thousands separators)
    text = text.replace(",", "")

    text = text.strip().lower()

    try:
        if " mil" in text or text.endswith("mil"):
            num = float(re.sub(r'\s*mil\s*', '', text).strip())
            return int(num * 1_000)
        elif "m" in text:
            num = float(text.replace("m", "").strip())
            return int(num * 1_000_000)
        elif "k" in text:
            num = float(text.replace("k", "").strip())
            return int(num * 1_000)
        else:
            return int(float(text))
    except (ValueError, TypeError):
        return 0


@retry(max_attempts=3, delay=3)
def scrape_video_search(keyword, gl="", hl=""):
    """Search YouTube for videos and extract channel IDs of video owners."""
    session = get_http_session()
    q = quote_plus(keyword)
    params = f"search_query={q}"
    if gl:
        params += f"&gl={gl}"
    if hl:
        params += f"&hl={hl}"
    url = f"https://www.youtube.com/results?{params}"

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

    channel_ids = set()
    _extract_video_channel_ids(data, channel_ids)
    return list(channel_ids)


def _extract_video_channel_ids(obj, ids, depth=0):
    if depth > 30:
        return
    if isinstance(obj, dict):
        if "videoRenderer" in obj:
            vr = obj["videoRenderer"]
            browse = vr.get("ownerText", {}).get("runs", [{}])[0]
            endpoint = browse.get("navigationEndpoint", {}).get("browseEndpoint", {})
            ch_id = endpoint.get("browseId", "")
            if ch_id.startswith("UC"):
                ids.add(ch_id)
        for val in obj.values():
            _extract_video_channel_ids(val, ids, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _extract_video_channel_ids(item, ids, depth + 1)


@retry(max_attempts=2, delay=3)
def scrape_channel_page(channel_id):
    """Scrape a channel's main page for subscriber count and details."""
    session = get_http_session()
    url = f"https://www.youtube.com/channel/{channel_id}"

    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    html = resp.text

    match = re.search(r"var ytInitialData\s*=\s*({.+?})\s*;\s*</script>", html, re.DOTALL)
    if not match:
        match = re.search(r"ytInitialData\s*=\s*({.+?})\s*;\s*(?:var|window)", html, re.DOTALL)
    if not match:
        return None

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None

    # Extract channel metadata
    result = {"channel_id": channel_id}
    _extract_channel_metadata(data, result)
    return result


def _extract_channel_metadata(obj, result, depth=0):
    """Extract name, subs, description from channel page ytInitialData."""
    if depth > 25:
        return
    if isinstance(obj, dict):
        # c4TabbedHeaderRenderer (older layout)
        if "c4TabbedHeaderRenderer" in obj:
            header = obj["c4TabbedHeaderRenderer"]
            result["name"] = result.get("name") or header.get("title", "")
            sub_text = header.get("subscriberCountText", {}).get("simpleText", "")
            if sub_text:
                result["subscriber_count"] = _parse_subscriber_text(sub_text)

        # subscriberCountText appears at various levels — grab the first valid one
        if "subscriberCountText" in obj and "subscriber_count" not in result:
            sct = obj["subscriberCountText"]
            sub_text = ""
            if isinstance(sct, dict):
                sub_text = sct.get("simpleText", "")
                if not sub_text:
                    sub_text = sct.get("accessibility", {}).get("accessibilityData", {}).get("label", "")
            if sub_text:
                parsed = _parse_subscriber_text(sub_text)
                if parsed > 0:
                    result["subscriber_count"] = parsed

        # channelMetadataRenderer has description and more
        if "channelMetadataRenderer" in obj:
            meta = obj["channelMetadataRenderer"]
            result["name"] = result.get("name") or meta.get("title", "")
            result["description"] = meta.get("description", "")
            result["custom_url"] = meta.get("vanityChannelUrl", "").replace("http://www.youtube.com/", "").replace("https://www.youtube.com/", "")

        for val in obj.values():
            _extract_channel_metadata(val, result, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _extract_channel_metadata(item, result, depth + 1)


def scrape_channel_videos(channel_id, max_videos=10):
    """Scrape a channel's videos page to get video IDs."""
    session = get_http_session()
    url = f"https://www.youtube.com/channel/{channel_id}/videos"

    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
    except Exception:
        return []

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

    video_ids = []
    _extract_video_ids(data, video_ids)
    return video_ids[:max_videos]


def _extract_video_ids(obj, ids, depth=0):
    if depth > 30 or len(ids) >= 20:
        return
    if isinstance(obj, dict):
        if "gridVideoRenderer" in obj:
            vid_id = obj["gridVideoRenderer"].get("videoId")
            if vid_id and vid_id not in ids:
                ids.append(vid_id)
        elif "richItemRenderer" in obj:
            content = obj["richItemRenderer"].get("content", {})
            vid_id = content.get("videoRenderer", {}).get("videoId")
            if vid_id and vid_id not in ids:
                ids.append(vid_id)
        elif "videoRenderer" in obj and "videoId" in obj.get("videoRenderer", {}):
            vid_id = obj["videoRenderer"]["videoId"]
            if vid_id and vid_id not in ids:
                ids.append(vid_id)
        for val in obj.values():
            _extract_video_ids(val, ids, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _extract_video_ids(item, ids, depth + 1)


def run_discovery(config, country_filter=None, keyword_filter=None, language_filter=None, skip_dubbing=False):
    """Main discovery loop — zero API quota consumed."""
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
        log.info("  %s (%s/%s) — %d keywords [NO API QUOTA]", label, country, lang, len(keywords))

        for keyword in keywords:
            log.info("  >> \"%s\"", keyword)

            # 1. Scrape channel search results (with country/language)
            all_channels = {}
            try:
                channels = scrape_channel_search(keyword, gl=country, hl=lang)
                for ch in channels:
                    if ch["channel_id"] not in all_channels:
                        all_channels[ch["channel_id"]] = ch
            except Exception as e:
                log.warning("    Channel scrape failed: %s", e)

            time.sleep(2)

            # 2. Also scrape video search to find more channel IDs
            try:
                extra_ids = scrape_video_search(keyword, gl=country, hl=lang)
                for cid in extra_ids:
                    if cid not in all_channels:
                        all_channels[cid] = {"channel_id": cid, "name": "", "subscriber_count": 0, "description": ""}
            except Exception as e:
                log.warning("    Video scrape failed: %s", e)

            time.sleep(2)

            # Filter already-known
            new_channels = {cid: ch for cid, ch in all_channels.items() if not db.channel_exists(cid)}
            log.info("    Found %d channels, %d new", len(all_channels), len(new_channels))

            if not new_channels:
                continue

            # 3. For channels missing subscriber count, scrape channel page
            qualified = []
            for cid, ch in new_channels.items():
                if ch["subscriber_count"] == 0 or not ch["name"]:
                    time.sleep(1.5)
                    try:
                        details = scrape_channel_page(cid)
                        if details:
                            ch.update(details)
                    except Exception as e:
                        log.debug("    Could not scrape channel %s: %s", cid, e)
                        continue

                subs = ch.get("subscriber_count", 0)
                if sub_min <= subs <= sub_max:
                    qualified.append(ch)

            log.info("    %d in %s-%s range", len(qualified), f"{sub_min:,}", f"{sub_max:,}")

            # 4. Save qualified channels
            with db.get_conn() as conn:
                for ch in qualified:
                    creator_score = score_creator(ch, config)
                    db.upsert_channel(
                        ch["channel_id"], conn=conn,
                        name=ch.get("name", ""),
                        custom_url=ch.get("custom_url", ""),
                        description=ch.get("description", ""),
                        country=ch.get("country", country),
                        default_language=ch.get("default_language", lang),
                        subscriber_count=ch.get("subscriber_count", 0),
                        view_count=ch.get("view_count", 0),
                        video_count=ch.get("video_count", 0),
                        topic_categories=ch.get("topic_categories", "[]"),
                        creator_score=creator_score,
                        discovered_via=f"{keyword} ({country}/{lang})",
                    )
                    total_new += 1

            if skip_dubbing:
                continue

            # 5. Check dubbing via web scraping
            for ch in qualified:
                log.info("    Dubbing: %s (%s subs)", ch.get("name", "?")[:40], f"{ch.get('subscriber_count', 0):,}")

                time.sleep(1.5)
                video_ids = scrape_channel_videos(ch["channel_id"], videos_to_check)
                if not video_ids:
                    log.debug("      No videos found")
                    continue

                channel_has_dubbing = False
                channel_dubbed_langs = set()

                with db.get_conn() as conn:
                    for vid_id in video_ids:
                        time.sleep(ytdlp_delay)
                        try:
                            result = check_video_dubbing(vid_id)
                        except Exception as e:
                            log.debug("      Check failed %s: %s", vid_id, e)
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

                    if channel_has_dubbing:
                        db.upsert_channel(
                            ch["channel_id"], conn=conn,
                            has_dubbing=1,
                            dubbed_languages=json.dumps(sorted(channel_dubbed_langs)),
                        )
                        total_dubbed += 1
                        log.info("      >>> DUBBED: %s — %s", ch.get("name", "?"), sorted(channel_dubbed_langs))

    return total_new, total_dubbed


def main():
    parser = argparse.ArgumentParser(description="YouTube Discovery — Zero API Quota")
    parser.add_argument("--country", type=str)
    parser.add_argument("--keyword", type=str)
    parser.add_argument("--language", type=str)
    parser.add_argument("--all", action="store_true", help="Run all countries/keywords")
    parser.add_argument("--skip-dubbing", action="store_true")
    args = parser.parse_args()

    config = load_config()

    if not args.all and not args.country and not args.keyword:
        print("Provide --country, --keyword, --all, or both")
        parser.print_help()
        sys.exit(1)

    log.info("Starting zero-quota discovery at %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    total_new, total_dubbed = run_discovery(
        config,
        country_filter=args.country,
        keyword_filter=args.keyword,
        language_filter=args.language,
        skip_dubbing=args.skip_dubbing,
    )
    log.info("Complete! New: %d, Dubbed: %d", total_new, total_dubbed)

    from discover import print_stats
    print_stats()


if __name__ == "__main__":
    main()
