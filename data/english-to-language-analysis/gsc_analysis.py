#!/usr/bin/env python3
"""Pull 6-month GSC metrics + top queries for all english-to-X pages."""

import json
import csv
from google.oauth2 import service_account
from googleapiclient.discovery import build

CREDENTIALS_PATH = "/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gsc-service-account.json"
SITE_URL = "sc-domain:synthesia.io"
SCOPE = ["https://www.googleapis.com/auth/webmasters.readonly"]
OUT_DIR = "/Users/george.fakorellis/Desktop/SEO Custom Projects/english-to-language-analysis"

# Last 6 months: 2025-11-18 to 2026-05-17
# Prior 6 months for comparison: 2025-05-18 to 2025-11-17
LAST_START, LAST_END = "2025-11-18", "2026-05-17"
PRIOR_START, PRIOR_END = "2025-05-18", "2025-11-17"

# Last 3 months vs prior 3 months for momentum signal
RECENT_START, RECENT_END = "2026-02-18", "2026-05-17"
PRECEDING_START, PRECEDING_END = "2025-11-18", "2026-02-17"

creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPE)
service = build("searchconsole", "v1", credentials=creds)


def query_gsc(start, end, dimensions, page=None, row_limit=25000):
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": dimensions,
        "rowLimit": row_limit,
    }
    if page:
        body["dimensionFilterGroups"] = [{
            "filters": [{"dimension": "page", "operator": "equals", "expression": page}]
        }]
    else:
        body["dimensionFilterGroups"] = [{
            "filters": [{"dimension": "page", "operator": "contains",
                         "expression": "/video-translator/english-to-"}]
        }]
    resp = service.searchanalytics().query(siteUrl=SITE_URL, body=body).execute()
    return resp.get("rows", [])


# 1) Get full page list with last-6mo + prior-6mo + recent-3mo + preceding-3mo metrics
print("Pulling page-level metrics across all 4 windows...")

last6_pages = query_gsc(LAST_START, LAST_END, ["page"])
prior6_pages = query_gsc(PRIOR_START, PRIOR_END, ["page"])
recent3_pages = query_gsc(RECENT_START, RECENT_END, ["page"])
preceding3_pages = query_gsc(PRECEDING_START, PRECEDING_END, ["page"])


def to_map(rows):
    return {r["keys"][0]: r for r in rows}


m_last6 = to_map(last6_pages)
m_prior6 = to_map(prior6_pages)
m_recent3 = to_map(recent3_pages)
m_preceding3 = to_map(preceding3_pages)

# Union of all english-to-X URLs that appeared in any window
all_urls = set(m_last6) | set(m_prior6) | set(m_recent3) | set(m_preceding3)
all_urls = sorted(u for u in all_urls if "/video-translator/english-to-" in u)
print(f"Total unique english-to-X URLs across windows: {len(all_urls)}")


def lang_from(url):
    return url.rsplit("english-to-", 1)[-1].strip("/")


def get(m, url, key, default=0):
    r = m.get(url)
    return r[key] if r else default


# 2) Aggregate per page
summary = []
for url in all_urls:
    lang = lang_from(url)
    row = {
        "language": lang,
        "url": url,
        "last6_clicks": get(m_last6, url, "clicks"),
        "last6_impr": get(m_last6, url, "impressions"),
        "last6_ctr": get(m_last6, url, "ctr"),
        "last6_pos": get(m_last6, url, "position"),
        "prior6_clicks": get(m_prior6, url, "clicks"),
        "prior6_impr": get(m_prior6, url, "impressions"),
        "prior6_ctr": get(m_prior6, url, "ctr"),
        "prior6_pos": get(m_prior6, url, "position"),
        "recent3_clicks": get(m_recent3, url, "clicks"),
        "recent3_impr": get(m_recent3, url, "impressions"),
        "recent3_ctr": get(m_recent3, url, "ctr"),
        "recent3_pos": get(m_recent3, url, "position"),
        "preceding3_clicks": get(m_preceding3, url, "clicks"),
        "preceding3_impr": get(m_preceding3, url, "impressions"),
        "preceding3_ctr": get(m_preceding3, url, "ctr"),
        "preceding3_pos": get(m_preceding3, url, "position"),
    }
    # Deltas
    def pct(curr, prev):
        if prev == 0:
            return None
        return (curr - prev) / prev * 100

    row["delta_clicks_6mo_pct"] = pct(row["last6_clicks"], row["prior6_clicks"])
    row["delta_impr_6mo_pct"] = pct(row["last6_impr"], row["prior6_impr"])
    row["delta_pos_6mo"] = (row["prior6_pos"] - row["last6_pos"]) if row["prior6_pos"] else None  # +ve = improved
    row["delta_clicks_3mo_pct"] = pct(row["recent3_clicks"], row["preceding3_clicks"])
    row["delta_pos_3mo"] = (row["preceding3_pos"] - row["recent3_pos"]) if row["preceding3_pos"] else None
    summary.append(row)

# Sort by last6 clicks desc
summary.sort(key=lambda r: r["last6_clicks"], reverse=True)

# 3) Pull top queries per page (last 6 months)
print("Pulling top queries per page...")
queries_by_page = {}
for url in all_urls:
    rows = query_gsc(LAST_START, LAST_END, ["query"], page=url)
    rows = sorted(rows, key=lambda r: r["clicks"], reverse=True)
    queries_by_page[url] = [
        {
            "query": r["keys"][0],
            "clicks": r["clicks"],
            "impressions": r["impressions"],
            "ctr": r["ctr"],
            "position": r["position"],
        }
        for r in rows
    ]

# 4) Save outputs
with open(f"{OUT_DIR}/page_summary.json", "w") as f:
    json.dump(summary, f, indent=2)

with open(f"{OUT_DIR}/queries_by_page.json", "w") as f:
    json.dump(queries_by_page, f, indent=2)

# CSV for quick scan
with open(f"{OUT_DIR}/page_summary.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
    w.writeheader()
    w.writerows(summary)

# Print page summary table
print("\n=== PAGE SUMMARY (Last 6 months) ===")
print(f"{'Language':<15} {'Clicks':>7} {'Impr':>8} {'CTR':>6} {'Pos':>5} | "
      f"{'Δ Clicks':>9} {'Δ Pos':>7} | {'3mo Δ Clicks':>13} {'3mo Δ Pos':>10}")
print("-" * 110)
for r in summary:
    dc = f"{r['delta_clicks_6mo_pct']:+.0f}%" if r['delta_clicks_6mo_pct'] is not None else "  N/A"
    dp = f"{r['delta_pos_6mo']:+.1f}" if r['delta_pos_6mo'] is not None else "  N/A"
    dc3 = f"{r['delta_clicks_3mo_pct']:+.0f}%" if r['delta_clicks_3mo_pct'] is not None else "  N/A"
    dp3 = f"{r['delta_pos_3mo']:+.1f}" if r['delta_pos_3mo'] is not None else "  N/A"
    ctr_pct = r['last6_ctr'] * 100
    print(f"{r['language']:<15} {r['last6_clicks']:>7.0f} {r['last6_impr']:>8.0f} "
          f"{ctr_pct:>5.1f}% {r['last6_pos']:>5.1f} | {dc:>9} {dp:>7} | {dc3:>13} {dp3:>10}")

# Aggregate totals
total_last6_clicks = sum(r["last6_clicks"] for r in summary)
total_last6_impr = sum(r["last6_impr"] for r in summary)
total_prior6_clicks = sum(r["prior6_clicks"] for r in summary)
total_prior6_impr = sum(r["prior6_impr"] for r in summary)
print("-" * 110)
print(f"{'TOTAL':<15} {total_last6_clicks:>7.0f} {total_last6_impr:>8.0f}")
print(f"\nClicks YoH (6mo vs prior 6mo): {total_last6_clicks:.0f} vs {total_prior6_clicks:.0f} "
      f"({(total_last6_clicks - total_prior6_clicks) / max(total_prior6_clicks, 1) * 100:+.1f}%)")
print(f"Impr YoH (6mo vs prior 6mo): {total_last6_impr:.0f} vs {total_prior6_impr:.0f} "
      f"({(total_last6_impr - total_prior6_impr) / max(total_prior6_impr, 1) * 100:+.1f}%)")

print(f"\nSaved page_summary.json, page_summary.csv, queries_by_page.json")
