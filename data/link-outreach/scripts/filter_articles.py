#!/usr/bin/env python3
"""Filter a campaign tab to keep only blog posts / articles.

Two-pass classifier:
1. If the row matches an Ahrefs response with `page_type_source` set, trust Ahrefs:
   - keep `/Article/*` and a few content types (Tutorial_or_Guide, Podcast)
   - drop `/Listing*`, `/Core_Page*`, `/User_Generated*`, `/Listing/Job`
2. If page_type is null (or no Ahrefs data), apply URL-pattern heuristics:
   - keep if path contains /blog/, /post/, /news/, /article/, /guide/, /tutorial/,
     /learn/, /insights/, /resources/, /journal/, /playbook/
   - keep if path has a /20YY/ year segment
   - keep if path ends with a long hyphenated slug (5+ hyphens)
   - else drop

Usage:
  python3 filter_articles.py <campaign> [--ahrefs-json <path>] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sheets_helper import (  # noqa: E402
    COLUMNS,
    CHECKBOX_COLUMNS,
    _col_letter,
    _get_tab_id,
    _sheets_service,
    ensure_master_sheet,
    read_campaign_rows,
    update_summary,
    sheet_url,
)

ARTICLE_PATH_MARKERS = (
    "/blog/", "/post/", "/posts/", "/news/", "/article/", "/articles/",
    "/guide/", "/guides/", "/tutorial/", "/tutorials/", "/how-to/",
    "/learn/", "/insights/", "/resources/", "/journal/", "/playbook/",
    "/stories/", "/case-studies/", "/case-study/", "/tips/", "/lessons/",
)
NEVER_PATH_MARKERS = (
    "/company/", "/companies/", "/org/", "/orgs/", "/profile/", "/profiles/",
    "/directory/", "/directories/", "/marketplace/",
    "/reviews/product/", "/reviews/products/", "/product/", "/products/",
    "/apps/", "/app/", "/tools/", "/tool/", "/sites/", "/site/",
    "/page/", "/search", "/tag/", "/tags/", "/topic/", "/topics/", "/category/", "/categories/",
    "/reference/", "/docs/", "/documentation", "/api/",
    "/about", "/contact", "/pricing", "/careers", "/jobs",
    "/privacy", "/security", "/legal", "/terms",
    "/thread/", "/comment/",
)
ARTICLE_PAGE_TYPE_PREFIXES = ("/Article/",)
ARTICLE_PAGE_TYPE_EXACT = ("/Video/Tutorial_or_Guide", "/Audio/Podcast")
NEVER_PAGE_TYPE_PREFIXES = ("/Listing", "/Core_Page", "/User_Generated", "/Search")


def is_article_url(url: str) -> bool:
    """URL-pattern heuristic for pages with no Ahrefs page_type classification.
    Drops first on hard non-article patterns; then checks for positive signals."""
    try:
        p = urlparse(url)
    except Exception:
        return False
    path = p.path.lower().rstrip("/")
    if not path or len(path) < 4:
        return False
    # Hard NO patterns
    if any(m in path for m in NEVER_PATH_MARKERS):
        return False
    # Strong positive signals
    if any(m in path for m in ARTICLE_PATH_MARKERS):
        return True
    if re.search(r"/20\d{2}(/|-)", path):
        return True
    # Long descriptive slug at end of a 1-or-2 segment path
    last_seg = path.split("/")[-1]
    if last_seg.count("-") >= 2 and len(last_seg) >= 12:
        return True
    return False


def classify(url: str, page_type: str | None) -> tuple[bool, str]:
    """Return (keep, reason)."""
    pt = (page_type or "").strip()
    if pt:
        if any(pt.startswith(pref) for pref in ARTICLE_PAGE_TYPE_PREFIXES) or pt in ARTICLE_PAGE_TYPE_EXACT:
            return True, f"page_type={pt}"
        if any(pt.startswith(pref) for pref in NEVER_PAGE_TYPE_PREFIXES):
            return False, f"page_type={pt}"
        return False, f"page_type={pt} (other)"
    if is_article_url(url):
        return True, "url_pattern"
    return False, "no_page_type, no_url_match"


def _normalize(url: str) -> str:
    return (url or "").strip().rstrip("/")


def filter_campaign(campaign: str, ahrefs_json: str | None, dry_run: bool) -> int:
    page_type_map: dict[str, str | None] = {}
    if ahrefs_json:
        with open(ahrefs_json) as f:
            data = json.load(f)
        for b in data.get("backlinks", []):
            u = _normalize(b.get("url_from", ""))
            if u:
                page_type_map[u] = b.get("page_type_source")

    sid = ensure_master_sheet()
    rows = read_campaign_rows(sid, campaign)
    print(f"loaded {len(rows)} rows from '{campaign}'")
    if ahrefs_json:
        print(f"  ahrefs page_type lookup map: {len(page_type_map)} URLs")

    keep_rows: list[list] = []
    drop_summary: dict[str, int] = {}
    decisions: list[tuple[str, bool, str]] = []
    for r in rows:
        u = _normalize(r.get("source_page", ""))
        pt = page_type_map.get(u)
        keep, reason = classify(u, pt)
        decisions.append((u, keep, reason))
        if keep:
            row_values = []
            for col in COLUMNS:
                v = r.get(col, "")
                if col in CHECKBOX_COLUMNS:
                    row_values.append(str(v).strip().upper() == "TRUE")
                else:
                    row_values.append("" if v is None else v)
            keep_rows.append(row_values)
        else:
            drop_summary[reason] = drop_summary.get(reason, 0) + 1

    print(f"\nclassification:")
    print(f"  keep: {len(keep_rows)}")
    print(f"  drop: {len(rows) - len(keep_rows)}")
    print(f"\ndrop reasons:")
    for reason, count in sorted(drop_summary.items(), key=lambda x: -x[1])[:15]:
        print(f"  {count:>4}  {reason}")

    if dry_run:
        print(f"\n[dry-run] no changes written. Sample dropped URLs:")
        for u, keep, reason in decisions:
            if not keep:
                print(f"  - [{reason}] {u}")
                if decisions.index((u, keep, reason)) > 10:
                    break
        return 0

    # Replace the data area in-place.
    sheets = _sheets_service()
    tab_id = _get_tab_id(sid, campaign)
    last_col = _col_letter(len(COLUMNS) - 1)
    # 1. Clear all data rows
    sheets.spreadsheets().values().clear(
        spreadsheetId=sid, range=f"{campaign}!A2:{last_col}",
    ).execute()
    # 2. Write kept rows back
    if keep_rows:
        sheets.spreadsheets().values().update(
            spreadsheetId=sid,
            range=f"{campaign}!A2",
            valueInputOption="USER_ENTERED",
            body={"values": keep_rows},
        ).execute()
        # 3. Re-apply checkbox validation to the new range
        from sheets_helper import _apply_checkbox_validation
        _apply_checkbox_validation(sid, tab_id, 1, len(keep_rows) + 1)

    update_summary(sid, campaign)
    print(f"\n{len(keep_rows)} rows kept; {len(rows) - len(keep_rows)} dropped.")
    print(f"sheet: {sheet_url(sid, campaign)}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Filter a campaign tab to articles only")
    p.add_argument("campaign")
    p.add_argument("--ahrefs-json", help="path to Ahrefs all-backlinks JSON containing page_type_source")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    return filter_campaign(args.campaign, args.ahrefs_json, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
