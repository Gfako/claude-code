#!/usr/bin/env python3
"""
enrich.py — Contact & Website Enrichment

Scrapes YouTube channel About pages (via ytInitialData) to extract:
  - Website URLs
  - Social media profiles (Twitter, Instagram, LinkedIn, TikTok)
  - Email addresses (from description and about page)

Usage:
    python3 enrich.py                     # Enrich all discovered channels
    python3 enrich.py --dubbed-only       # Only enrich channels with dubbing
"""

import argparse
import json
import re
import time
from datetime import datetime
from urllib.parse import unquote, urlparse

import db
from utils import load_config, get_http_session, retry, log


# ============================================================
# 1. EMAIL EXTRACTION
# ============================================================

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

EMAIL_BLACKLIST = {
    "example@email.com", "example@gmail.com", "your@email.com",
    "name@email.com", "email@example.com", "user@example.com",
}


def extract_emails(text):
    """Extract email addresses from text, filtering false positives."""
    if not text:
        return []
    emails = EMAIL_RE.findall(text)
    return [e for e in emails if e.lower() not in EMAIL_BLACKLIST]


# ============================================================
# 2. URL EXTRACTION & CATEGORISATION
# ============================================================

URL_RE = re.compile(r"https?://[^\s<>\"'\)]+", re.IGNORECASE)


def extract_urls(text):
    if not text:
        return []
    return URL_RE.findall(text)


def categorize_url(url):
    """Categorize a URL into platform type."""
    url_lower = url.lower()
    if not url_lower.startswith(("http://", "https://")):
        url_lower = "https://" + url_lower
    domain = urlparse(url_lower).netloc

    if "twitter.com" in domain or "x.com" in domain:
        return "twitter"
    elif "instagram.com" in domain:
        return "instagram"
    elif "linkedin.com" in domain:
        return "linkedin"
    elif "tiktok.com" in domain:
        return "tiktok"
    elif "facebook.com" in domain or "fb.com" in domain:
        return "facebook"
    elif "discord" in domain:
        return "discord"
    elif "twitch.tv" in domain:
        return "twitch"
    elif "patreon.com" in domain:
        return "patreon"
    elif "linktr.ee" in domain or "beacons.ai" in domain or "bio.link" in domain:
        return "linktree"
    elif "youtube.com" in domain or "youtu.be" in domain:
        return "youtube"
    elif any(d in domain for d in ["google.com", "goo.gl", "bit.ly", "amzn.to"]):
        return "other"
    else:
        return "website"


# ============================================================
# 3. ABOUT PAGE SCRAPING (ytInitialData)
# ============================================================

def resolve_youtube_redirect(url):
    """Resolve YouTube redirect URLs."""
    if "youtube.com/redirect" in url:
        match = re.search(r"[?&]q=([^&]+)", url)
        if match:
            return unquote(match.group(1))
    return url


@retry(max_attempts=3, delay=2)
def scrape_about_page(channel_id, custom_url=None):
    """
    Scrape a channel's About page to extract links and metadata
    from the embedded ytInitialData JSON.
    """
    if custom_url:
        url = f"https://www.youtube.com/{custom_url}/about"
    else:
        url = f"https://www.youtube.com/channel/{channel_id}/about"

    session = get_http_session()
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    html = resp.text

    match = re.search(r"var ytInitialData\s*=\s*({.+?})\s*;\s*</script>", html, re.DOTALL)
    if not match:
        match = re.search(r"ytInitialData\s*=\s*({.+?})\s*;\s*(?:var|window)", html, re.DOTALL)
    if not match:
        log.debug("Could not extract ytInitialData for %s", channel_id)
        return None

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        log.debug("JSON parse error for %s", channel_id)
        return None

    result = {
        "links": [],
        "emails": [],
        "description_from_about": "",
        "_seen_urls": set(),
    }

    _extract_links_from_data(data, result)
    del result["_seen_urls"]
    return result


def _extract_links_from_data(data, result):
    _search_json(data, "aboutChannelViewModel", result)
    _search_json(data, "channelAboutFullMetadataRenderer", result)
    _search_json(data, "channelExternalLinkViewModel", result)
    _search_json(data, "channelHeaderLinksViewModel", result)


def _search_json(obj, target_key, result, depth=0):
    if depth > 20:
        return
    if isinstance(obj, dict):
        for key, val in obj.items():
            if key == target_key and isinstance(val, dict):
                _process_renderer(key, val, result)
            elif key == "primaryLinks" and isinstance(val, list):
                for link_item in val:
                    _extract_link(link_item, result)
            elif key == "channelExternalLinkViewModel" and isinstance(val, dict):
                _extract_external_link(val, result)
            else:
                _search_json(val, target_key, result, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _search_json(item, target_key, result, depth + 1)


def _process_renderer(key, renderer, result):
    if key == "aboutChannelViewModel":
        desc = renderer.get("description", "")
        if desc:
            result["description_from_about"] = desc
            result["emails"].extend(extract_emails(desc))
        for link_item in renderer.get("links", []):
            _extract_external_link(link_item.get("channelExternalLinkViewModel", {}), result)

    elif key == "channelAboutFullMetadataRenderer":
        desc_runs = renderer.get("description", {}).get("simpleText", "")
        if desc_runs:
            result["description_from_about"] = desc_runs
            result["emails"].extend(extract_emails(desc_runs))
        for link_item in renderer.get("primaryLinks", []):
            _extract_link(link_item, result)

    elif key == "channelHeaderLinksViewModel":
        for btn in renderer.get("firstLink", []):
            url = btn.get("commandRuns", [{}])[0].get("command", {}).get("url", "")
            if url:
                result["links"].append({"title": "Header Link", "url": resolve_youtube_redirect(url)})


def _extract_link(link_item, result):
    title = ""
    url = ""

    title_obj = link_item.get("title", {})
    if isinstance(title_obj, str):
        title = title_obj
    elif isinstance(title_obj, dict):
        title = title_obj.get("simpleText", "") or title_obj.get("content", "")

    nav = link_item.get("navigationEndpoint", {})
    url_endpoint = nav.get("urlEndpoint", {})
    url = url_endpoint.get("url", "")

    if not url:
        cmd = nav.get("commandMetadata", {}).get("webCommandMetadata", {})
        url = cmd.get("url", "")

    if url:
        url = resolve_youtube_redirect(url)
        if url not in result.get("_seen_urls", set()):
            result.get("_seen_urls", set()).add(url)
            result["links"].append({"title": title, "url": url})
            result["emails"].extend(extract_emails(url))


def _extract_external_link(link_vm, result):
    title = link_vm.get("title", {}).get("content", "") or link_vm.get("title", "")
    link_obj = link_vm.get("link", {})

    url = link_obj.get("commandRuns", [{}])[0].get("command", {}).get("innertubeCommand", {}).get(
        "urlEndpoint", {}
    ).get("url", "")

    if not url:
        url = link_obj.get("content", "")

    if url:
        url = resolve_youtube_redirect(url)
        if url not in result.get("_seen_urls", set()):
            result.get("_seen_urls", set()).add(url)
            result["links"].append({"title": title, "url": url})


# ============================================================
# 4. ENRICHMENT PIPELINE
# ============================================================

def enrich_channel(channel):
    """Enrich a single channel with contact data."""
    channel_id = channel["channel_id"]
    custom_url = channel.get("custom_url")
    description = channel.get("description", "")

    contact_data = {
        "website_url": None,
        "email_from_desc": None,
        "email_from_about": None,
        "twitter_url": None,
        "instagram_url": None,
        "linkedin_url": None,
        "tiktok_url": None,
        "other_links": [],
    }

    # Emails from channel description
    desc_emails = extract_emails(description)
    if desc_emails:
        contact_data["email_from_desc"] = desc_emails[0]

    # URLs from description
    desc_urls = extract_urls(description)
    for url in desc_urls:
        cat = categorize_url(url)
        if cat == "website" and not contact_data["website_url"]:
            contact_data["website_url"] = url
        elif cat == "twitter" and not contact_data["twitter_url"]:
            contact_data["twitter_url"] = url
        elif cat == "instagram" and not contact_data["instagram_url"]:
            contact_data["instagram_url"] = url
        elif cat == "linkedin" and not contact_data["linkedin_url"]:
            contact_data["linkedin_url"] = url
        elif cat == "tiktok" and not contact_data["tiktok_url"]:
            contact_data["tiktok_url"] = url

    # Scrape About page
    try:
        about_data = scrape_about_page(channel_id, custom_url)
    except Exception as e:
        log.warning("About page scrape failed for %s: %s", channel_id, e)
        about_data = None

    if about_data:
        for link in about_data.get("links", []):
            url = link.get("url", "")
            title = link.get("title", "")
            if not url:
                continue
            cat = categorize_url(url)
            if cat == "website" and not contact_data["website_url"]:
                contact_data["website_url"] = url
            elif cat == "twitter" and not contact_data["twitter_url"]:
                contact_data["twitter_url"] = url
            elif cat == "instagram" and not contact_data["instagram_url"]:
                contact_data["instagram_url"] = url
            elif cat == "linkedin" and not contact_data["linkedin_url"]:
                contact_data["linkedin_url"] = url
            elif cat == "tiktok" and not contact_data["tiktok_url"]:
                contact_data["tiktok_url"] = url
            elif cat == "linktree":
                if not contact_data["website_url"]:
                    contact_data["website_url"] = url
                contact_data["other_links"].append({"title": title or "Linktree", "url": url})
            elif cat not in ("youtube", "other"):
                contact_data["other_links"].append({"title": title, "url": url})

        about_emails = about_data.get("emails", [])
        if about_emails:
            contact_data["email_from_about"] = about_emails[0]

    return contact_data


def run_enrichment(dubbed_only=False):
    """Run enrichment on all qualifying channels."""
    config = load_config()
    delay = config["enrichment"]["request_delay"]

    if dubbed_only:
        channels = db.get_dubbed_channels()
    else:
        channels = db.get_channels_by_status("discovered")

    channels = [c for c in channels if c["status"] not in ("enriched", "reviewed", "approved", "dubbed", "pitched", "responded")]

    if not channels:
        log.info("No channels to enrich.")
        return

    log.info("Enriching %d channels...", len(channels))

    enriched_count = 0
    with_website = 0
    with_email = 0

    for i, channel in enumerate(channels):
        ch_id = channel["channel_id"]
        name = channel["name"]
        subs = channel["subscriber_count"]

        log.info("  [%d/%d] %s (%s subs)", i + 1, len(channels), name, f"{subs:,}")

        contact_data = enrich_channel(channel)

        # Compute website_domain for Ahrefs matching
        from utils import clean_domain
        website_domain = clean_domain(contact_data["website_url"]) if contact_data["website_url"] else None

        with db.get_conn() as conn:
            db.upsert_contact(
                ch_id, conn=conn,
                website_url=contact_data["website_url"],
                website_domain=website_domain,
                email_from_desc=contact_data["email_from_desc"],
                email_from_about=contact_data["email_from_about"],
                twitter_url=contact_data["twitter_url"],
                instagram_url=contact_data["instagram_url"],
                linkedin_url=contact_data["linkedin_url"],
                tiktok_url=contact_data["tiktok_url"],
                other_links=json.dumps(contact_data["other_links"]),
                enriched_at=datetime.now().isoformat(),
            )
            db.upsert_channel(ch_id, conn=conn, status="enriched")

        enriched_count += 1
        has_website = bool(contact_data["website_url"])
        has_email = bool(contact_data["email_from_desc"] or contact_data["email_from_about"])
        if has_website:
            with_website += 1
        if has_email:
            with_email += 1

        indicators = []
        if has_website:
            indicators.append(f"web: {contact_data['website_url'][:50]}")
        if has_email:
            email = contact_data["email_from_desc"] or contact_data["email_from_about"]
            indicators.append(f"email: {email}")
        if contact_data["twitter_url"]:
            indicators.append("twitter")
        if contact_data["instagram_url"]:
            indicators.append("instagram")
        if contact_data["linkedin_url"]:
            indicators.append("linkedin")

        if indicators:
            log.info("    Found: %s", ", ".join(indicators))
        else:
            log.info("    No contact info found")

        time.sleep(delay)

    log.info("=" * 60)
    log.info("  Enrichment complete! %d channels", enriched_count)
    log.info("  With website: %d (%d%%)", with_website, 100 * with_website // max(enriched_count, 1))
    log.info("  With email: %d (%d%%)", with_email, 100 * with_email // max(enriched_count, 1))


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Contact & Website Enrichment")
    parser.add_argument("--dubbed-only", action="store_true", help="Only enrich channels with dubbing")
    args = parser.parse_args()

    run_enrichment(dubbed_only=args.dubbed_only)


if __name__ == "__main__":
    main()
