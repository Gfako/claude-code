#!/usr/bin/env python3
"""Discover all video-translator language-pair pages from GSC (last 6 months)."""

import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

CREDENTIALS_PATH = "/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gsc-service-account.json"
SITE_URL = "sc-domain:synthesia.io"
SCOPE = ["https://www.googleapis.com/auth/webmasters.readonly"]

creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPE)
service = build("searchconsole", "v1", credentials=creds)

# Try several URL patterns to find where english-to-X pages live
patterns = [
    "/features/video-translator/",
    "/tools/translate-",
    "/features/dubbing/",
    "english-to-",
    "translate-english",
]

for pattern in patterns:
    body = {
        "startDate": "2025-11-18",
        "endDate": "2026-05-17",
        "dimensions": ["page"],
        "dimensionFilterGroups": [{
            "filters": [{
                "dimension": "page",
                "operator": "contains",
                "expression": pattern
            }]
        }],
        "rowLimit": 5000
    }
    resp = service.searchanalytics().query(siteUrl=SITE_URL, body=body).execute()
    rows = resp.get("rows", [])
    print(f"\n=== Pattern '{pattern}': {len(rows)} pages ===")
    for r in sorted(rows, key=lambda x: x["clicks"], reverse=True)[:30]:
        page = r["keys"][0]
        print(f"  {r['clicks']:>6.0f} clicks | {r['impressions']:>8.0f} impr | {page}")
