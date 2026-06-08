#!/usr/bin/env python3
"""
1) Pinpoint the english-to-X cluster launch date (daily impressions, March 2026).
2) Pull weekly trajectory for the 3 X-to-english pages, Jan - May 2026.
3) Compare pre/post mid-March correlation.
"""

import json
from datetime import date, timedelta
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


# 1) Daily impressions for english-to-X cluster, all of March 2026
print("=" * 70)
print("english-to-X cluster: DAILY impressions, March 2026")
print("=" * 70)
rows = query_gsc("2026-03-01", "2026-03-31", ["date"], contains="/video-translator/english-to-")
rows = sorted(rows, key=lambda r: r["keys"][0])
first_day_with_impressions = None
for r in rows:
    d = r["keys"][0]
    if r["impressions"] > 0 and first_day_with_impressions is None:
        first_day_with_impressions = d
    print(f"  {d}: {int(r['clicks']):>4} clk  {int(r['impressions']):>5} impr")

print(f"\nFirst day with cluster impressions: {first_day_with_impressions}")

# 2) Weekly trajectory for X-to-english pages, Jan 1 - May 17 2026
pages = [
    ("spanish-to-english", "https://www.synthesia.io/features/video-translator/spanish-to-english"),
    ("french-to-english", "https://www.synthesia.io/features/video-translator/french-to-english"),
    ("japanese-to-english", "https://www.synthesia.io/features/video-translator/japanese-to-english"),
]

# Build week buckets: ISO week, Monday start
def week_buckets(start_date, end_date):
    """Yield (week_start, week_end, label) tuples for ISO weeks within range."""
    # Adjust to Monday
    d = start_date - timedelta(days=start_date.weekday())
    buckets = []
    while d <= end_date:
        wstart = d
        wend = min(d + timedelta(days=6), end_date)
        label = f"W{wstart.isocalendar()[1]:02d} ({wstart.strftime('%b %d')})"
        buckets.append((wstart.isoformat(), wend.isoformat(), label))
        d += timedelta(days=7)
    return buckets


buckets = week_buckets(date(2026, 1, 5), date(2026, 5, 17))

# 3) Pull each X-to-english page weekly + cluster aggregate weekly
all_weekly = {}
for slug, url in pages:
    print(f"\n=== Weekly trajectory: {slug} ===")
    print(f"{'Week':<22} {'Clk':>5} {'Impr':>6} {'CTR':>6} {'Pos':>6}")
    all_weekly[slug] = []
    for wstart, wend, label in buckets:
        r = query_gsc(wstart, wend, ["page"], page=url)
        if r:
            row = r[0]
            ctr = row["ctr"] * 100
            print(f"{label:<22} {int(row['clicks']):>5} {int(row['impressions']):>6} "
                  f"{ctr:>5.1f}% {row['position']:>6.1f}")
            all_weekly[slug].append({"week": label, "wstart": wstart, "clicks": row["clicks"],
                                     "impr": row["impressions"], "ctr": row["ctr"], "pos": row["position"]})
        else:
            print(f"{label:<22} {'0':>5} {'0':>6} {'-':>6} {'-':>6}")
            all_weekly[slug].append({"week": label, "wstart": wstart, "clicks": 0,
                                     "impr": 0, "ctr": 0, "pos": 0})

# Cluster-level (3 pages combined) weekly
print(f"\n=== Weekly trajectory: X-to-english CLUSTER (Spanish + French + Japanese) ===")
print(f"{'Week':<22} {'Clk':>5} {'Impr':>6}")
cluster_weekly = []
for wstart, wend, label in buckets:
    total_clk = 0
    total_impr = 0
    for slug, url in pages:
        r = query_gsc(wstart, wend, ["page"], page=url)
        if r:
            total_clk += r[0]["clicks"]
            total_impr += r[0]["impressions"]
    print(f"{label:<22} {int(total_clk):>5} {int(total_impr):>6}")
    cluster_weekly.append({"week": label, "wstart": wstart, "clicks": total_clk, "impr": total_impr})

# 4) Same window but for the english-to-X cluster, to overlay launch
print(f"\n=== Weekly trajectory: NEW english-to-X cluster (26 pages) ===")
print(f"{'Week':<22} {'Clk':>5} {'Impr':>6} {'Active pages':>12}")
english_to_x_weekly = []
for wstart, wend, label in buckets:
    rows = query_gsc(wstart, wend, ["page"], contains="/video-translator/english-to-")
    total_clk = sum(r["clicks"] for r in rows)
    total_impr = sum(r["impressions"] for r in rows)
    active = len([r for r in rows if r["impressions"] > 0])
    print(f"{label:<22} {int(total_clk):>5} {int(total_impr):>6} {active:>12}")
    english_to_x_weekly.append({"week": label, "wstart": wstart, "clicks": total_clk,
                                "impr": total_impr, "active_pages": active})

# Save all
out = {
    "first_cluster_impression_date": first_day_with_impressions,
    "x_to_english_weekly": all_weekly,
    "x_to_english_cluster_weekly": cluster_weekly,
    "english_to_x_weekly": english_to_x_weekly,
}
with open("/Users/george.fakorellis/Desktop/SEO Custom Projects/english-to-language-analysis/weekly_data.json", "w") as f:
    json.dump(out, f, indent=2)
print("\nSaved weekly_data.json")
