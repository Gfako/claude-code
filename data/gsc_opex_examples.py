#!/usr/bin/env python3
"""GSC data for /post/operational-excellence-examples"""

import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

CREDENTIALS_PATH = "/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gsc-service-account.json"
SITE_URL = "sc-domain:synthesia.io"
PAGE_URL = "https://www.synthesia.io/post/operational-excellence-examples"
SCOPE = ["https://www.googleapis.com/auth/webmasters.readonly"]

creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPE)
service = build("searchconsole", "v1", credentials=creds)

def query_gsc(start, end, dimensions, row_limit=25000):
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": dimensions,
        "dimensionFilterGroups": [{"filters": [{"dimension": "page", "operator": "equals", "expression": PAGE_URL}]}],
        "rowLimit": row_limit
    }
    return service.searchanalytics().query(siteUrl=SITE_URL, body=body).execute().get("rows", [])

def fmt_pct(val):
    if val is None: return "N/A"
    return f"{val:+.1f}%"

def fmt_num(val): return f"{val:,.0f}"

def delta_pct(c, p):
    if p == 0: return None
    return ((c - p) / p) * 100

months = [
    ("2025-01-01", "2025-01-31", "Jan 2025"),
    ("2025-02-01", "2025-02-28", "Feb 2025"),
    ("2025-03-01", "2025-03-31", "Mar 2025"),
    ("2025-04-01", "2025-04-30", "Apr 2025"),
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
    ("2026-04-01", "2026-04-27", "Apr 2026"),
]

print("=" * 70)
print("PAGE-LEVEL MONTHLY TREND")
print("=" * 70)
print(f"{'Month':<12} {'Clicks':>10} {'Impressions':>14}")
print("-" * 38)
for start, end, label in months:
    rows = query_gsc(start, end, ["page"])
    clicks = sum(r["clicks"] for r in rows) if rows else 0
    impressions = sum(r["impressions"] for r in rows) if rows else 0
    print(f"{label:<12} {fmt_num(clicks):>10} {fmt_num(impressions):>14}")

print()
print("=" * 70)
print("PAGE-LEVEL: Last 3 mo vs Previous 3 mo")
print("=" * 70)

last3_start, last3_end = "2026-02-01", "2026-04-27"
prev3_start, prev3_end = "2025-11-01", "2026-01-31"

last3_page = query_gsc(last3_start, last3_end, ["page"])
prev3_page = query_gsc(prev3_start, prev3_end, ["page"])

last3_clicks = sum(r["clicks"] for r in last3_page) if last3_page else 0
last3_impr = sum(r["impressions"] for r in last3_page) if last3_page else 0
prev3_clicks = sum(r["clicks"] for r in prev3_page) if prev3_page else 0
prev3_impr = sum(r["impressions"] for r in prev3_page) if prev3_page else 0

last3_kw = query_gsc(last3_start, last3_end, ["query"])
prev3_kw = query_gsc(prev3_start, prev3_end, ["query"])
last3_queries = len(last3_kw)
prev3_queries = len(prev3_kw)

print(f"{'Metric':<22} {'Prev 3mo':>14} {'Last 3mo':>14} {'Delta':>10}")
print("-" * 62)
print(f"{'Clicks':<22} {fmt_num(prev3_clicks):>14} {fmt_num(last3_clicks):>14} {fmt_pct(delta_pct(last3_clicks, prev3_clicks)):>10}")
print(f"{'Impressions':<22} {fmt_num(prev3_impr):>14} {fmt_num(last3_impr):>14} {fmt_pct(delta_pct(last3_impr, prev3_impr)):>10}")
print(f"{'Unique Queries':<22} {fmt_num(prev3_queries):>14} {fmt_num(last3_queries):>14} {fmt_pct(delta_pct(last3_queries, prev3_queries)):>10}")

print()
print("=" * 70)
print("TOP 10 KEYWORDS BY CLICKS (Last 3 mo)")
print("=" * 70)

last3_kw_sorted = sorted(last3_kw, key=lambda r: r["clicks"], reverse=True)[:10]
top_keywords = [r["keys"][0] for r in last3_kw_sorted]

prev3_kw_dict = {r["keys"][0]: r for r in prev3_kw}

for i, kw in enumerate(top_keywords, 1):
    last = next(r for r in last3_kw_sorted if r["keys"][0] == kw)
    prev = prev3_kw_dict.get(kw, {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0})

    l_clicks, l_impr = last["clicks"], last["impressions"]
    l_ctr, l_pos = last["ctr"] * 100, last["position"]

    p_clicks = prev.get("clicks", 0)
    p_impr = prev.get("impressions", 0)
    p_ctr = (prev.get("ctr", 0) or 0) * 100
    p_pos = prev.get("position", 0) or 0

    print(f"\n  #{i}: {kw}")
    print(f"      Clicks:      {fmt_num(p_clicks):>10} -> {fmt_num(l_clicks):>10}  ({fmt_pct(delta_pct(l_clicks, p_clicks))})")
    print(f"      Impressions: {fmt_num(p_impr):>10} -> {fmt_num(l_impr):>10}  ({fmt_pct(delta_pct(l_impr, p_impr))})")
    print(f"      CTR:         {p_ctr:>9.1f}% -> {l_ctr:>9.1f}%  ({fmt_pct(l_ctr - p_ctr)})")
    pos_delta = p_pos - l_pos
    pos_sign = "+" if pos_delta > 0 else ""
    pos_delta_str = f"{pos_sign}{pos_delta:.1f}" if p_pos > 0 else "new"
    print(f"      Position:    {p_pos:>10.1f} -> {l_pos:>10.1f}  ({pos_delta_str})")

print("\nDone.")
