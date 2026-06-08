#!/usr/bin/env python3
"""
Collect GSC data for a specific page:
1. Monthly trend (Dec 2024 - Mar 2026)
2. 3-month comparison snapshot (page-level)
3. Top 10 keywords comparison snapshot
"""

import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import date

# ── Config ──────────────────────────────────────────────────────────────────
CREDENTIALS_PATH = "/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gsc-service-account.json"
SITE_URL = "sc-domain:synthesia.io"
PAGE_URL = "https://www.synthesia.io/post/why-and-how-to-use-ai-for-training-and-development"
SCOPE = ["https://www.googleapis.com/auth/webmasters.readonly"]

# ── Auth ────────────────────────────────────────────────────────────────────
creds = service_account.Credentials.from_service_account_file(
    CREDENTIALS_PATH, scopes=SCOPE
)
service = build("searchconsole", "v1", credentials=creds)

# ── Helper ──────────────────────────────────────────────────────────────────
def query_gsc(start, end, dimensions, row_limit=25000):
    """Run a GSC searchAnalytics query filtered to PAGE_URL."""
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": dimensions,
        "dimensionFilterGroups": [{
            "filters": [{
                "dimension": "page",
                "operator": "equals",
                "expression": PAGE_URL
            }]
        }],
        "rowLimit": row_limit
    }
    resp = service.searchanalytics().query(siteUrl=SITE_URL, body=body).execute()
    return resp.get("rows", [])

def fmt_pct(val):
    """Format a percentage nicely."""
    if val is None:
        return "N/A"
    return f"{val:+.1f}%"

def fmt_num(val):
    return f"{val:,.0f}"

def delta_pct(current, previous):
    if previous == 0:
        return None
    return ((current - previous) / previous) * 100

# ── Month boundaries ────────────────────────────────────────────────────────
# Dec 2024 through Mar 2026
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

# ══════════════════════════════════════════════════════════════════════════════
# 1. PAGE-LEVEL MONTHLY TREND
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("1. PAGE-LEVEL MONTHLY TREND (Dec 2024 – Mar 2026)")
print("=" * 70)
print(f"{'Month':<12} {'Clicks':>10} {'Impressions':>14}")
print("-" * 38)

monthly_data = []
for start, end, label in months:
    rows = query_gsc(start, end, ["page"])
    clicks = sum(r["clicks"] for r in rows) if rows else 0
    impressions = sum(r["impressions"] for r in rows) if rows else 0
    monthly_data.append((label, clicks, impressions))
    print(f"{label:<12} {fmt_num(clicks):>10} {fmt_num(impressions):>14}")

print()

# ══════════════════════════════════════════════════════════════════════════════
# 2. COMPARISON SNAPSHOT (PAGE-LEVEL)
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("2. PAGE-LEVEL COMPARISON: Last 3 mo vs Previous 3 mo")
print("=" * 70)

# Last 3 months: Jan-Mar 2026
last3_start = "2026-01-01"
last3_end = "2026-03-31"
# Previous 3 months: Oct-Dec 2025
prev3_start = "2025-10-01"
prev3_end = "2025-12-31"

# Page-level totals
last3_page = query_gsc(last3_start, last3_end, ["page"])
prev3_page = query_gsc(prev3_start, prev3_end, ["page"])

last3_clicks = sum(r["clicks"] for r in last3_page) if last3_page else 0
last3_impr = sum(r["impressions"] for r in last3_page) if last3_page else 0
prev3_clicks = sum(r["clicks"] for r in prev3_page) if prev3_page else 0
prev3_impr = sum(r["impressions"] for r in prev3_page) if prev3_page else 0

# Unique queries count
last3_kw = query_gsc(last3_start, last3_end, ["query"])
prev3_kw = query_gsc(prev3_start, prev3_end, ["query"])
last3_queries = len(last3_kw)
prev3_queries = len(prev3_kw)

print(f"{'Metric':<22} {'Oct-Dec 2025':>14} {'Jan-Mar 2026':>14} {'Delta':>10}")
print("-" * 62)
print(f"{'Clicks':<22} {fmt_num(prev3_clicks):>14} {fmt_num(last3_clicks):>14} {fmt_pct(delta_pct(last3_clicks, prev3_clicks)):>10}")
print(f"{'Impressions':<22} {fmt_num(prev3_impr):>14} {fmt_num(last3_impr):>14} {fmt_pct(delta_pct(last3_impr, prev3_impr)):>10}")
print(f"{'Unique Queries':<22} {fmt_num(prev3_queries):>14} {fmt_num(last3_queries):>14} {fmt_pct(delta_pct(last3_queries, prev3_queries)):>10}")
print()

# ══════════════════════════════════════════════════════════════════════════════
# 3. PER-KEYWORD SNAPSHOT (TOP 10 BY CLICKS, LAST 3 MONTHS)
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("3. TOP 10 KEYWORDS BY CLICKS (Jan-Mar 2026) vs Oct-Dec 2025")
print("=" * 70)

# Sort last 3 months keywords by clicks, take top 10
last3_kw_sorted = sorted(last3_kw, key=lambda r: r["clicks"], reverse=True)[:10]
top_keywords = [r["keys"][0] for r in last3_kw_sorted]

# Build lookup for previous period
prev3_kw_dict = {}
for r in prev3_kw:
    prev3_kw_dict[r["keys"][0]] = r

for i, kw in enumerate(top_keywords, 1):
    last = next(r for r in last3_kw_sorted if r["keys"][0] == kw)
    prev = prev3_kw_dict.get(kw, {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0})

    l_clicks = last["clicks"]
    l_impr = last["impressions"]
    l_ctr = last["ctr"] * 100
    l_pos = last["position"]

    p_clicks = prev["clicks"] if isinstance(prev, dict) and "clicks" in prev else prev.get("clicks", 0)
    p_impr = prev["impressions"] if isinstance(prev, dict) and "impressions" in prev else prev.get("impressions", 0)
    p_ctr = (prev["ctr"] * 100) if prev.get("ctr") else 0
    p_pos = prev.get("position", 0)

    print(f"\n  #{i}: {kw}")
    print(f"  {'':4}{'Metric':<14} {'Oct-Dec 2025':>14} {'Jan-Mar 2026':>14} {'Delta':>12}")
    print(f"  {'':4}{'-'*56}")
    print(f"  {'':4}{'Clicks':<14} {fmt_num(p_clicks):>14} {fmt_num(l_clicks):>14} {fmt_pct(delta_pct(l_clicks, p_clicks)):>12}")
    print(f"  {'':4}{'Impressions':<14} {fmt_num(p_impr):>14} {fmt_num(l_impr):>14} {fmt_pct(delta_pct(l_impr, p_impr)):>12}")
    print(f"  {'':4}{'CTR':<14} {p_ctr:>13.1f}% {l_ctr:>13.1f}% {fmt_pct(l_ctr - p_ctr):>12}")
    # For position, lower is better, so invert the direction label
    pos_delta = p_pos - l_pos  # positive = improved
    pos_sign = "+" if pos_delta > 0 else ""
    pos_delta_str = f"{pos_sign}{pos_delta:.1f}" if p_pos > 0 else "N/A (new)"
    print(f"  {'':4}{'Avg Position':<14} {p_pos:>14.1f} {l_pos:>14.1f} {pos_delta_str:>12}")

print("\n" + "=" * 70)
print("Done.")
