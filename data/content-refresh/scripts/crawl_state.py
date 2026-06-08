#!/usr/bin/env python3
"""
Manage crawl state: which URLs have been checked, when, and with what content hash.

State schema (state/crawl_state.json):
{
  "version": 1,
  "last_run": "2026-04-24T07:07:00Z",
  "urls": {
    "<url>": {
      "section": "blog" | "alternatives",
      "last_checked": "2026-04-24",
      "last_change_detected": "2026-04-20",
      "content_hash": "<sha256>",
      "notion_page_id": "<uuid>" | null,
      "findings_count": 3,
      "score": 42,
      "severity": "High"
    }
  }
}

Usage:
  python3 crawl_state.py pick-urls [--count 15]     # print N URLs to process today
  python3 crawl_state.py record-result < result.json  # update state for one URL
  python3 crawl_state.py mark-run-start
  python3 crawl_state.py mark-run-end
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config.json"
STATE_PATH = ROOT / "state" / "crawl_state.json"


def load_state() -> dict:
    with open(STATE_PATH) as f:
        return json.load(f)


def save_state(state: dict):
    tmp = STATE_PATH.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    tmp.replace(STATE_PATH)


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def pick_urls(sitemap_entries: list[dict], state: dict, count: int) -> list[dict]:
    """
    Priority:
      1. Never-checked URLs, newest sitemap lastmod first.
      2. Previously-checked URLs whose lastmod is newer than last_checked.
      3. Oldest last_checked.
    Ties broken by lastmod desc, then URL asc.
    """
    urls_state = state.get("urls", {})

    def priority(e: dict):
        url = e["url"]
        st = urls_state.get(url)
        if st is None:
            return (0, -_lastmod_sort_key(e.get("lastmod")), url)
        last_checked = st.get("last_checked") or ""
        lastmod = e.get("lastmod") or ""
        if lastmod and last_checked and lastmod > last_checked:
            return (1, -_lastmod_sort_key(lastmod), url)
        return (2, last_checked, url)

    ordered = sorted(sitemap_entries, key=priority)
    return ordered[:count]


def _lastmod_sort_key(lastmod: str | None) -> float:
    if not lastmod:
        return 0.0
    try:
        return datetime.fromisoformat(lastmod.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def record_result(state: dict, result: dict) -> dict:
    """
    result: {
      "url": "...",
      "section": "blog",
      "content_hash": "...",
      "findings_count": int,
      "score": int,
      "severity": "...",
      "notion_page_id": "..." | null,
      "changed": bool   # did content hash change since last check
    }
    """
    url = result["url"]
    urls = state.setdefault("urls", {})
    prev = urls.get(url, {})
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    last_change = prev.get("last_change_detected")
    if result.get("changed") or prev.get("content_hash") != result.get("content_hash"):
        last_change = today

    urls[url] = {
        "section": result.get("section") or prev.get("section"),
        "last_checked": today,
        "last_change_detected": last_change,
        "content_hash": result.get("content_hash"),
        "notion_page_id": result.get("notion_page_id") or prev.get("notion_page_id"),
        "findings_count": result.get("findings_count", 0),
        "score": result.get("score", 0),
        "severity": result.get("severity", "Clean"),
    }
    return state


def cmd_pick_urls(args):
    cfg = load_config()
    state = load_state()
    count = args.count or cfg.get("urls_per_day", 15)
    # Sitemap entries are passed on stdin as JSON list (from sitemap_fetch output's "urls" field).
    payload = json.loads(sys.stdin.read())
    entries = payload if isinstance(payload, list) else payload.get("urls", [])
    picks = pick_urls(entries, state, count)
    print(json.dumps(picks, indent=2))


def cmd_record_result(args):
    state = load_state()
    result = json.loads(sys.stdin.read())
    state = record_result(state, result)
    save_state(state)
    print(json.dumps({"ok": True, "url": result.get("url")}))


def cmd_mark_run_start(args):
    state = load_state()
    state["last_run_start"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    print(json.dumps({"ok": True}))


def cmd_mark_run_end(args):
    state = load_state()
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    print(json.dumps({"ok": True}))


def cmd_hash(args):
    text = sys.stdin.read()
    print(content_hash(text))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("pick-urls")
    p.add_argument("--count", type=int, default=None)
    p.set_defaults(func=cmd_pick_urls)

    p = sub.add_parser("record-result")
    p.set_defaults(func=cmd_record_result)

    sub.add_parser("mark-run-start").set_defaults(func=cmd_mark_run_start)
    sub.add_parser("mark-run-end").set_defaults(func=cmd_mark_run_end)
    sub.add_parser("hash").set_defaults(func=cmd_hash)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
