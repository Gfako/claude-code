#!/usr/bin/env python3
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

CREDENTIALS_PATH = "/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gsc-service-account.json"
SITE_URL = "sc-domain:synthesia.io"
PAGE_URL = "https://www.synthesia.io/post/microlearning-videos"
SCOPE = ["https://www.googleapis.com/auth/webmasters.readonly"]

creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPE)
service = build("searchconsole", "v1", credentials=creds)

def query_gsc(start, end, dimensions, row_limit=25000):
    body = {
        "startDate": start, "endDate": end, "dimensions": dimensions,
        "dimensionFilterGroups": [{"filters": [{"dimension": "page", "operator": "equals", "expression": PAGE_URL}]}],
        "rowLimit": row_limit
    }
    resp = service.searchanalytics().query(siteUrl=SITE_URL, body=body).execute()
    return resp.get("rows", [])

def fmt_pct(val):
    if val is None: return "N/A"
    return f"{val:+.1f}%"

def fmt_num(val):
    return f"{val:,.0f}"

def delta_pct(current, previous):
    if previous == 0: return None
    return ((current - previous) / previous) * 100

months = [
    ("2024-12-01", "2024-12-31", "Dec 2024"),
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
]

print("=" * 70)
print(f"PAGE: {PAGE_URL}")
print("1. PAGE-LEVEL MONTHLY TREND (Dec 2024 – Mar 2026)")
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
print("2. PAGE-LEVEL COMPARISON: Last 3 mo vs Previous 3 mo")
print("=" * 70)

last3_start, last3_end = "2026-01-01", "2026-03-31"
prev3_start, prev3_end = "2025-10-01", "2025-12-31"

last3_page = query_gsc(last3_start, last3_end, ["page"])
prev3_page = query_gsc(prev3_start, prev3_end, ["page"])

last3_clicks = sum(r["clicks"] for r in last3_page) if last3_page else 0
last3_impr = sum(r["impressions"] for r in last3_page) if last3_page else 0
prev3_clicks = sum(r["clicks"] for r in prev3_page) if prev3_page else 0
prev3_impr = sum(r["impressions"] for r in prev3_page) if prev3_page else 0

last3_kw = query_gsc(last3_start, last3_end, ["query"])
prev3_kw = query_gsc(prev3_start, prev3_end, ["query"])

print(f"{'Metric':<22} {'Oct-Dec 2025':>14} {'Jan-Mar 2026':>14} {'Delta':>10}")
print("-" * 62)
print(f"{'Clicks':<22} {fmt_num(prev3_clicks):>14} {fmt_num(last3_clicks):>14} {fmt_pct(delta_pct(last3_clicks, prev3_clicks)):>10}")
print(f"{'Impressions':<22} {fmt_num(prev3_impr):>14} {fmt_num(last3_impr):>14} {fmt_pct(delta_pct(last3_impr, prev3_impr)):>10}")
print(f"{'Unique Queries':<22} {fmt_num(len(prev3_kw)):>14} {fmt_num(len(last3_kw)):>14} {fmt_pct(delta_pct(len(last3_kw), len(prev3_kw))):>10}")

print()
print("=" * 70)
print("3. TOP KEYWORDS (Jan-Mar 2026) vs Oct-Dec 2025")
print("=" * 70)

last3_kw_sorted = sorted(last3_kw, key=lambda r: r["clicks"], reverse=True)[:10]
prev3_kw_dict = {r["keys"][0]: r for r in prev3_kw}

for i, row in enumerate(last3_kw_sorted, 1):
    kw = row["keys"][0]
    prev = prev3_kw_dict.get(kw, {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0})
    l_clicks, l_impr = row["clicks"], row["impressions"]
    l_ctr, l_pos = row["ctr"] * 100, row["position"]
    p_clicks, p_impr = prev.get("clicks", 0), prev.get("impressions", 0)
    p_ctr = (prev.get("ctr") or 0) * 100
    p_pos = prev.get("position", 0)
    print(f"\n  #{i}: {kw}")
    print(f"  {'':4}{'Metric':<14} {'Prev':>10} {'Now':>10} {'Delta':>12}")
    print(f"  {'':4}{'Clicks':<14} {fmt_num(p_clicks):>10} {fmt_num(l_clicks):>10} {fmt_pct(delta_pct(l_clicks, p_clicks)):>12}")
    print(f"  {'':4}{'Impressions':<14} {fmt_num(p_impr):>10} {fmt_num(l_impr):>10} {fmt_pct(delta_pct(l_impr, p_impr)):>12}")
    print(f"  {'':4}{'CTR':<14} {p_ctr:>9.1f}% {l_ctr:>9.1f}% {fmt_pct(l_ctr - p_ctr):>12}")
    pos_delta = p_pos - l_pos
    pos_str = f"{'+' if pos_delta > 0 else ''}{pos_delta:.1f}" if p_pos > 0 else "N/A (new)"
    print(f"  {'':4}{'Avg Position':<14} {p_pos:>10.1f} {l_pos:>10.1f} {pos_str:>12}")

print("\nDone.")
