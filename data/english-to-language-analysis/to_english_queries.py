#!/usr/bin/env python3
"""Top queries pre/post Mar 2026 for the 3 X-to-english pages."""

import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

CREDENTIALS_PATH = "/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gsc-service-account.json"
SITE_URL = "sc-domain:synthesia.io"
SCOPE = ["https://www.googleapis.com/auth/webmasters.readonly"]

creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPE)
service = build("searchconsole", "v1", credentials=creds)

pages = [
    "https://www.synthesia.io/features/video-translator/spanish-to-english",
    "https://www.synthesia.io/features/video-translator/french-to-english",
    "https://www.synthesia.io/features/video-translator/japanese-to-english",
]


def query_gsc(start, end, page):
    body = {
        "startDate": start, "endDate": end, "dimensions": ["query"],
        "dimensionFilterGroups": [{"filters": [{"dimension": "page", "operator": "equals", "expression": page}]}],
        "rowLimit": 50,
    }
    return service.searchanalytics().query(siteUrl=SITE_URL, body=body).execute().get("rows", [])


# Pre = Sep 2025 - Feb 2026; Post = Mar - May 17 2026
for page in pages:
    print(f"\n{'=' * 100}")
    print(page)
    print('=' * 100)

    pre = query_gsc("2025-09-01", "2026-02-28", page)
    post = query_gsc("2026-03-01", "2026-05-17", page)

    pre_map = {r["keys"][0]: r for r in pre}
    post_map = {r["keys"][0]: r for r in post}

    pre_sorted = sorted(pre, key=lambda r: -r["clicks"])[:10]
    post_sorted = sorted(post, key=lambda r: -r["clicks"])[:10]

    print("\nPRE-LAUNCH TOP 10 QUERIES (Sep '25 - Feb '26)")
    print(f"{'Q':<60} {'Clk':>5} {'Imp':>6} {'CTR':>6} {'Pos':>5}")
    for r in pre_sorted:
        print(f"{r['keys'][0][:58]:<60} {r['clicks']:>5.0f} {r['impressions']:>6.0f} "
              f"{r['ctr']*100:>5.1f}% {r['position']:>5.1f}")

    print("\nPOST-LAUNCH TOP 10 QUERIES (Mar - May 17 '26)")
    print(f"{'Q':<60} {'Clk':>5} {'Imp':>6} {'CTR':>6} {'Pos':>5}  Δpos")
    for r in post_sorted:
        prev = pre_map.get(r["keys"][0])
        pos_delta = ""
        if prev:
            d = prev["position"] - r["position"]
            pos_delta = f" {d:+.1f}"
        print(f"{r['keys'][0][:58]:<60} {r['clicks']:>5.0f} {r['impressions']:>6.0f} "
              f"{r['ctr']*100:>5.1f}% {r['position']:>5.1f}{pos_delta}")

    # New queries that only appeared post-launch
    new_queries = [r for r in post_sorted if r["keys"][0] not in pre_map and r["clicks"] >= 1]
    if new_queries:
        print(f"\nNEW post-launch queries (not in pre period, clicks >= 1):")
        for r in new_queries[:10]:
            print(f"  +{r['clicks']:.0f} clk @ pos {r['position']:.1f} | {r['keys'][0]}")
