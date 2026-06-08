#!/usr/bin/env python3
"""Analyze the top queries data: patterns, top performers, untapped opportunities."""

import json
from collections import Counter, defaultdict

with open("/Users/george.fakorellis/Desktop/SEO Custom Projects/english-to-language-analysis/queries_by_page.json") as f:
    qbp = json.load(f)

# 1) For each page, print top 5 queries
print("=" * 100)
print("TOP 5 QUERIES PER PAGE (last 6 months)")
print("=" * 100)

for url, queries in sorted(qbp.items(), key=lambda x: -sum(q["clicks"] for q in x[1])):
    lang = url.rsplit("english-to-", 1)[-1].strip("/")
    total_clicks = sum(q["clicks"] for q in queries)
    total_impr = sum(q["impressions"] for q in queries)
    print(f"\n--- {lang.upper()} ({total_clicks} clicks, {total_impr} impr, {len(queries)} unique queries) ---")
    for q in queries[:5]:
        ctr = q["ctr"] * 100
        print(f"  {q['clicks']:>4.0f} clk | {q['impressions']:>6.0f} impr | "
              f"{ctr:>5.1f}% CTR | pos {q['position']:>5.1f} | {q['query']}")

# 2) Find common query patterns
print("\n" + "=" * 100)
print("COMMON QUERY PATTERNS")
print("=" * 100)

all_queries = []
for url, queries in qbp.items():
    for q in queries:
        all_queries.append({**q, "lang": url.rsplit("english-to-", 1)[-1].strip("/")})

# Pattern detection by checking which tokens appear most often
tokens = Counter()
for q in all_queries:
    for t in q["query"].lower().split():
        tokens[t] += 1

print("\nMost common tokens across all queries:")
for t, c in tokens.most_common(30):
    print(f"  {c:>4}  {t}")

# 3) High-impression / low-CTR opportunities
print("\n" + "=" * 100)
print("HIGH IMPRESSIONS, LOW CTR (CTR < 1% AND IMPR >= 200)")
print("=" * 100)
candidates = [q for q in all_queries if q["impressions"] >= 200 and q["ctr"] < 0.01]
candidates.sort(key=lambda q: -q["impressions"])
for q in candidates[:30]:
    ctr = q["ctr"] * 100
    print(f"  {q['impressions']:>5.0f} impr | {q['clicks']:>3.0f} clk | "
          f"{ctr:>4.1f}% CTR | pos {q['position']:>5.1f} | {q['lang']:<12} | {q['query']}")

# 4) Position 4-15 = opportunity to push to top 3
print("\n" + "=" * 100)
print("OPPORTUNITY: POSITION 4-15 WITH >=50 IMPR (push these to top 3)")
print("=" * 100)
opportunities = [q for q in all_queries if 4 <= q["position"] <= 15 and q["impressions"] >= 50]
opportunities.sort(key=lambda q: -q["impressions"])
for q in opportunities[:30]:
    ctr = q["ctr"] * 100
    print(f"  pos {q['position']:>5.1f} | {q['impressions']:>5.0f} impr | "
          f"{q['clicks']:>3.0f} clk | {ctr:>4.1f}% CTR | {q['lang']:<12} | {q['query']}")

# 5) Pages with high impressions but very low clicks (canonical "underperforming")
print("\n" + "=" * 100)
print("WORST CTR PAGES (impr >= 500)")
print("=" * 100)
page_totals = []
for url, queries in qbp.items():
    clicks = sum(q["clicks"] for q in queries)
    impr = sum(q["impressions"] for q in queries)
    ctr = (clicks / impr) if impr else 0
    page_totals.append({
        "lang": url.rsplit("english-to-", 1)[-1].strip("/"),
        "url": url,
        "clicks": clicks,
        "impr": impr,
        "ctr": ctr,
    })
page_totals.sort(key=lambda p: p["ctr"])
for p in page_totals:
    if p["impr"] >= 500:
        print(f"  {p['ctr']*100:>4.1f}% CTR | {p['impr']:>6.0f} impr | "
              f"{p['clicks']:>4.0f} clk | {p['lang']}")
