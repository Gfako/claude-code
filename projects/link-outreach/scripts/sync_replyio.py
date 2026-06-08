#!/usr/bin/env python3
"""Reply.io status sync for /link-discover.

For each campaign tab row, looks up each email across the configured
Reply.io sequences and updates these columns:
  - added_to_sequence  (checkbox)  : email exists in at least one sequence
  - email_sent         (checkbox)  : status.delivered=true OR stepNumber > 1
  - reply_status                   : best signal across sequences (replied >
                                     bounced > opened > delivered > added)
  - reply_sequence                 : sequence name(s) joined by '; '
  - last_activity_at               : most recent lastStepCompletedAt / addedAt

Usage:
  python3 sync_replyio.py <campaign>
"""
from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
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
API_BASE = "https://api.reply.io"
ADDITIONAL_COLUMNS = "CurrentStep,LastStepCompletedAt,Status"
PAGE_SIZE = 200
# Order matters — higher index wins when merging across multiple sequences.
STATUS_RANK = ["added", "delivered", "opened", "clicked", "bounced", "replied", "opted_out"]


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _read_api_key(cfg: dict) -> str:
    p = cfg.get("reply_io", {}).get("api_key_file")
    if not p:
        p = str(PROJECT_ROOT / ".credentials" / "reply-io-api-key.txt")
    return open(p).read().strip()


def _http_get_json(url: str, api_key: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                last_err = e
                continue
            raise
        except Exception as e:
            last_err = e
            time.sleep(2 ** attempt)
    raise last_err  # type: ignore[misc]


def fetch_sequence_contacts(sequence_id: int, api_key: str) -> list[dict]:
    """Paginate /v3/sequences/{id}/contacts/state. Returns full list of contact-state items."""
    out: list[dict] = []
    skip = 0
    while True:
        qs = urllib.parse.urlencode({
            "additionalColumns": ADDITIONAL_COLUMNS,
            "skip": skip,
            "take": PAGE_SIZE,
        })
        data = _http_get_json(f"{API_BASE}/v3/sequences/{sequence_id}/contacts/state?{qs}", api_key)
        items = data.get("items", [])
        out.extend(items)
        if not data.get("hasMore") or not items:
            break
        skip += len(items)
    return out


def _classify(item: dict) -> dict:
    """Reduce a sequence-contact-state record to the columns we care about."""
    step = item.get("currentStep") or {}
    step_num = step.get("stepNumber") or 0
    last_completed = item.get("lastStepCompletedAt")
    status_obj = item.get("status") or {}
    status_name = (status_obj.get("status") or "").lower()
    replied = bool(status_obj.get("replied"))
    bounced = bool(status_obj.get("bounced"))
    opened = bool(status_obj.get("opened"))
    clicked = bool(status_obj.get("clicked"))
    delivered = bool(status_obj.get("delivered"))

    sent = bool(delivered or last_completed or (isinstance(step_num, int) and step_num > 1))

    if replied:
        flag = "replied"
    elif bounced:
        flag = "bounced"
    elif status_name in ("optedout", "opted_out", "opted-out"):
        flag = "opted_out"
    elif clicked:
        flag = "clicked"
    elif opened:
        flag = "opened"
    elif delivered:
        flag = "delivered"
    else:
        flag = "added"

    return {
        "added": True,
        "sent": sent,
        "flag": flag,
        "last_activity_at": last_completed or item.get("addedAt") or "",
    }


def _best_flag(a: str, b: str) -> str:
    return a if STATUS_RANK.index(a) >= STATUS_RANK.index(b) else b


def build_email_index(api_key: str, sequences: dict[str, int]) -> dict[str, dict]:
    """Return email (lowercased) → {added, sent, flag, sequences:[names], last_activity_at}."""
    index: dict[str, dict] = {}
    for name, seq_id in sequences.items():
        print(f"  fetching sequence '{name}' (id={seq_id})...")
        items = fetch_sequence_contacts(seq_id, api_key)
        print(f"    {len(items)} contacts")
        for item in items:
            email = (item.get("email") or "").strip().lower()
            if not email:
                continue
            c = _classify(item)
            existing = index.get(email)
            if existing is None:
                index[email] = {
                    "added": True,
                    "sent": c["sent"],
                    "flag": c["flag"],
                    "sequences": [name],
                    "last_activity_at": c["last_activity_at"],
                }
            else:
                existing["added"] = existing["added"] or True
                existing["sent"] = existing["sent"] or c["sent"]
                existing["flag"] = _best_flag(existing["flag"], c["flag"])
                if name not in existing["sequences"]:
                    existing["sequences"].append(name)
                if c["last_activity_at"] > (existing.get("last_activity_at") or ""):
                    existing["last_activity_at"] = c["last_activity_at"]
    return index


def fetch_all_sequences(api_key: str) -> dict[str, int]:
    """Pull every active sequence from Reply.io v3, returning {name: id}.
    Falls back to the static config if the API call fails."""
    try:
        data = _http_get_json(f"{API_BASE}/v3/sequences", api_key)
        out = {}
        for s in data.get("items", []):
            if s.get("isArchived"):
                continue
            out[s["name"]] = s["id"]
        return out
    except Exception as e:
        print(f"  warn: dynamic sequence fetch failed ({e}); falling back to config", file=sys.stderr)
        return {}


def sync(campaign: str) -> int:
    cfg = load_config()
    api_key = _read_api_key(cfg)
    # Prefer dynamic fetch: every non-archived Reply.io sequence. Falls back to config.
    all_sequences = fetch_all_sequences(api_key) or cfg.get("reply_io", {}).get("sequences", {})
    if not all_sequences:
        print("no sequences found (API empty and no config fallback)", file=sys.stderr)
        return 1

    # Per-campaign sequence whitelist (prevents false positives from emails in unrelated sequences).
    # If no whitelist is configured for this campaign, fall back to all sequences (legacy behavior).
    campaign_whitelist_ids = cfg.get("reply_io", {}).get("campaign_sequences", {}).get(campaign, [])
    if campaign_whitelist_ids:
        sequences = {name: sid for name, sid in all_sequences.items() if sid in campaign_whitelist_ids}
        print(f"[1/3] '{campaign}' is restricted to {len(sequences)} sequence(s): {list(sequences.keys())}")
    else:
        sequences = all_sequences
        print(f"[1/3] '{campaign}' has no sequence whitelist; using all {len(sequences)} sequences")

    if not sequences:
        print(f"  no matching sequences for campaign '{campaign}' — nothing to sync", file=sys.stderr)
        return 0

    email_index = build_email_index(api_key, sequences)
    print(f"  total unique emails across sequences: {len(email_index)}")

    sid = ensure_master_sheet()
    rows = read_campaign_rows(sid, campaign)
    print(f"[2/3] checking {len(rows)} rows in '{campaign}' tab...")

    updated = 0
    added_count = 0
    sent_count = 0
    for r in rows:
        emails_csv = (r.get("emails") or "").strip()
        if not emails_csv:
            continue
        emails = [e.strip().lower() for e in emails_csv.split(",") if e.strip()]
        hits = [email_index.get(e) for e in emails]
        hits = [h for h in hits if h]
        if not hits:
            # Reply.io doesn't know this contact yet → don't touch the sheet.
            # Never clear manually-ticked values (per never-overwrite rule).
            continue

        added = any(h["added"] for h in hits)
        sent = any(h["sent"] for h in hits)
        flag = hits[0]["flag"]
        for h in hits[1:]:
            flag = _best_flag(flag, h["flag"])
        seq_names: list[str] = []
        last_activity = ""
        for h in hits:
            for s in h["sequences"]:
                if s not in seq_names:
                    seq_names.append(s)
            if (h.get("last_activity_at") or "") > last_activity:
                last_activity = h["last_activity_at"]

        # OR-merge with existing sheet values — only ever escalate, never downgrade.
        existing_added = str(r.get("added_to_sequence")).strip().upper() == "TRUE"
        existing_sent = str(r.get("email_sent")).strip().upper() == "TRUE"
        existing_seq = (r.get("reply_sequence") or "").strip()
        existing_last = (r.get("last_activity_at") or "").strip()

        merged_seq_names = list(seq_names)
        if existing_seq:
            for s in [x.strip() for x in existing_seq.replace(";", ",").split(",") if x.strip()]:
                if s not in merged_seq_names:
                    merged_seq_names.append(s)

        patch = {
            "added_to_sequence": added or existing_added,
            "email_sent": sent or existing_sent,
            "reply_status": flag,
            "reply_sequence": "; ".join(merged_seq_names),
            "last_activity_at": last_activity if last_activity > existing_last else existing_last,
        }
        update_row_by_source_page(sid, campaign, r["source_page"], patch)
        updated += 1
        if added:
            added_count += 1
        if sent:
            sent_count += 1

    update_summary(sid, campaign)
    print(f"[3/3] done. updated={updated} added={added_count} sent={sent_count}")
    print(f"  sheet: {sheet_url(sid, campaign)}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Sync Reply.io status into the campaign tab")
    p.add_argument("campaign")
    args = p.parse_args()
    return sync(args.campaign)


if __name__ == "__main__":
    sys.exit(main())
