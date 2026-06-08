#!/usr/bin/env python3
"""
Pull contacts from AirOps grid, filter (Mentions Synthesia = No + has email),
and push to Reply.io campaign 1664426.
"""

import json
import time
import requests
import glob
import os
from datetime import datetime

# --- Config ---
CAMPAIGN_ID = 1664426
API_KEY_PATH = "/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/reply-io-api-key.txt"
TOOL_RESULTS_DIR = "/Users/george.fakorellis/.claude/projects/-Users-george-fakorellis-Desktop-SEO-Custom-Projects/0c9ece3e-a64c-4f7c-bafd-8962e9e4f914/tool-results"
OUTPUT_LOG = "/Users/george.fakorellis/Desktop/SEO Custom Projects/link-outreach/campaigns/hourone-broken-links/replyio-no-mention-push-log.json"

# The last chunk (offset=500) was returned inline, so we embed it
LAST_CHUNK_PATH = None  # Will be loaded from inline data below

def load_api_key():
    with open(API_KEY_PATH, "r") as f:
        return f.read().strip()

def load_grid_rows():
    """Load all rows from the latest batch of tool result files + inline last chunk."""
    # Find the latest batch files (timestamps starting with 17763509...)
    pattern = os.path.join(TOOL_RESULTS_DIR, "mcp-airops-read_grid-177635096*.txt")
    files = sorted(glob.glob(pattern))

    print(f"Found {len(files)} tool result files matching latest batch")

    all_rows = []
    offsets_loaded = set()

    for f in files:
        with open(f, "r") as fh:
            data = json.load(fh)
            offset = data["offset"]
            if offset not in offsets_loaded:
                all_rows.extend(data["rows"])
                offsets_loaded.add(offset)
                print(f"  Loaded offset {offset}: {len(data['rows'])} rows")

    # Load inline last chunk (offset 500, 39 rows)
    last_chunk_file = os.path.join(TOOL_RESULTS_DIR, "mcp-airops-read_grid-1776350965751.txt")
    # Actually the offset 500 chunk was returned inline. Let's check if we have it in files
    if 500 not in offsets_loaded:
        print("  Offset 500 not found in files, will load from inline data")

    print(f"\nTotal rows loaded from files: {len(all_rows)}")
    print(f"Offsets loaded: {sorted(offsets_loaded)}")

    return all_rows

def extract_contact(row):
    """Extract standardized contact fields from a row."""
    return {
        "company": row.get("Company", ""),
        "domain": row.get("Domain", ""),
        "first_name": row.get("First Name", ""),
        "last_name": row.get("Last Name", ""),
        "email": row.get("Email", ""),
        "position": row.get("Position", ""),
        "url": row.get("URL", ""),
        "article_topic": row.get("Article Topic", ""),
        "outreach_track": row.get("Outreach Track", ""),
        "dr": row.get("DR", ""),
        "synthesia_target_url": row.get("Synthesia Target URL", "https://www.synthesia.io"),
        "mentions_synthesia": row.get("Mentions Synthesia", ""),
        "page_type": row.get("Page Type", ""),
        "total_broken_links": row.get("Total Broken Links", ""),
    }

def filter_contacts(contacts):
    """Keep only: Mentions Synthesia = No (or blank) AND email is not blank."""
    no_mention = []
    has_email = []
    no_email = []
    mentions_yes = []

    for c in contacts:
        mention_val = c["mentions_synthesia"].strip().lower()
        email_val = c["email"].strip()

        if mention_val == "yes":
            mentions_yes.append(c)
            continue

        # Treat blank/empty/"no" as No
        no_mention.append(c)

        if email_val:
            has_email.append(c)
        else:
            no_email.append(c)

    return has_email, no_mention, no_email, mentions_yes

def push_to_replyio(contacts, api_key):
    """Push filtered contacts to Reply.io campaign."""
    url = "https://api.reply.io/v1/actions/addandpushtocampaign"
    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json"
    }

    results = []
    success_count = 0
    fail_count = 0

    for i, c in enumerate(contacts):
        first_name = c["first_name"].strip() if c["first_name"].strip() else "there"
        last_name = c["last_name"].strip()

        payload = {
            "campaignId": CAMPAIGN_ID,
            "firstName": first_name,
            "lastName": last_name,
            "email": c["email"].strip(),
            "company": c["company"].strip(),
            "customFields": [
                {"key": "article_url", "value": c["url"]},
                {"key": "article_topic", "value": c["article_topic"]},
                {"key": "synthesia_target_page", "value": c["synthesia_target_url"] or "https://www.synthesia.io"},
                {"key": "total_broken_links", "value": str(c["total_broken_links"])},
                {"key": "outreach_track", "value": c["outreach_track"]},
                {"key": "page_type", "value": c["page_type"]}
            ]
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code in (200, 201, 204):
                status = "success"
                error_msg = None
                success_count += 1
            else:
                status = "failed"
                error_msg = f"HTTP {resp.status_code}: {resp.text[:500]}"
                fail_count += 1
        except Exception as e:
            status = "failed"
            error_msg = str(e)
            fail_count += 1

        result_entry = {
            "index": i + 1,
            "email": c["email"],
            "company": c["company"],
            "first_name": first_name,
            "last_name": last_name,
            "status": status,
            "error": error_msg
        }
        results.append(result_entry)

        status_icon = "OK" if status == "success" else "FAIL"
        print(f"  [{i+1}/{len(contacts)}] {status_icon} - {c['email']} ({c['company']}){' - ' + error_msg if error_msg else ''}")

        # 0.5 second delay between calls
        if i < len(contacts) - 1:
            time.sleep(0.5)

    return results, success_count, fail_count

def main():
    print("=" * 60)
    print("Reply.io Push: No-Mention Contacts from AirOps Grid 64369")
    print("=" * 60)
    print()

    # Load API key
    api_key = load_api_key()
    print(f"API key loaded: {api_key[:8]}...")
    print()

    # Load all rows from files
    all_rows = load_grid_rows()

    # Load the inline last chunk (offset 500) - we'll read it from a separate file
    last_chunk_path = "/Users/george.fakorellis/Desktop/SEO Custom Projects/link-outreach/campaigns/hourone-broken-links/offset500_inline.json"
    if os.path.exists(last_chunk_path):
        with open(last_chunk_path, "r") as f:
            last_chunk = json.load(f)
            all_rows.extend(last_chunk)
            print(f"  Loaded offset 500 inline chunk: {len(last_chunk)} rows")

    print(f"\nTotal rows: {len(all_rows)}")

    # Extract contacts
    contacts = [extract_contact(row) for row in all_rows]

    # Filter
    eligible, no_mention_all, no_email, mentions_yes = filter_contacts(contacts)

    print(f"\n--- Filter Summary ---")
    print(f"Total rows:              {len(contacts)}")
    print(f"Mentions Synthesia=Yes:  {len(mentions_yes)}")
    print(f"Mentions Synthesia=No:   {len(no_mention_all)} (includes blank)")
    print(f"  - With email:          {len(eligible)}")
    print(f"  - Without email:       {len(no_email)}")
    print(f"\nContacts to push:        {len(eligible)}")
    print()

    if not eligible:
        print("No contacts to push. Exiting.")
        return

    # Push to Reply.io
    print("--- Pushing to Reply.io ---")
    print(f"Campaign ID: {CAMPAIGN_ID}")
    print()

    results, success_count, fail_count = push_to_replyio(eligible, api_key)

    # Build log
    log = {
        "timestamp": datetime.now().isoformat(),
        "campaign_id": CAMPAIGN_ID,
        "grid_id": 64369,
        "grid_table_id": 83240,
        "filter": "Mentions Synthesia != Yes AND Email not blank",
        "total_rows_in_grid": len(contacts),
        "mentions_yes_count": len(mentions_yes),
        "no_mention_count": len(no_mention_all),
        "no_mention_with_email": len(eligible),
        "no_mention_without_email": len(no_email),
        "total_pushed": len(results),
        "successes": success_count,
        "failures": fail_count,
        "results": results
    }

    # Save log
    os.makedirs(os.path.dirname(OUTPUT_LOG), exist_ok=True)
    with open(OUTPUT_LOG, "w") as f:
        json.dump(log, f, indent=2)

    print(f"\n--- Push Summary ---")
    print(f"Total pushed:  {len(results)}")
    print(f"Successes:     {success_count}")
    print(f"Failures:      {fail_count}")
    print(f"\nLog saved to: {OUTPUT_LOG}")

    if fail_count > 0:
        print(f"\n--- Failed Contacts ---")
        for r in results:
            if r["status"] == "failed":
                print(f"  {r['email']} - {r['error']}")

if __name__ == "__main__":
    main()
