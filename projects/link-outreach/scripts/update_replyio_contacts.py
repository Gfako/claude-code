#!/usr/bin/env python3
"""
Update existing Reply.io contacts with full data from AirOps grid.
Fixes: first_name, last_name, position, and adds missing custom fields.
"""

import json
import urllib.request
import urllib.error
import ssl
import time

ssl._create_default_https_context = ssl._create_unverified_context

REPLY_IO_API_KEY = "hZY3nAQBsVgt40QjBJBiL9WV"
PUSH_DATA_FILE = "/Users/george.fakorellis/Desktop/SEO Custom Projects/link-outreach/campaigns/niche-edits/2026-04-08-video-translator/replyio-update-data.json"

def update_contact(email, data):
    # Use addandpushtocampaign with forcePush to update custom fields
    # Determine the right campaign based on fit strength
    fit = data.get("custom_fields", {}).get("fit_strength", "")
    campaign_id = 1659743 if fit in ("strong", "medium") else 1660542

    payload = {
        "campaignId": campaign_id,
        "email": email,
        "firstName": data.get("first_name", ""),
        "lastName": data.get("last_name", ""),
        "company": data.get("company", ""),
        "title": data.get("position", ""),
        "forcePush": True,
        "customFields": [{"key": k, "value": str(v)} for k, v in data.get("custom_fields", {}).items() if v]
    }

    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        "https://api.reply.io/v1/actions/addandpushtocampaign",
        data=body,
        headers={'Content-Type': 'application/json', 'x-api-key': REPLY_IO_API_KEY},
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return {"status": "success"}
    except urllib.error.HTTPError as e:
        msg = e.read().decode('utf-8') if e.fp else ''
        return {"status": "error", "code": e.code, "message": msg[:200]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def main():
    with open(PUSH_DATA_FILE) as f:
        contacts = json.load(f)

    print(f"Updating {len(contacts)} contacts in Reply.io...")

    ok = 0
    err = 0
    skip = 0

    for i, c in enumerate(contacts):
        email = c.get("email", "")
        if not email:
            skip += 1
            continue

        result = update_contact(email, c)
        if result["status"] == "success":
            ok += 1
            if (i + 1) % 25 == 0:
                print(f"  [{i+1}/{len(contacts)}] {ok} updated, {err} errors")
        else:
            err += 1
            print(f"  [{i+1}/{len(contacts)}] ERR: {email} — {result.get('message', '')[:80]}")

        time.sleep(0.3)

    print(f"\nDone. Updated: {ok} | Errors: {err} | Skipped: {skip}")

if __name__ == "__main__":
    main()
