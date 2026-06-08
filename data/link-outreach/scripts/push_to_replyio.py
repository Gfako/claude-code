#!/usr/bin/env python3
"""
Push enriched contacts from AirOps grid to Reply.io sequences.
- Strong + Medium fit → Free Synthesia Plan Offer (ID: 1659743)
- Weak + No fit → Convert Article to Video (ID: 1660542)
"""

import json
import urllib.request
import urllib.error
import time
import sys

# Config
REPLY_IO_API_KEY = "hZY3nAQBsVgt40QjBJBiL9WV"
REPLY_IO_BASE = "https://api.reply.io/v1"

SEQUENCE_FREE_PLAN = 1659743
SEQUENCE_CONVERT_VIDEO = 1660542

AIROPS_GRID_EXPORT = "/Users/george.fakorellis/Desktop/SEO Custom Projects/link-outreach/campaigns/niche-edits/2026-04-08-video-translator/replyio-push-data.json"
LOG_FILE = "/Users/george.fakorellis/Desktop/SEO Custom Projects/link-outreach/campaigns/niche-edits/2026-04-08-video-translator/reply-io-push-log.json"

def push_contact(campaign_id, email, first_name, last_name, company, position, custom_fields):
    """Push a single contact to a Reply.io sequence."""
    payload = {
        "campaignId": campaign_id,
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
        "company": company,
        "title": position,
        "customFields": [{"key": k, "value": v} for k, v in custom_fields.items() if v]
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        f"{REPLY_IO_BASE}/actions/addandpushtocampaign",
        data=data,
        headers={
            'Content-Type': 'application/json',
            'x-api-key': REPLY_IO_API_KEY
        },
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
    with open(AIROPS_GRID_EXPORT) as f:
        contacts = json.load(f)

    print(f"Total contacts to push: {len(contacts)}")

    # Split by sequence
    free_plan = [c for c in contacts if c["sequence"] == "free_plan_offer"]
    convert_video = [c for c in contacts if c["sequence"] == "convert_article_to_video"]

    print(f"  Free Synthesia Plan Offer: {len(free_plan)}")
    print(f"  Convert Article to Video: {len(convert_video)}")

    log = {"pushed": [], "errors": [], "skipped": []}

    for i, contact in enumerate(contacts):
        email = contact.get("email", "")
        if not email:
            log["skipped"].append({"domain": contact.get("domain"), "reason": "no email"})
            continue

        campaign_id = SEQUENCE_FREE_PLAN if contact["sequence"] == "free_plan_offer" else SEQUENCE_CONVERT_VIDEO

        result = push_contact(
            campaign_id=campaign_id,
            email=email,
            first_name=contact.get("first_name", ""),
            last_name=contact.get("last_name", ""),
            company=contact.get("company", ""),
            position=contact.get("position", ""),
            custom_fields=contact.get("custom_fields", {})
        )

        if result["status"] == "success":
            log["pushed"].append({"email": email, "domain": contact.get("domain"), "sequence": contact["sequence"]})
            print(f"  [{i+1}/{len(contacts)}] OK: {email} → {contact['sequence']}")
        else:
            log["errors"].append({"email": email, "domain": contact.get("domain"), "error": result})
            print(f"  [{i+1}/{len(contacts)}] ERROR: {email} — {result.get('message', result.get('code', ''))}")

        time.sleep(0.3)  # Rate limiting

    # Save log
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

    print(f"\n{'='*50}")
    print(f"DONE")
    print(f"  Pushed: {len(log['pushed'])}")
    print(f"  Errors: {len(log['errors'])}")
    print(f"  Skipped (no email): {len(log['skipped'])}")
    print(f"  Log saved to: {LOG_FILE}")


if __name__ == "__main__":
    main()
