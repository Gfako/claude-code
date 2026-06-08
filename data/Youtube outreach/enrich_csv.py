#!/usr/bin/env python3
"""
enrich_csv.py - Enrich a CSV of YouTube channels with contact info.

Reads a CSV with channel names and optional URLs, then:
1. Resolves missing channel URLs via YouTube API search
2. Scrapes each channel's About page for emails, website, social links
3. Optionally scrapes found websites for contact emails
4. Outputs an enriched CSV

Usage:
    python3 enrich_csv.py input.csv
    python3 enrich_csv.py input.csv --output enriched.csv
    python3 enrich_csv.py input.csv --scrape-websites   # also scrape found websites for emails
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from urllib.parse import urlparse, unquote

import requests

from utils import load_config, get_http_session, log
from enrich import (
    scrape_about_page, extract_emails, extract_urls,
    categorize_url, resolve_youtube_redirect,
)


# ============================================================
# 1. RESOLVE CHANNEL URLs via YouTube API
# ============================================================

def find_channel_url(youtube, channel_name):
    """Search YouTube for a channel by name and return its URL + ID."""
    try:
        request = youtube.search().list(
            part="snippet",
            q=channel_name,
            type="channel",
            maxResults=5,
        )
        response = request.execute()
    except Exception as e:
        print(f"    [!] API error: {e}")
        return None, None

    # Try to match by name
    name_lower = channel_name.lower().strip()
    for item in response.get("items", []):
        title = item["snippet"]["title"]
        ch_id = item["snippet"]["channelId"]
        if title.lower().strip() == name_lower:
            custom = item["snippet"].get("customUrl", "")
            url = f"https://www.youtube.com/{custom}" if custom else f"https://www.youtube.com/channel/{ch_id}"
            return url, ch_id

    # Fall back to first result if no exact match
    if response.get("items"):
        item = response["items"][0]
        ch_id = item["snippet"]["channelId"]
        custom = item["snippet"].get("customUrl", "")
        url = f"https://www.youtube.com/{custom}" if custom else f"https://www.youtube.com/channel/{ch_id}"
        return url, ch_id

    return None, None


def extract_channel_id_from_url(url):
    """Extract channel ID or custom handle from a YouTube URL."""
    if not url:
        return None, None
    url = url.strip()
    # https://www.youtube.com/channel/UCxxxx
    m = re.search(r"youtube\.com/channel/(UC[a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1), None
    # https://www.youtube.com/@handle
    m = re.search(r"youtube\.com/(@[a-zA-Z0-9_.-]+)", url)
    if m:
        return None, m.group(1)
    return None, None


# ============================================================
# 2. SCRAPE WEBSITE FOR EMAILS
# ============================================================

def scrape_website_for_emails(website_url, max_pages=3):
    """
    Scrape a website's main page and common contact pages for email addresses.
    """
    if not website_url:
        return []

    # Normalize URL
    if not website_url.startswith(("http://", "https://")):
        website_url = "https://" + website_url

    found_emails = set()
    pages_to_try = [
        website_url,
        website_url.rstrip("/") + "/contact",
        website_url.rstrip("/") + "/about",
        website_url.rstrip("/") + "/contact-us",
        website_url.rstrip("/") + "/about-us",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/122.0.0.0 Safari/537.36",
    }

    for page_url in pages_to_try[:max_pages]:
        try:
            resp = requests.get(page_url, headers=headers, timeout=10, allow_redirects=True)
            if resp.status_code == 200:
                emails = extract_emails(resp.text)
                found_emails.update(emails)
        except Exception:
            pass

    # Filter out generic/noreply emails
    blacklist_patterns = ["noreply", "no-reply", "donotreply", "example", "wordpress", "wix", "squarespace"]
    return [e for e in found_emails if not any(p in e.lower() for p in blacklist_patterns)]


# ============================================================
# 3. MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Enrich a CSV of YouTube channels with contact info")
    parser.add_argument("input_csv", help="Input CSV file")
    parser.add_argument("--output", "-o", help="Output CSV path", default=None)
    parser.add_argument("--scrape-websites", action="store_true", help="Also scrape found websites for emails")
    args = parser.parse_args()

    config = load_config()
    api_key = config.get("youtube_api_key", "")

    youtube = None
    if api_key:
        from googleapiclient.discovery import build
        youtube = build("youtube", "v3", developerKey=api_key)

    # Read input CSV
    rows = []
    with open(args.input_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip empty rows
            if not row.get("Channel Name"):
                continue
            rows.append(row)

    print(f"Loaded {len(rows)} channels from {args.input_csv}\n")

    # Output path
    if args.output:
        out_path = args.output
    else:
        base = os.path.splitext(args.input_csv)[0]
        out_path = f"{base}_enriched.csv"

    results = []

    for i, row in enumerate(rows):
        name = row.get("Channel Name", "").strip()
        channel_url = row.get("Channel", "").strip()

        print(f"[{i+1}/{len(rows)}] {name}")

        # Step 1: Resolve channel URL if missing
        channel_id = None
        custom_handle = None

        if channel_url:
            channel_id, custom_handle = extract_channel_id_from_url(channel_url)
        elif youtube:
            print(f"  Searching YouTube for channel...")
            channel_url, channel_id = find_channel_url(youtube, name)
            if channel_url:
                print(f"  Found: {channel_url}")
                _, custom_handle = extract_channel_id_from_url(channel_url)
            else:
                print(f"  Could not find channel URL")
            time.sleep(0.5)

        # Step 2: Scrape About page
        email = ""
        website = ""
        twitter = ""
        instagram = ""
        linkedin = ""
        tiktok = ""
        other_social = ""
        all_links = []

        if channel_id or custom_handle:
            about = scrape_about_page(channel_id, custom_handle)
            if about:
                # Emails
                if about["emails"]:
                    email = about["emails"][0]

                # Links
                for link in about.get("links", []):
                    url = link.get("url", "")
                    title = link.get("title", "")
                    cat = categorize_url(url)

                    if cat == "website" and not website:
                        website = url
                    elif cat == "twitter" and not twitter:
                        twitter = url
                    elif cat == "instagram" and not instagram:
                        instagram = url
                    elif cat == "linkedin" and not linkedin:
                        linkedin = url
                    elif cat == "tiktok" and not tiktok:
                        tiktok = url
                    elif cat == "linktree" and not website:
                        website = url
                    elif cat not in ("youtube", "other"):
                        all_links.append(f"{title}: {url}")

                # Also check description for emails
                desc_about = about.get("description_from_about", "")
                desc_emails = extract_emails(desc_about)
                if desc_emails and not email:
                    email = desc_emails[0]

            time.sleep(1.5)
        else:
            print(f"  No channel ID/handle — skipping About page scrape")

        # Step 3: Scrape website for emails (optional)
        website_emails = []
        if args.scrape_websites and website:
            print(f"  Scraping website: {website[:50]}...")
            website_emails = scrape_website_for_emails(website)
            if website_emails:
                print(f"  Found {len(website_emails)} email(s) from website: {website_emails}")
                if not email:
                    email = website_emails[0]
            time.sleep(1)

        # Build result
        result = {
            "#": row.get("#", ""),
            "Channel Name": name,
            "Subscribers": row.get("Subscribers", ""),
            "Videos": row.get("Videos", ""),
            "Total Views": row.get("Total Views", ""),
            "About / Niche": row.get("About / Niche", ""),
            "Channel URL": channel_url or "",
            "Email": email,
            "Website": website,
            "Twitter": twitter,
            "Instagram": instagram,
            "LinkedIn": linkedin,
            "TikTok": tiktok,
            "Other Links": "; ".join(all_links),
            "Website Emails": "; ".join(website_emails) if website_emails else "",
        }
        results.append(result)

        # Print summary
        found = []
        if email: found.append(f"email={email}")
        if website: found.append(f"web={website[:40]}")
        if twitter: found.append("twitter")
        if instagram: found.append("instagram")
        if linkedin: found.append("linkedin")
        if website_emails: found.append(f"site_emails={website_emails}")
        if found:
            print(f"  >> {', '.join(found)}")
        else:
            print(f"  >> No contact info found")

    # Write output CSV
    fieldnames = [
        "#", "Channel Name", "Subscribers", "Videos", "Total Views",
        "About / Niche", "Channel URL", "Email", "Website",
        "Twitter", "Instagram", "LinkedIn", "TikTok", "Other Links", "Website Emails",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    # Summary
    total = len(results)
    with_email = sum(1 for r in results if r["Email"])
    with_website = sum(1 for r in results if r["Website"])
    with_social = sum(1 for r in results if r["Twitter"] or r["Instagram"] or r["LinkedIn"])

    print(f"\n{'='*60}")
    print(f"  Done! Enriched {total} channels")
    print(f"  Emails found:   {with_email} ({100*with_email//max(total,1)}%)")
    print(f"  Websites found: {with_website} ({100*with_website//max(total,1)}%)")
    print(f"  Social links:   {with_social} ({100*with_social//max(total,1)}%)")
    print(f"  Output: {out_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
