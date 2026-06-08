#!/usr/bin/env python3
"""Discover guest-post opportunities via Google search footprints.

Pipeline:
1. Firecrawl search for each footprint × topic-keyword combination
2. Dedupe URLs across queries
3. Filter:
   - Drop excluded domains (platforms / social / news / competitors)
   - Keep only URLs that look like guidelines pages (URL pattern OR title pattern)
4. Scrape each candidate to verify it IS a guest-post guidelines page:
   - Looks for keywords: "submit", "pitch", "guidelines", "we accept", "contribute", "contributor", "guest post"
   - Bonus signal: contains an email pattern (editor@, submit@, pitch@, contribute@)
5. (Later, via filter.py) hydrate DR via Ahrefs, filter DR ≥ threshold

Topic categories baked in (per user choice):
- SaaS / B2B marketing
- HR / training / sales enablement
- Video marketing / corporate video / e-learning

Usage:
  python3 discover_guest_posts.py [--campaign <slug>] [--limit-queries N]
                                  [--limit-scrape N] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from firecrawl import FirecrawlApp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sheets_helper import append_rows, ensure_master_sheet, sheet_url, update_summary  # noqa: E402
from discover_competitor_affiliates import KNOWN_AI_TOOL_DOMAINS, PLATFORM_HOSTS  # noqa: E402

ssl._create_default_https_context = ssl._create_unverified_context

PROJECT_ROOT = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects")
CONFIG_PATH = PROJECT_ROOT / "link-outreach" / "config.json"
FIRECRAWL_API_KEY = (PROJECT_ROOT / ".credentials" / "firecrawl-api-key.txt").read_text().strip()

# ─── search queries: footprint × topic ─────────────────────────────────
FOOTPRINTS = [
    '"write for us"',
    '"submit a guest post"',
    '"become a contributor"',
    '"guest post guidelines"',
    '"contributor guidelines"',
    'intitle:"write for us"',
    'inurl:write-for-us',
    'inurl:contribute',
    'inurl:guest-post',
]

TOPIC_KEYWORDS = {
    "saas_b2b": [
        "SaaS",
        "B2B marketing",
        "B2B SaaS",
        "growth marketing",
        "content marketing",
        "SaaS marketing",
    ],
    "hr_training_sales": [
        "HR tech",
        "learning and development",
        "sales enablement",
        "employee training",
        "corporate training",
        "instructional design",
    ],
    "video": [
        "video marketing",
        "e-learning",
        "online courses",
        "corporate video",
    ],
}

# URL-pattern signal that a page is a guidelines page
GUIDELINES_URL_RE = re.compile(
    r"/(write[-_]for[-_]us|contribute|guest[-_]post|guest[-_]blog"
    r"|submit[-_](a[-_])?guest|guest[-_]author|guidelines|become[-_]a[-_]contributor|submissions?)\b",
    re.IGNORECASE,
)

# Content signals: phrases that confirm the page actually accepts submissions
ACCEPTANCE_PHRASES = [
    "submit a guest post", "submit your guest post", "submit an article",
    "we accept guest posts", "we accept contributions", "we welcome guest posts",
    "guest blogging guidelines", "guest post guidelines", "contributor guidelines",
    "become a contributor", "become a guest", "join our contributors",
    "pitch your idea", "pitch us", "pitch your article",
    "submission guidelines",
]
ACCEPTANCE_RE = re.compile("|".join(re.escape(p) for p in ACCEPTANCE_PHRASES), re.IGNORECASE)
EMAIL_PATTERN_RE = re.compile(r"(editor|submit|submissions?|pitch|contribute|contributors?)@", re.IGNORECASE)

# Reject signals — pay-to-play / link-farm language
SPAMMY_PHRASES = [
    "buy guest post", "premium guest post", "pbn", "link insertion",
    "paid guest post", "guest post service", "starting at $", "from $",
]
SPAMMY_RE = re.compile("|".join(re.escape(p) for p in SPAMMY_PHRASES), re.IGNORECASE)


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _domain(url: str) -> str:
    return (urlparse(url).netloc or "").lower()


def _root_domain(host: str) -> str:
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def _host_matches_exclude(host: str, exclude: set[str]) -> bool:
    if host in exclude:
        return True
    parts = host.split(".")
    for i in range(len(parts) - 1):
        if ".".join(parts[i:]) in exclude:
            return True
    return False


def build_queries(topics: list[str] | None = None) -> list[str]:
    if topics is None:
        topics = list(TOPIC_KEYWORDS.keys())
    queries: list[str] = []
    for t in topics:
        for kw in TOPIC_KEYWORDS.get(t, []):
            # Pair each topic kw with a subset of footprints to keep query count manageable
            for fp in FOOTPRINTS:
                queries.append(f'{fp} "{kw}"')
    # Dedupe
    return list(dict.fromkeys(queries))


def firecrawl_search(app: FirecrawlApp, query: str, limit: int = 10) -> list[dict]:
    resp = app.search(query, limit=limit)
    out = []
    for r in getattr(resp, "web", []) or []:
        url = getattr(r, "url", None)
        title = getattr(r, "title", None) or ""
        if url:
            out.append({"url": url, "title": title, "query": query})
    return out


def scrape(app: FirecrawlApp, url: str) -> tuple[str, str] | None:
    try:
        result = app.scrape(url, formats=["markdown"], only_main_content=False)
        md = (getattr(result, "markdown", None) or "")
        meta = getattr(result, "metadata", None) or {}
        title = ""
        if meta:
            title = getattr(meta, "title", None) or (meta.get("title") if isinstance(meta, dict) else "") or ""
        return title, md
    except Exception:
        return None


def verify_guidelines_page(markdown: str) -> tuple[bool, str]:
    """Return (is_guidelines, reason). Confirms page genuinely accepts guest posts."""
    if not markdown:
        return False, "empty"
    md_lower = markdown.lower()
    if SPAMMY_RE.search(md_lower):
        return False, "spammy"
    accept = ACCEPTANCE_RE.search(md_lower)
    email = EMAIL_PATTERN_RE.search(md_lower)
    if accept and email:
        return True, "accept_phrase+email"
    if accept:
        return True, "accept_phrase"
    if email and "guest" in md_lower:
        return True, "email+guest_keyword"
    return False, "no_clear_acceptance"


def is_likely_guidelines_url(url: str, title: str = "") -> bool:
    """URL or title pattern matching guidelines page."""
    if GUIDELINES_URL_RE.search(url):
        return True
    t = title.lower()
    if any(p in t for p in ("write for us", "guest post", "contributor", "contribute", "become a guest", "submission guidelines", "submit a guest", "submit a post")):
        return True
    return False


def run(campaign: str, topics: list[str] | None, limit_queries: int | None, limit_scrape: int | None, dry_run: bool) -> int:
    cfg = load_config()
    exclude_domains: set[str] = set(cfg.get("exclude_domains", [])) | PLATFORM_HOSTS | KNOWN_AI_TOOL_DOMAINS

    queries = build_queries(topics)
    if limit_queries:
        queries = queries[:limit_queries]
    print(f"=== guest-post discovery ===")
    print(f"campaign:    {campaign}")
    print(f"queries:     {len(queries)}")

    app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

    # 1. Search
    print(f"\n[1/4] Firecrawl search ({len(queries)} queries)...")
    all_results: dict[str, dict] = {}
    for i, q in enumerate(queries, 1):
        hits = firecrawl_search(app, q, limit=10)
        for h in hits:
            u = h["url"].split("#", 1)[0]
            if u in all_results:
                all_results[u]["queries"].append(q)
            else:
                all_results[u] = {"url": u, "title": h["title"], "queries": [q]}
        if i % 10 == 0 or i == len(queries):
            print(f"  [{i}/{len(queries)}] total unique URLs: {len(all_results)}")
        time.sleep(0.3)

    # 2. Pre-filter
    print(f"\n[2/4] Pre-filtering URLs...")
    candidates = []
    skipped = {"excluded": 0, "url_pattern_miss": 0}
    for u, info in all_results.items():
        host = _domain(u)
        if _host_matches_exclude(host, exclude_domains):
            skipped["excluded"] += 1
            continue
        # Must look like a guidelines page (URL pattern OR title pattern)
        if not is_likely_guidelines_url(u, info.get("title", "")):
            skipped["url_pattern_miss"] += 1
            continue
        candidates.append(info)
    print(f"  {len(all_results)} URLs → {len(candidates)} pre-filtered candidates")
    print(f"  excluded: {skipped['excluded']}, URL-pattern miss: {skipped['url_pattern_miss']}")

    if limit_scrape:
        candidates = candidates[:limit_scrape]
        print(f"  limited to {len(candidates)} for scraping")

    # 3. Scrape + verify
    print(f"\n[3/4] Scraping + verifying {len(candidates)} candidates (concurrent=8)...")
    today = date.today().isoformat()
    new_rows: list[dict] = []
    stats = {"scrape_fail": 0, "spammy": 0, "no_acceptance": 0, "verified": 0}

    def process(info):
        result = scrape(app, info["url"])
        if not result:
            return info, None, "scrape_fail"
        title, md = result
        is_g, reason = verify_guidelines_page(md)
        return info, (title or info.get("title", "")), (None if is_g else reason)

    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(process, c) for c in candidates]
        done = 0
        for fut in as_completed(futs):
            info, title, fail_reason = fut.result()
            done += 1
            if fail_reason:
                stats[fail_reason if fail_reason in stats else "no_acceptance"] += 1
                if done % 25 == 0:
                    print(f"  processed {done}/{len(candidates)}")
                continue
            stats["verified"] += 1
            new_rows.append({
                "source_technique": "guest-post:footprint",
                "source_page": info["url"],
                "source_page_title": title or info.get("title", ""),
                "domain": _domain(info["url"]),
                "anchor_text": "|".join(info.get("queries", []))[:200],
                "added_to_sequence": False,
                "email_sent": False,
                "enrichment_ran": False,
                "blocked_by_replyio": False,
                "excluded": False,
                "discovered_at": today,
            })
            if done % 25 == 0:
                print(f"  processed {done}/{len(candidates)}  ({stats['verified']} verified so far)")

    print(f"\nstats: {stats}")

    if dry_run:
        print(f"\n[dry-run] {len(new_rows)} rows would land in '{campaign}'")
        for r in new_rows[:10]:
            print(f"  {r['domain']:35}  {r['source_page'][:80]}")
        return 0

    if not new_rows:
        print("\nno rows to append.")
        return 0

    print(f"\n[4/4] Writing {len(new_rows)} verified guidelines pages to master sheet...")
    sid = ensure_master_sheet()
    n = append_rows(sid, campaign, new_rows)
    update_summary(sid, campaign)
    print(f"  appended {n} (dedup skipped {len(new_rows) - n})")
    print(f"\nsheet: {sheet_url(sid, campaign)}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--campaign", default="guest-posts")
    p.add_argument("--topics", nargs="*", default=None,
                   help="topic keys: saas_b2b hr_training_sales video")
    p.add_argument("--limit-queries", type=int, default=None)
    p.add_argument("--limit-scrape", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    return run(args.campaign, args.topics, args.limit_queries, args.limit_scrape, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
