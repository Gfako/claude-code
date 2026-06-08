#!/usr/bin/env python3
"""Load Ahrefs all-backlinks / broken-backlinks JSON into a campaign tab.

The Ahrefs MCP call is made by Claude in the skill flow; this script just takes
the JSON output and writes filtered article rows to the master sheet.

Filtering applied:
- exclude_domains from config
- platform/aggregator hosts (notion.site, webflow.io, etc.)
- non-English pages (language tag != 'en' when set)
- non-article pages via filter_articles classifier (Ahrefs page_type_source + URL fallback)

Usage:
  python3 apply_ahrefs_backlinks.py <campaign> --file <ahrefs.json> \
      [--technique ahrefs:backlinks-defunct] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sheets_helper import append_rows, ensure_master_sheet, sheet_url, update_summary  # noqa: E402
from filter_articles import classify, _normalize  # noqa: E402

PROJECT_ROOT = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects")
CONFIG_PATH = PROJECT_ROOT / "link-outreach" / "config.json"

PLATFORM_HOSTS_EXCLUDE = {
    "notion.site", "webflow.io", "framer.website", "bio.site", "tilda.ws",
    "vercel.app", "netlify.app", "wixsite.com", "squarespace.com",
    "blogspot.com", "wordpress.com", "github.io",
    "substack.com", "medium.com",
    "t.me", "telegram.me", "twitter.com", "x.com", "facebook.com",
    "linkedin.com", "instagram.com", "pinterest.com",
}


def _domain(url: str) -> str:
    from urllib.parse import urlparse
    return (urlparse(url).netloc or "").lower()


def _root(host: str) -> str:
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def load(campaign: str, file_path: str, technique: str, dry_run: bool) -> int:
    with open(file_path) as f:
        data = json.load(f)
    backlinks = data.get("backlinks", [])
    print(f"loaded {len(backlinks)} backlinks from {file_path}")

    cfg = json.load(open(CONFIG_PATH))
    excl: set[str] = set(cfg.get("exclude_domains", [])) | PLATFORM_HOSTS_EXCLUDE

    today = date.today().isoformat()
    kept: list[dict] = []
    drops = {"excluded_domain": 0, "non_english": 0, "not_article": 0, "duplicate": 0}
    seen = set()
    for b in backlinks:
        url_from = b.get("url_from") or ""
        if not url_from:
            continue
        url_from_norm = _normalize(url_from)
        if url_from_norm in seen:
            drops["duplicate"] += 1
            continue
        seen.add(url_from_norm)

        host = _domain(url_from)
        root = _root(host)
        rn = (b.get("root_name_source") or "").lower()
        if host in excl or root in excl or rn in excl:
            drops["excluded_domain"] += 1
            continue

        langs = b.get("languages") or []
        if langs and "en" not in langs:
            drops["non_english"] += 1
            continue

        page_type = b.get("page_type_source")
        keep, _reason = classify(url_from, page_type)
        if not keep:
            drops["not_article"] += 1
            continue

        kept.append({
            "source_technique": technique,
            "source_page": url_from,
            "source_page_title": b.get("title") or "",
            "domain": rn,
            "dr": int(b.get("domain_rating_source") or 0),
            "traffic": int(b.get("traffic_domain") or 0),
            "broken_url": b.get("url_to") or "",
            "anchor_text": b.get("anchor") or "",
            "added_to_sequence": False,
            "email_sent": False,
            "discovered_at": today,
        })

    print(f"\n  kept (articles): {len(kept)}")
    for k, v in drops.items():
        print(f"  drop {k}: {v}")

    if dry_run:
        print("\n[dry-run] no rows written.")
        return 0

    sid = ensure_master_sheet()
    n = append_rows(sid, campaign, kept)
    update_summary(sid, campaign)
    print(f"\nappended {n} new rows (existing dedup: {len(kept) - n})")
    print(f"sheet: {sheet_url(sid, campaign)}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("campaign")
    p.add_argument("--file", required=True)
    p.add_argument("--technique", default="ahrefs:backlinks-defunct")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    return load(args.campaign, args.file, args.technique, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
