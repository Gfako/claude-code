#!/usr/bin/env python3
"""Filter stage for /link-discover.

DR/traffic hydration. Designed to work with the Ahrefs MCP (no direct REST key):
- `list-domains <campaign>` prints unique domains that still lack a DR value.
  The slash-command harness then calls mcp__ahrefs__batch-analysis in batches
  of 100 and pipes the response back via `apply-results`.
- `apply-results <campaign> --json <results.json>` reads the Ahrefs batch
  response and writes dr/traffic onto every matching row.

Usage:
  python3 filter.py list-domains <campaign>
  python3 filter.py apply-results <campaign> --file ahrefs_results.json
  python3 filter.py mark-qualified <campaign>   # optional: tag rows by dr threshold
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sheets_helper import (  # noqa: E402
    ensure_master_sheet,
    read_campaign_rows,
    update_row_by_source_page,
    update_summary,
    sheet_url,
)

PROJECT_ROOT = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects")
CONFIG_PATH = PROJECT_ROOT / "link-outreach" / "config.json"
MASTER_TRACKER = PROJECT_ROOT / "link-outreach" / "master-tracker.csv"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _domain_of_row(row: dict) -> str:
    d = (row.get("domain") or "").strip().lower()
    return d


def _historical_domains() -> set[str]:
    """Domains already contacted (from master-tracker.csv) — kept for visibility, not used to delete rows."""
    if not MASTER_TRACKER.exists():
        return set()
    import csv
    out: set[str] = set()
    with open(MASTER_TRACKER, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            dom = (r.get("domain") or "").strip().lower()
            if dom:
                out.add(dom)
    return out


def cmd_list_domains(campaign: str) -> int:
    sid = ensure_master_sheet()
    rows = read_campaign_rows(sid, campaign)
    domains: dict[str, int] = {}
    for r in rows:
        dr = (r.get("dr") or "").strip()
        if dr:
            continue
        d = _domain_of_row(r)
        if d:
            domains[d] = domains.get(d, 0) + 1
    payload = {
        "campaign": campaign,
        "domains_needing_dr": sorted(domains.keys()),
        "total": len(domains),
        "row_counts": domains,
    }
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def _normalize_results(raw: object) -> dict[str, dict]:
    """Accept Ahrefs MCP batch-analysis output in several shapes; return {domain: {dr, traffic}}."""
    items: list[dict] = []
    if isinstance(raw, dict):
        for key in ("results", "data", "domains", "items"):
            if isinstance(raw.get(key), list):
                items = raw[key]
                break
        else:
            if raw and all(isinstance(v, dict) for v in raw.values()):
                return {
                    _strip_domain(k): {
                        "dr": _coerce_int(v.get("dr") or v.get("domain_rating")),
                        "traffic": _coerce_int(v.get("traffic") or v.get("organic_traffic")),
                    }
                    for k, v in raw.items()
                }
    elif isinstance(raw, list):
        items = raw

    out: dict[str, dict] = {}
    for it in items:
        if not isinstance(it, dict):
            continue
        domain = it.get("target") or it.get("domain") or it.get("url") or ""
        domain = _strip_domain(str(domain))
        if not domain:
            continue
        dr = _coerce_int(it.get("dr") or it.get("domain_rating") or (it.get("metrics") or {}).get("domain_rating"))
        traffic = _coerce_int(it.get("traffic") or it.get("organic_traffic") or (it.get("metrics") or {}).get("traffic"))
        out[domain] = {"dr": dr, "traffic": traffic}
    return out


def _strip_domain(s: str) -> str:
    s = s.strip().lower()
    s = s.replace("https://", "").replace("http://", "")
    s = s.split("/", 1)[0]
    s = s.removeprefix("www.")
    return s


def _coerce_int(v: object) -> int | str:
    if v is None or v == "":
        return ""
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return ""


def cmd_apply_results(campaign: str, file_path: str) -> int:
    with open(file_path) as f:
        raw = json.load(f)
    mapping = _normalize_results(raw)
    if not mapping:
        print(f"no usable results parsed from {file_path}", file=sys.stderr)
        return 1

    sid = ensure_master_sheet()
    rows = read_campaign_rows(sid, campaign)

    updated = 0
    unmatched: list[str] = []
    for r in rows:
        if (r.get("dr") or "").strip():
            continue
        d = _strip_domain(_domain_of_row(r))
        # try with and without www
        hit = mapping.get(d) or mapping.get("www." + d)
        if not hit:
            unmatched.append(d)
            continue
        patch = {}
        if hit.get("dr") != "":
            patch["dr"] = hit["dr"]
        if hit.get("traffic") != "":
            patch["traffic"] = hit["traffic"]
        if patch:
            update_row_by_source_page(sid, campaign, r["source_page"], patch)
            updated += 1

    update_summary(sid, campaign)
    print(json.dumps({
        "campaign": campaign,
        "updated_rows": updated,
        "unmatched_domains": sorted(set(unmatched))[:20],
        "sheet": sheet_url(sid, campaign),
    }, indent=2))
    return 0


def cmd_mark_qualified(campaign: str) -> int:
    """Print stats only — qualified = dr >= dr_min. Doesn't change schema."""
    cfg = load_config()
    dr_min = int(cfg.get("link_discover", {}).get("dr_min", cfg.get("qualification", {}).get("min_dr", 30)))
    dr_max = int(cfg.get("link_discover", {}).get("dr_max", 95))

    sid = ensure_master_sheet()
    rows = read_campaign_rows(sid, campaign)
    historical = _historical_domains()

    qualified = 0
    below = 0
    above = 0
    no_dr = 0
    historical_dup = 0
    for r in rows:
        dr_str = (r.get("dr") or "").strip()
        if not dr_str:
            no_dr += 1
            continue
        try:
            dr = int(float(dr_str))
        except ValueError:
            no_dr += 1
            continue
        if dr < dr_min:
            below += 1
        elif dr > dr_max:
            above += 1
        else:
            qualified += 1
        if _domain_of_row(r) in historical:
            historical_dup += 1
    print(json.dumps({
        "campaign": campaign,
        "total_rows": len(rows),
        "qualified": qualified,
        "below_dr_min": below,
        "above_dr_max": above,
        "missing_dr": no_dr,
        "historical_duplicates": historical_dup,
        "dr_window": [dr_min, dr_max],
    }, indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="link-discover filter stage")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list-domains")
    p_list.add_argument("campaign")

    p_apply = sub.add_parser("apply-results")
    p_apply.add_argument("campaign")
    p_apply.add_argument("--file", required=True, help="JSON file with Ahrefs batch-analysis output")

    p_qual = sub.add_parser("mark-qualified")
    p_qual.add_argument("campaign")

    args = p.parse_args()
    if args.cmd == "list-domains":
        return cmd_list_domains(args.campaign)
    if args.cmd == "apply-results":
        return cmd_apply_results(args.campaign, args.file)
    if args.cmd == "mark-qualified":
        return cmd_mark_qualified(args.campaign)
    return 1


if __name__ == "__main__":
    sys.exit(main())
