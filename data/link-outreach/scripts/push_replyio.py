#!/usr/bin/env python3
"""Push enriched contacts from a campaign tab into a Reply.io sequence.

For each sheet row where `emails` is set AND `added_to_sequence` is FALSE,
push a contact via Reply.io v1 `actions/addandpushtocampaign`. On success,
tick the `added_to_sequence` checkbox in the sheet so it shows up on the
Dashboard breakdown.

Custom field mapping:
- article_url            ← source_page
- article_topic          ← source_page_title (truncated)
- synthesia_target_page  ← --synthesia-url (default https://www.synthesia.io)
- fit_strength           ← --fit-strength (default 'strong')
- outreach_track         ← --outreach-track (default '<campaign>')

Usage:
  python3 push_replyio.py <campaign> <sequence_id> \
      [--synthesia-url <url>] [--outreach-track <name>] [--fit-strength <s>] \
      [--require-named] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sheets_helper import (  # noqa: E402
    ensure_master_sheet,
    read_campaign_rows,
    update_row_by_source_page,
    update_summary,
    sheet_url,
)

ssl._create_default_https_context = ssl._create_unverified_context

PROJECT_ROOT = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects")
CONFIG_PATH = PROJECT_ROOT / "link-outreach" / "config.json"
REPLY_IO_BASE = "https://api.reply.io"


def _api_key() -> str:
    return open(PROJECT_ROOT / ".credentials" / "reply-io-api-key.txt").read().strip()


def _split_name(full: str) -> tuple[str, str]:
    full = (full or "").strip()
    if not full:
        return "", ""
    parts = full.split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def _company_from_domain(domain: str) -> str:
    d = (domain or "").lower()
    if d.startswith("www."):
        d = d[4:]
    root = d.split(".")[0] if "." in d else d
    return root.capitalize()


def _truncate(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[:n - 1] + "…"


def _push(campaign_id: int, payload: dict, api_key: str) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{REPLY_IO_BASE}/v1/actions/addandpushtocampaign",
        data=data,
        headers={"Content-Type": "application/json", "x-api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return {"status": "success", "code": r.status}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        return {"status": "error", "code": e.code, "message": body[:200]}
    except Exception as e:
        return {"status": "error", "code": 0, "message": str(e)}


def run(campaign: str, sequence_id: int, synthesia_url: str, outreach_track: str, fit_strength: str, require_named: bool, dry_run: bool) -> int:
    api_key = _api_key()
    sid = ensure_master_sheet()
    rows = read_campaign_rows(sid, campaign)

    candidates = []
    skip = {"no_email": 0, "already_added": 0, "no_first_name": 0, "duplicate_email_in_sheet": 0, "excluded": 0, "blocked_by_replyio": 0}
    seen_emails: set[str] = set()
    for r in rows:
        # Respect the user's Excluded flag — never outreach to rows ticked excluded
        if str(r.get("excluded")).strip().upper() == "TRUE":
            skip["excluded"] += 1
            continue
        # Reply.io previously rejected this contact — don't retry
        if str(r.get("blocked_by_replyio")).strip().upper() == "TRUE":
            skip["blocked_by_replyio"] += 1
            continue
        email = (r.get("emails") or "").split(",")[0].strip().lower()
        if not email:
            skip["no_email"] += 1
            continue
        if str(r.get("added_to_sequence")).strip().upper() == "TRUE":
            skip["already_added"] += 1
            continue
        first = (r.get("first_name") or "").strip()
        last = (r.get("last_name") or "").strip()
        # Fallback: if first_name happens to contain a full name, split it.
        if first and not last and " " in first:
            first, last = _split_name(first)
        if require_named and not first:
            skip["no_first_name"] += 1
            continue
        # Dedup within this run — never push the same email twice
        if email in seen_emails:
            skip["duplicate_email_in_sheet"] += 1
            continue
        seen_emails.add(email)
        candidates.append({
            "row": r,
            "email": email,
            "first": first,
            "last": last,
        })

    print(f"campaign:        {campaign}")
    print(f"sequence_id:     {sequence_id}")
    print(f"synthesia_url:   {synthesia_url}")
    print(f"outreach_track:  {outreach_track}")
    print(f"candidates:      {len(candidates)}")
    for k, v in skip.items():
        print(f"  skip {k}: {v}")

    if dry_run:
        print("\n[dry-run] sample first 5:")
        for c in candidates[:5]:
            r = c["row"]
            print(f"  {c['email']:40} {c['first']:15} {c['last']:15} {r['domain']:25} DR={r['dr']}")
        return 0

    pushed = 0
    errors: list[dict] = []
    for i, c in enumerate(candidates, 1):
        r = c["row"]
        custom_fields = [
            {"key": "article_url", "value": r.get("source_page", "")},
            {"key": "article_topic", "value": _truncate(r.get("source_page_title", ""), 200)},
            {"key": "synthesia_target_page", "value": synthesia_url},
            {"key": "fit_strength", "value": fit_strength},
            {"key": "outreach_track", "value": outreach_track},
            {"key": "custom_domain", "value": r.get("domain", "")},
        ]
        payload = {
            "campaignId": sequence_id,
            "email": c["email"],
            "firstName": c["first"] or "",
            "lastName": c["last"] or "",
            "company": _company_from_domain(r.get("domain", "")),
            "title": r.get("primary_contact_title", "") or "",
            "customFields": [cf for cf in custom_fields if cf["value"]],
        }
        result = _push(sequence_id, payload, api_key)
        if result["status"] == "success":
            pushed += 1
            update_row_by_source_page(sid, campaign, r["source_page"], {
                "added_to_sequence": True,
                "reply_status": "in_sequence",
                "reply_sequence": campaign,  # human-readable; sync_replyio.py will refine
            })
            print(f"  [{i}/{len(candidates)}] OK  {c['email']:40}  DR{r['dr']}")
        else:
            errors.append({"email": c["email"], "domain": r.get("domain", ""), "result": result})
            # Tick Blocked by Reply.io so we don't retry this row on future runs
            update_row_by_source_page(sid, campaign, r["source_page"], {
                "blocked_by_replyio": True,
            })
            print(f"  [{i}/{len(candidates)}] ERR {c['email']:40}  {result.get('message','')[:80]}")
        time.sleep(0.3)

    update_summary(sid, campaign)
    print(f"\npushed: {pushed}/{len(candidates)} | errors: {len(errors)}")
    print(f"sheet: {sheet_url(sid, campaign)}")
    if errors:
        print("\nfirst 5 errors:")
        for e in errors[:5]:
            print(f"  {e['email']:40}  {e['result'].get('message','')[:120]}")
    return 0 if not errors else 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("campaign")
    p.add_argument("sequence_id", type=int)
    p.add_argument("--synthesia-url", default="https://www.synthesia.io")
    p.add_argument("--outreach-track", default="")
    p.add_argument("--fit-strength", default="strong")
    p.add_argument("--require-named", action="store_true", help="skip contacts without a first name")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    outreach_track = args.outreach_track or args.campaign
    return run(args.campaign, args.sequence_id, args.synthesia_url, outreach_track, args.fit_strength, args.require_named, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
