#!/usr/bin/env python3
"""
Read enriched contacts from AirOps grid CSV export and push to Reply.io sequences.
- Strong + Medium fit → Free Synthesia Plan Offer (ID: 1659743)
- Everything else → Convert Article to Video (ID: 1660542)

Usage:
  1. Export the AirOps grid as CSV
  2. Run: python3 read_and_push_replyio.py <path_to_csv>
  OR: python3 read_and_push_replyio.py  (uses default analyzed.json + grid data)
"""

import json
import csv
import urllib.request
import urllib.error
import ssl
import time
import sys
import os

# Fix macOS SSL certificate issue
ssl._create_default_https_context = ssl._create_unverified_context

REPLY_IO_API_KEY = "hZY3nAQBsVgt40QjBJBiL9WV"
SEQUENCE_FREE_PLAN = 1659743       # strong + medium → Free Synthesia Plan Offer
SEQUENCE_CONVERT_VIDEO = 1660542   # weak + no_fit + weak_for_translator → Convert Article to Video

CAMPAIGN_DIR = "/Users/george.fakorellis/Desktop/SEO Custom Projects/link-outreach/campaigns/niche-edits/2026-04-08-video-translator"
LOG_FILE = f"{CAMPAIGN_DIR}/reply-io-push-log.json"
PUSH_DATA_FILE = f"{CAMPAIGN_DIR}/replyio-push-data.json"

SYNTHESIA_URL = "https://www.synthesia.io/features/video-translator"

# Fit strengths that go to Free Plan sequence
FREE_PLAN_FITS = {"strong", "medium"}
# Everything else goes to Convert Video sequence

def push_contact(campaign_id, email, first_name, last_name, company, position, custom_fields):
    payload = {
        "campaignId": campaign_id,
        "email": email,
        "firstName": first_name or "",
        "lastName": last_name or "",
        "company": company or "",
        "title": position or "",
        "customFields": [{"key": k, "value": str(v)} for k, v in custom_fields.items() if v]
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        f"https://api.reply.io/v1/actions/addandpushtocampaign",
        data=data,
        headers={'Content-Type': 'application/json', 'x-api-key': REPLY_IO_API_KEY},
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return {"status": "success", "code": response.status}
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else ''
        return {"status": "error", "code": e.code, "message": body[:200]}
    except Exception as e:
        return {"status": "error", "code": 0, "message": str(e)}


def main():
    # Load push data
    if not os.path.exists(PUSH_DATA_FILE):
        print(f"ERROR: {PUSH_DATA_FILE} not found.")
        print("Run the data assembly step first.")
        sys.exit(1)

    with open(PUSH_DATA_FILE) as f:
        contacts = json.load(f)

    # Split by sequence based on fit_strength
    free_plan = [c for c in contacts if c.get("fit_strength") in FREE_PLAN_FITS]
    convert_video = [c for c in contacts if c.get("fit_strength") not in FREE_PLAN_FITS]

    print(f"Total contacts: {len(contacts)}")
    print(f"  → Free Synthesia Plan Offer (strong+medium): {len(free_plan)}")
    print(f"  → Convert Article to Video (weak+no_fit+other): {len(convert_video)}")
    print()

    log = {"free_plan_pushed": [], "convert_video_pushed": [], "errors": [], "skipped": []}

    for i, contact in enumerate(contacts):
        email = contact.get("email", "").strip()
        if not email:
            log["skipped"].append({"domain": contact.get("domain", ""), "reason": "no email"})
            continue

        fit = contact.get("fit_strength", "")
        if fit in FREE_PLAN_FITS:
            campaign_id = SEQUENCE_FREE_PLAN
            sequence_name = "free_plan"
        else:
            campaign_id = SEQUENCE_CONVERT_VIDEO
            sequence_name = "convert_video"

        custom_fields = {
            "article_topic": contact.get("article_topic", ""),
            "prospect_url": contact.get("url", ""),
            "synthesia_url": SYNTHESIA_URL,
            "suggested_anchor_text": contact.get("suggested_anchor_text", ""),
            "fit_strength": fit,
        }

        result = push_contact(
            campaign_id=campaign_id,
            email=email,
            first_name=contact.get("first_name", ""),
            last_name=contact.get("last_name", ""),
            company=contact.get("company", ""),
            position=contact.get("position", ""),
            custom_fields=custom_fields
        )

        if result["status"] == "success":
            log[f"{sequence_name}_pushed"].append({
                "email": email, "domain": contact.get("domain", ""), "fit": fit
            })
            print(f"  [{i+1}/{len(contacts)}] OK → {sequence_name}: {email}")
        else:
            log["errors"].append({
                "email": email, "domain": contact.get("domain", ""),
                "sequence": sequence_name, "error": result
            })
            print(f"  [{i+1}/{len(contacts)}] ERR → {sequence_name}: {email} — {result.get('message', '')[:80]}")

        time.sleep(0.3)

    # Save log
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

    print(f"\n{'='*50}")
    print(f"DONE")
    print(f"  Free Plan Offer pushed: {len(log['free_plan_pushed'])}")
    print(f"  Convert Video pushed: {len(log['convert_video_pushed'])}")
    print(f"  Errors: {len(log['errors'])}")
    print(f"  Skipped (no email): {len(log['skipped'])}")
    print(f"  Log: {LOG_FILE}")


if __name__ == "__main__":
    main()
