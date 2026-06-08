#!/usr/bin/env python3
"""Load Ahrefs affiliate-filtered backlinks JSON into a campaign tab,
   then Firecrawl-scrape each survivor to detect Synthesia presence for tier classification.

Input JSON should come from `mcp__ahrefs__site-explorer-all-backlinks` with a where filter
on url_to substring (?via=, ?ref=, aff_id=, fpr=, etc.) and/or is_sponsored=true.

Filtering:
- Drop competitors (config.exclude_domains) and known AI tools (self-promo)
- Drop non-article page_type
- Drop non-English

Classification:
- Tier A: page mentions 'synthesia' in scraped markdown
- Tier B: doesn't mention Synthesia

The competitor's tracking URL (url_to) is preserved in the `broken_url` field as proof
of affiliation; anchor goes in `anchor_text`.

Usage:
  python3 apply_ahrefs_affiliate_backlinks.py <campaign> --file <ahrefs.json> --competitor <name>
                                              [--dry-run] [--no-scrape]
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from firecrawl import FirecrawlApp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sheets_helper import append_rows, ensure_master_sheet, sheet_url, update_summary  # noqa: E402
from filter_articles import is_article_url, classify as classify_article  # noqa: E402
from discover_competitor_affiliates import KNOWN_AI_TOOL_DOMAINS  # noqa: E402

ssl._create_default_https_context = ssl._create_unverified_context

PROJECT_ROOT = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects")
CONFIG_PATH = PROJECT_ROOT / "link-outreach" / "config.json"
FIRECRAWL_API_KEY = (PROJECT_ROOT / ".credentials" / "firecrawl-api-key.txt").read_text().strip()

SYNTHESIA_RE = re.compile(r"\bsynthesia\b", re.IGNORECASE)


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _domain(url: str) -> str:
    return (urlparse(url).netloc or "").lower()


def _root_domain(host: str) -> str:
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def check_synthesia(app: FirecrawlApp, url: str) -> bool | None:
    """True if Synthesia mentioned, False if scraped and not, None on scrape failure."""
    try:
        result = app.scrape(url, formats=["markdown"], only_main_content=True)
        md = (getattr(result, "markdown", None) or "").lower()
        return bool(SYNTHESIA_RE.search(md)) or "synthesia.io" in md
    except Exception:
        return None


def run(campaign: str, file_path: str, competitor: str, dry_run: bool, no_scrape: bool) -> int:
    cfg = load_config()
    exclude_domains: set[str] = set(cfg.get("exclude_domains", []))

    with open(file_path) as f:
        data = json.load(f)
    backlinks = data.get("backlinks", [])
    print(f"loaded {len(backlinks)} backlinks from {file_path}")

    # Pre-filter
    survivors: list[dict] = []
    drops = {"excluded": 0, "self_promo": 0, "non_english": 0, "non_article": 0, "dup": 0}
    seen: set[str] = set()
    for b in backlinks:
        url = (b.get("url_from") or "").strip().rstrip("/")
        if not url or url in seen:
            drops["dup"] += 1
            continue
        seen.add(url)
        root = (b.get("root_name_source") or "").lower()
        host = _domain(url)
        if (
            root in exclude_domains
            or host in exclude_domains
            or _root_domain(host) in exclude_domains
        ):
            drops["excluded"] += 1
            continue
        if (
            root in KNOWN_AI_TOOL_DOMAINS
            or host in KNOWN_AI_TOOL_DOMAINS
            or _root_domain(host) in KNOWN_AI_TOOL_DOMAINS
        ):
            drops["self_promo"] += 1
            continue
        langs = b.get("languages") or []
        if langs and "en" not in langs:
            drops["non_english"] += 1
            continue
        # Article-only filter via classify (handles page_type AND URL fallback)
        pt = b.get("page_type_source")
        keep, _reason = classify_article(url, pt)
        if not keep:
            drops["non_article"] += 1
            continue
        survivors.append(b)

    print(f"\nafter pre-filter: {len(survivors)} survive")
    for k, v in drops.items():
        print(f"  drop {k}: {v}")

    # Scrape each survivor for Synthesia presence (parallelized)
    # Also skip scraping during dry-run — no point burning Firecrawl credits on data we throw away
    if no_scrape or dry_run:
        synthesia_map = {b["url_from"]: None for b in survivors}
        msg = "[--dry-run] " if dry_run else "[--no-scrape] "
        print(f"\n{msg}skipping Synthesia presence detection — all rows → Tier B (placeholder)")
    else:
        print(f"\nscraping {len(survivors)} pages for Synthesia presence (concurrent=5)...")
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
        synthesia_map: dict[str, bool | None] = {}
        with ThreadPoolExecutor(max_workers=5) as ex:
            futs = {ex.submit(check_synthesia, app, b["url_from"]): b for b in survivors}
            done = 0
            for fut in as_completed(futs):
                b = futs[fut]
                result = fut.result()
                synthesia_map[b["url_from"]] = result
                done += 1
                if done % 25 == 0:
                    print(f"  scraped {done}/{len(survivors)}")
        n_yes = sum(1 for v in synthesia_map.values() if v is True)
        n_no = sum(1 for v in synthesia_map.values() if v is False)
        n_fail = sum(1 for v in synthesia_map.values() if v is None)
        print(f"  done. Synthesia mentioned: {n_yes}, not mentioned: {n_no}, scrape failed: {n_fail}")

    # Build rows
    today = date.today().isoformat()
    rows: list[dict] = []
    n_a, n_b = 0, 0
    for b in survivors:
        mentions = synthesia_map.get(b["url_from"])
        tier = "A" if mentions is True else "B"
        if tier == "A":
            n_a += 1
        else:
            n_b += 1
        rows.append({
            "source_technique": f"ahrefs:affiliate-tier-{tier.lower()}",
            "source_page": b["url_from"],
            "source_page_title": b.get("title") or "",
            "domain": _domain(b["url_from"]),
            "dr": int(b.get("domain_rating_source") or 0),
            "traffic": int(b.get("traffic_domain") or 0),
            "broken_url": b.get("url_to") or "",  # competitor tracking URL = proof
            "anchor_text": b.get("anchor") or "",
            "added_to_sequence": False,
            "email_sent": False,
            "enrichment_ran": False,
            "blocked_by_replyio": False,
            "excluded": False,
            "discovered_at": today,
        })

    print(f"\nfinal classification: Tier A: {n_a}, Tier B: {n_b}")

    if dry_run:
        print("\n[dry-run] no rows written.")
        return 0

    sid = ensure_master_sheet()
    n = append_rows(sid, campaign, rows)
    update_summary(sid, campaign)
    print(f"\nappended {n} new rows ({len(rows) - n} were already in the sheet)")
    print(f"sheet: {sheet_url(sid, campaign)}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("campaign")
    p.add_argument("--file", required=True)
    p.add_argument("--competitor", default="unknown")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-scrape", action="store_true")
    args = p.parse_args()
    return run(args.campaign, args.file, args.competitor, args.dry_run, args.no_scrape)


if __name__ == "__main__":
    sys.exit(main())
