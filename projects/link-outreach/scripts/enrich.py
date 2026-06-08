#!/usr/bin/env python3
"""Enrichment stage for /link-discover.

AirOps Hunter enrichment via MCP. Split into two Python steps that the slash
command threads together (the actual write_grid / read_grid happens in Claude):

  python3 enrich.py prepare-push <campaign>
    → prints JSON: rows to push to the AirOps grid (one per unique domain),
      with the source_page URLs they belong to.

  python3 enrich.py apply-contacts <campaign> --file <airops_export.json>
    → reads back AirOps grid output and writes emails / names / titles to the
      matching sheet rows (joined by domain).

Only rows where dr >= dr_min and emails column is empty are sent to AirOps.
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


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _dr_threshold(cfg: dict) -> int:
    return int(cfg.get("link_discover", {}).get("dr_min", cfg.get("qualification", {}).get("min_dr", 30)))


def _normalize_domain(d: str) -> str:
    d = (d or "").strip().lower()
    return d.removeprefix("www.")


def cmd_prepare_push(campaign: str) -> int:
    cfg = load_config()
    dr_min = _dr_threshold(cfg)

    sid = ensure_master_sheet()
    rows = read_campaign_rows(sid, campaign)

    # Group by domain — one AirOps row per domain (Hunter searches by domain).
    by_domain: dict[str, list[str]] = {}
    skipped_low_dr = 0
    skipped_has_emails = 0
    skipped_no_dr = 0
    skipped_already_enriched = 0
    skipped_excluded = 0
    for r in rows:
        # Respect the user's Excluded flag — don't waste Hunter credits on rows we won't pitch
        if str(r.get("excluded")).strip().upper() == "TRUE":
            skipped_excluded += 1
            continue
        # Skip rows already pushed through AirOps even if Hunter found nothing
        if str(r.get("enrichment_ran")).strip().upper() == "TRUE":
            skipped_already_enriched += 1
            continue
        if r.get("emails"):
            skipped_has_emails += 1
            continue
        dr_str = (r.get("dr") or "").strip()
        if not dr_str:
            skipped_no_dr += 1
            continue
        try:
            dr = int(float(dr_str))
        except ValueError:
            skipped_no_dr += 1
            continue
        if dr < dr_min:
            skipped_low_dr += 1
            continue
        domain = _normalize_domain(r.get("domain", ""))
        if not domain:
            continue
        by_domain.setdefault(domain, []).append(r["source_page"])

    push_rows = [
        {
            "domain": domain,
            "source_pages": pages,
        }
        for domain, pages in sorted(by_domain.items())
    ]

    payload = {
        "campaign": campaign,
        "airops_grid_id": cfg.get("airops", {}).get("enrichment_grid_id"),
        "airops_table_id": cfg.get("airops", {}).get("enrichment_table_id"),
        "dr_min": dr_min,
        "skipped": {
            "excluded": skipped_excluded,
            "already_enriched": skipped_already_enriched,
            "already_has_emails": skipped_has_emails,
            "no_dr_yet": skipped_no_dr,
            "below_dr_min": skipped_low_dr,
        },
        "to_push": push_rows,
        "to_push_count": len(push_rows),
    }
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def _extract_contact_fields(row: dict) -> dict:
    """Map heterogeneous AirOps column names to our canonical contact fields.
    Combines up to 3 contacts (Email + Email 2nd + Email 3rd) into comma-separated emails."""
    def first_truthy(*keys: str) -> str:
        for k in keys:
            v = row.get(k)
            if v:
                return str(v).strip()
        return ""

    # Collect up to 3 emails
    email_keys = [("Email", "email", "Hunter Emails", "hunter_emails"), ("Email 2nd", "email_2nd"), ("Email 3rd", "email_3rd")]
    collected = []
    for variants in email_keys:
        v = first_truthy(*variants)
        if v:
            for e in v.replace(";", ",").replace("\n", ",").split(","):
                e = e.strip()
                if e and e not in collected:
                    collected.append(e)
    # Also support combined "Emails" field if present
    if not collected:
        combined = first_truthy("Emails", "emails")
        if combined:
            for e in combined.replace(";", ",").replace("\n", ",").split(","):
                e = e.strip()
                if e and e not in collected:
                    collected.append(e)
    emails = ",".join(collected)

    first_name = first_truthy("First Name", "first_name", "Primary Name", "primary_name", "Contact Name", "contact_name", "name")
    last_name = first_truthy("Last Name", "last_name", "surname")
    # If first_name contains the full name (e.g., "John Doe") and last_name is empty, split it.
    if first_name and not last_name and " " in first_name.strip():
        parts = first_name.strip().split()
        first_name = parts[0]
        last_name = " ".join(parts[1:])
    primary_title = first_truthy("Position", "position", "Title", "title", "Job Title", "job_title", "Primary Title", "primary_title")
    domain = first_truthy("domain", "Domain", "Website Domain")
    return {
        "domain": _normalize_domain(domain),
        "emails": emails,
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "primary_contact_title": primary_title.strip(),
    }


def cmd_apply_contacts(campaign: str, file_path: str) -> int:
    with open(file_path) as f:
        raw = json.load(f)
    if isinstance(raw, dict):
        for key in ("rows", "results", "data", "items"):
            if isinstance(raw.get(key), list):
                items = raw[key]
                break
        else:
            items = []
    elif isinstance(raw, list):
        items = raw
    else:
        items = []

    enriched_domains: set[str] = set()  # every domain that went through AirOps (whether emails found or not)
    by_domain: dict[str, dict] = {}
    for it in items:
        if not isinstance(it, dict):
            continue
        contact = _extract_contact_fields(it)
        if contact["domain"]:
            enriched_domains.add(contact["domain"])
            if contact["emails"] or contact["first_name"]:
                by_domain[contact["domain"]] = contact

    sid = ensure_master_sheet()
    rows = read_campaign_rows(sid, campaign)
    updated = 0
    enrichment_ticked = 0
    skipped_manual = 0
    skipped_domain_mismatch = 0
    for r in rows:
        d = _normalize_domain(r.get("domain", ""))

        # 1. Tick enrichment_ran=TRUE for any row whose domain went through AirOps,
        #    even if Hunter found nothing — this prevents re-pushing the same domain.
        if d in enriched_domains and str(r.get("enrichment_ran")).strip().upper() != "TRUE":
            update_row_by_source_page(sid, campaign, r["source_page"], {"enrichment_ran": True})
            enrichment_ticked += 1

        # 2. Apply contact data only to rows that don't have manual entries (never overwrite)
        if r.get("emails") or r.get("first_name") or r.get("last_name") or r.get("primary_contact_title"):
            if not r.get("emails"):
                skipped_manual += 1
            continue
        hit = by_domain.get(d)
        if not hit:
            continue
        # Safety: the row's source_page URL should actually be on this domain.
        from urllib.parse import urlparse
        page_host = (urlparse(r.get("source_page", "")).netloc or "").lower().removeprefix("www.")
        if page_host and d:
            page_root = ".".join(page_host.split(".")[-2:]) if "." in page_host else page_host
            d_root = ".".join(d.split(".")[-2:]) if "." in d else d
            if page_root != d_root:
                skipped_domain_mismatch += 1
                continue
        patch = {
            "emails": hit["emails"],
            "first_name": hit["first_name"],
            "last_name": hit["last_name"],
            "primary_contact_title": hit["primary_contact_title"],
            "enrichment_ran": True,
        }
        update_row_by_source_page(sid, campaign, r["source_page"], patch)
        updated += 1

    update_summary(sid, campaign)
    print(json.dumps({
        "campaign": campaign,
        "updated_rows": updated,
        "domains_with_contacts": len(by_domain),
        "skipped_manual": skipped_manual,
        "skipped_domain_mismatch": skipped_domain_mismatch,
        "sheet": sheet_url(sid, campaign),
    }, indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="link-discover enrichment stage")
    sub = p.add_subparsers(dest="cmd", required=True)
    p_prep = sub.add_parser("prepare-push")
    p_prep.add_argument("campaign")
    p_apply = sub.add_parser("apply-contacts")
    p_apply.add_argument("campaign")
    p_apply.add_argument("--file", required=True)
    args = p.parse_args()
    if args.cmd == "prepare-push":
        return cmd_prepare_push(args.campaign)
    if args.cmd == "apply-contacts":
        return cmd_apply_contacts(args.campaign, args.file)
    return 1


if __name__ == "__main__":
    sys.exit(main())
