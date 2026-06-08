#!/usr/bin/env python3
"""Find when each english-to-X page started showing impressions."""

import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

CREDENTIALS_PATH = "/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gsc-service-account.json"
SITE_URL = "sc-domain:synthesia.io"
SCOPE = ["https://www.googleapis.com/auth/webmasters.readonly"]

creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPE)
service = build("searchconsole", "v1", credentials=creds)

# Monthly breakdown for whole english-to-X cluster
months = [
    ("2025-05-01", "2025-05-31", "May 2025"),
    ("2025-06-01", "2025-06-30", "Jun 2025"),
    ("2025-07-01", "2025-07-31", "Jul 2025"),
    ("2025-08-01", "2025-08-31", "Aug 2025"),
    ("2025-09-01", "2025-09-30", "Sep 2025"),
    ("2025-10-01", "2025-10-31", "Oct 2025"),
    ("2025-11-01", "2025-11-30", "Nov 2025"),
    ("2025-12-01", "2025-12-31", "Dec 2025"),
    ("2026-01-01", "2026-01-31", "Jan 2026"),
    ("2026-02-01", "2026-02-28", "Feb 2026"),
    ("2026-03-01", "2026-03-31", "Mar 2026"),
    ("2026-04-01", "2026-04-30", "Apr 2026"),
    ("2026-05-01", "2026-05-17", "May 2026 (mtd)"),
]

print(f"{'Month':<18} {'Clicks':>8} {'Impr':>9} {'Unique URLs':>12}")
print("-" * 50)

for start, end, label in months:
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": ["page"],
        "dimensionFilterGroups": [{
            "filters": [{
                "dimension": "page",
                "operator": "contains",
                "expression": "/video-translator/english-to-"
            }]
        }],
        "rowLimit": 5000,
    }
    resp = service.searchanalytics().query(siteUrl=SITE_URL, body=body).execute()
    rows = resp.get("rows", [])
    clicks = sum(r["clicks"] for r in rows)
    impr = sum(r["impressions"] for r in rows)
    print(f"{label:<18} {clicks:>8.0f} {impr:>9.0f} {len(rows):>12}")
