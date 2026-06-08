#!/usr/bin/env python3
"""
Find all X-to-english pages and analyze monthly trajectory Sep 2025 - May 2026,
to detect any uplift after the english-to-X cluster launched in Mar 2026.
"""

import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

CREDENTIALS_PATH = "/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gsc-service-account.json"
SITE_URL = "sc-domain:synthesia.io"
SCOPE = ["https://www.googleapis.com/auth/webmasters.readonly"]

creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPE)
service = build("searchconsole", "v1", credentials=creds)


def query_gsc(start, end, dimensions, contains=None, page=None, row_limit=25000):
    body = {"startDate": start, "endDate": end, "dimensions": dimensions, "rowLimit": row_limit}
    filters = []
    if contains:
        filters.append({"dimension": "page", "operator": "contains", "expression": contains})
    if page:
        filters.append({"dimension": "page", "operator": "equals", "expression": page})
    if filters:
        body["dimensionFilterGroups"] = [{"filters": filters}]
    resp = service.searchanalytics().query(siteUrl=SITE_URL, body=body).execute()
    return resp.get("rows", [])


# 1) Discover all X-to-english pages (try widest window)
print("=== Discovering all X-to-english pages (last 12 months) ===")
rows = query_gsc("2025-05-18", "2026-05-17", ["page"], contains="-to-english")
to_english_pages = sorted([r["keys"][0] for r in rows
                           if "/video-translator/" in r["keys"][0] and r["keys"][0].endswith("-to-english")])
for r in sorted(rows, key=lambda x: -x["clicks"]):
    p = r["keys"][0]
    if "-to-english" in p:
        print(f"  {r['clicks']:>5.0f} clk | {r['impressions']:>7.0f} impr | pos {r['position']:>5.1f} | {p}")

# Filter to canonical X-to-english pages
to_english_pages = [p for p in to_english_pages if p.endswith("-to-english")]
print(f"\n{len(to_english_pages)} X-to-english pages discovered")

# 2) Monthly trajectory per page (Sep 2025 to May 2026)
months = [
    ("2025-09-01", "2025-09-30", "Sep 2025"),
    ("2025-10-01", "2025-10-31", "Oct 2025"),
    ("2025-11-01", "2025-11-30", "Nov 2025"),
    ("2025-12-01", "2025-12-31", "Dec 2025"),
    ("2026-01-01", "2026-01-31", "Jan 2026"),
    ("2026-02-01", "2026-02-28", "Feb 2026"),
    ("2026-03-01", "2026-03-31", "Mar 2026 (launch)"),
    ("2026-04-01", "2026-04-30", "Apr 2026"),
    ("2026-05-01", "2026-05-17", "May 2026 (mtd)"),
]

print("\n=== Monthly trajectory per page ===")
trajectory = {}
for page in to_english_pages:
    print(f"\n--- {page} ---")
    print(f"{'Month':<20} {'Clicks':>7} {'Impr':>8} {'CTR':>6} {'Pos':>5}")
    trajectory[page] = []
    for start, end, label in months:
        rows = query_gsc(start, end, ["page"], page=page)
        if rows:
            r = rows[0]
            ctr = r["ctr"] * 100
            print(f"{label:<20} {r['clicks']:>7.0f} {r['impressions']:>8.0f} {ctr:>5.1f}% {r['position']:>5.1f}")
            trajectory[page].append({"month": label, "clicks": r["clicks"], "impr": r["impressions"],
                                     "ctr": r["ctr"], "pos": r["position"]})
        else:
            print(f"{label:<20} {'0':>7} {'0':>8} {'-':>6} {'-':>5}")
            trajectory[page].append({"month": label, "clicks": 0, "impr": 0, "ctr": 0, "pos": 0})

# 3) Aggregate cluster monthly trajectory
print("\n=== AGGREGATE X-to-english cluster monthly ===")
print(f"{'Month':<20} {'Clicks':>7} {'Impr':>8} {'Pages':>6}")
agg = {}
for start, end, label in months:
    total_clk = 0
    total_impr = 0
    page_count = 0
    for page in to_english_pages:
        rows = query_gsc(start, end, ["page"], page=page)
        if rows:
            total_clk += rows[0]["clicks"]
            total_impr += rows[0]["impressions"]
            if rows[0]["impressions"] > 0:
                page_count += 1
    agg[label] = {"clicks": total_clk, "impr": total_impr, "pages_with_data": page_count}
    print(f"{label:<20} {total_clk:>7.0f} {total_impr:>8.0f} {page_count:>6}")

# 4) Pre/post comparison
print("\n=== PRE vs POST english-to-X launch (Mar 2026) ===")
# Pre = Sep 2025 - Feb 2026 (6 months)
# Post = Mar 2026 - May 17 2026 (~2.5 months) — normalize per-month
pre_clk = sum(agg[m]["clicks"] for m in ["Sep 2025", "Oct 2025", "Nov 2025", "Dec 2025", "Jan 2026", "Feb 2026"])
pre_impr = sum(agg[m]["impr"] for m in ["Sep 2025", "Oct 2025", "Nov 2025", "Dec 2025", "Jan 2026", "Feb 2026"])
post_clk = sum(agg[m]["clicks"] for m in ["Mar 2026 (launch)", "Apr 2026", "May 2026 (mtd)"])
post_impr = sum(agg[m]["impr"] for m in ["Mar 2026 (launch)", "Apr 2026", "May 2026 (mtd)"])
# Per-month normalization: pre = 6 months, post = ~2.55 months (Mar full + Apr full + 17/31 of May)
pre_months = 6
post_months = 1 + 1 + 17/31
print(f"Pre-launch (Sep '25 – Feb '26, {pre_months} mo):   {pre_clk:>5} clicks / {pre_impr:>6} impr  "
      f"=> {pre_clk/pre_months:.0f} clk/mo, {pre_impr/pre_months:.0f} impr/mo")
print(f"Post-launch (Mar '26 – May 17 '26, {post_months:.2f} mo): {post_clk:>5} clicks / {post_impr:>6} impr  "
      f"=> {post_clk/post_months:.0f} clk/mo, {post_impr/post_months:.0f} impr/mo")
print(f"Per-month delta: clicks {((post_clk/post_months) - (pre_clk/pre_months)) / max(pre_clk/pre_months, 1) * 100:+.1f}%, "
      f"impr {((post_impr/post_months) - (pre_impr/pre_months)) / max(pre_impr/pre_months, 1) * 100:+.1f}%")

# Save
with open("/Users/george.fakorellis/Desktop/SEO Custom Projects/english-to-language-analysis/to_english_trajectory.json", "w") as f:
    json.dump({"trajectory": trajectory, "aggregate": agg}, f, indent=2)
print("\nSaved to_english_trajectory.json")
