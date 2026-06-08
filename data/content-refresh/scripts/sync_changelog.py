#!/usr/bin/env python3
"""
Append-and-merge sync for the Synthesia product KB.

This script is the deterministic half — it manages timestamps, dedupe, and
the merge-by-id (newer wins via `supersedes`). The actual extraction of
product facts from Slack posts is LLM-driven and lives in the daily skill.

Usage in the skill flow:
  1. Skill calls slack_read_channel for posts since `state.kb_last_synced_ts`.
  2. Skill saves new raw posts to /tmp/changelog_new.md.
  3. Skill (LLM) extracts new entries → /tmp/new_entries.json (same schema as
     the existing KB entries).
  4. This script: merges /tmp/new_entries.json into state/synthesia_kb.json,
     bumps last_synced_ts, writes a human-readable diff to logs/.

Subcommands:
  - merge-entries < /tmp/new_entries.json
  - get-last-synced-ts
  - mark-synced <ts>
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
KB_PATH = ROOT / "state" / "synthesia_kb.json"
STATE_PATH = ROOT / "state" / "crawl_state.json"
LOGS = ROOT / "logs"


def load_kb() -> dict:
    if not KB_PATH.exists():
        return {
            "version": 1,
            "entries": [],
            "covered_range": {"oldest": None, "newest": None},
        }
    return json.loads(KB_PATH.read_text())


def save_kb(kb: dict):
    tmp = KB_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(kb, indent=2, ensure_ascii=False))
    tmp.replace(KB_PATH)


def merge_entries(new_entries: list[dict]) -> dict:
    """
    Merge a list of new entries into the KB. Rules:
      - Match by `id`. If id exists in KB:
          - If new entry's source date >= existing source date: REPLACE the
            existing entry, push the old entry's id into the new entry's
            `supersedes` list.
          - Otherwise: skip (we already have a newer fact).
      - If id doesn't exist: append.
    Returns the updated KB.
    """
    kb = load_kb()
    by_id = {e["id"]: e for e in kb.get("entries", [])}
    diff = {"added": [], "updated": [], "skipped_older": []}

    for new in new_entries:
        nid = new.get("id")
        if not nid:
            continue
        new_date = (new.get("source") or {}).get("date") or ""
        if nid in by_id:
            existing = by_id[nid]
            existing_date = (existing.get("source") or {}).get("date") or ""
            if new_date >= existing_date:
                supersedes = list(new.get("supersedes") or [])
                if existing_date and existing_date != new_date:
                    supersedes.append({"id": nid, "date": existing_date, "name": existing.get("name")})
                new["supersedes"] = supersedes
                by_id[nid] = new
                diff["updated"].append({"id": nid, "from": existing_date, "to": new_date})
            else:
                diff["skipped_older"].append({"id": nid, "incoming_date": new_date, "kb_date": existing_date})
        else:
            by_id[nid] = new
            diff["added"].append({"id": nid, "name": new.get("name"), "date": new_date})

    kb["entries"] = list(by_id.values())
    # Update covered_range.newest if any new dates are later
    all_dates = [(e.get("source") or {}).get("date") for e in kb["entries"] if (e.get("source") or {}).get("date")]
    if all_dates:
        kb["covered_range"] = {"oldest": min(all_dates), "newest": max(all_dates)}
    kb["last_merged_at"] = datetime.now(timezone.utc).isoformat()
    save_kb(kb)
    return diff


def cmd_merge_entries(args):
    payload = json.loads(sys.stdin.read())
    if isinstance(payload, dict) and "entries" in payload:
        new_entries = payload["entries"]
    else:
        new_entries = payload
    diff = merge_entries(new_entries)
    LOGS.mkdir(exist_ok=True)
    log_path = LOGS / f"kb-merge-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
    log_path.write_text(json.dumps(diff, indent=2, ensure_ascii=False))
    print(json.dumps({
        "added": len(diff["added"]),
        "updated": len(diff["updated"]),
        "skipped_older": len(diff["skipped_older"]),
        "log": str(log_path),
    }))


def cmd_get_last_synced_ts(args):
    state = json.loads(STATE_PATH.read_text())
    ts = state.get("kb_last_synced_ts")
    print(ts or "")


def cmd_mark_synced(args):
    state = json.loads(STATE_PATH.read_text())
    state["kb_last_synced_ts"] = args.ts
    state["kb_last_synced_at"] = datetime.now(timezone.utc).isoformat()
    STATE_PATH.write_text(json.dumps(state, indent=2))
    print(json.dumps({"ok": True}))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("merge-entries").set_defaults(func=cmd_merge_entries)
    sub.add_parser("get-last-synced-ts").set_defaults(func=cmd_get_last_synced_ts)
    p = sub.add_parser("mark-synced")
    p.add_argument("ts", type=str)
    p.set_defaults(func=cmd_mark_synced)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
