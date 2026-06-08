#!/usr/bin/env python3
"""
Export AirOps grid data to JSON by reading from the grid page by page.
This script is called by Claude with each page of data piped in via stdin.

Usage:
  echo '<json_rows>' | python3 export_airops_grid.py append
  python3 export_airops_grid.py finalize
"""

import json
import sys
import os

OUTPUT_FILE = "/Users/george.fakorellis/Desktop/SEO Custom Projects/link-outreach/campaigns/niche-edits/2026-04-08-video-translator/grid-export.json"

def append_rows(rows_json):
    """Append rows to the export file."""
    existing = []
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            existing = json.load(f)

    rows = json.loads(rows_json) if isinstance(rows_json, str) else rows_json
    existing.extend(rows)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(existing, f, indent=2)

    return len(existing)

def finalize():
    """Print summary of exported data."""
    with open(OUTPUT_FILE) as f:
        data = json.load(f)

    with_email = sum(1 for r in data if r.get("Email"))
    print(f"Total rows: {len(data)}")
    print(f"With email: {with_email}")
    print(f"Without email: {len(data) - with_email}")
    return data

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "append"

    if cmd == "append":
        rows_json = sys.stdin.read()
        total = append_rows(rows_json)
        print(f"Appended. Total rows: {total}")
    elif cmd == "finalize":
        finalize()
    elif cmd == "reset":
        if os.path.exists(OUTPUT_FILE):
            os.remove(OUTPUT_FILE)
        print("Reset.")
