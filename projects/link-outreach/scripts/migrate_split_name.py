#!/usr/bin/env python3
"""One-time migration: split 'primary_contact_name' column into 'first_name' + 'last_name'.

For each campaign tab:
- Reads current primary_contact_name values from col O (index 14).
- Inserts a new sheet column at index 15.
- Writes split values: first word -> col 14, rest -> col 15.
- Rewrites the headers at col 14 to "First Name" and col 15 to "Last Name".

Run this AFTER the sheets_helper.py COLUMNS schema has been updated.
The script operates on raw column indices so it does not depend on the new schema.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sheets_helper import _sheets_service, ensure_master_sheet, _col_letter  # type: ignore

PRIMARY_NAME_COL_IDX = 14  # current position of primary_contact_name in old schema


def _split(full: str) -> tuple[str, str]:
    full = (full or "").strip()
    if not full:
        return "", ""
    parts = full.split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def migrate_tab(svc, sid: str, tab_name: str) -> int:
    # Resolve tab id
    meta = svc.spreadsheets().get(spreadsheetId=sid, fields="sheets(properties(sheetId,title))").execute()
    tab_id = None
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == tab_name:
            tab_id = s["properties"]["sheetId"]
            break
    if tab_id is None:
        print(f"  tab not found: {tab_name}")
        return 0

    # Read all values in current primary_contact_name column (col O, idx 14)
    col_letter = _col_letter(PRIMARY_NAME_COL_IDX)
    rng = f"{tab_name}!{col_letter}2:{col_letter}"
    resp = svc.spreadsheets().values().get(spreadsheetId=sid, range=rng).execute()
    existing_values = resp.get("values", [])

    # Compute splits
    first_names = [_split((row[0] if row else ""))[0] for row in existing_values]
    last_names = [_split((row[0] if row else ""))[1] for row in existing_values]

    # Insert new physical sheet column at index 15
    svc.spreadsheets().batchUpdate(spreadsheetId=sid, body={
        "requests": [{
            "insertDimension": {
                "range": {"sheetId": tab_id, "dimension": "COLUMNS",
                          "startIndex": PRIMARY_NAME_COL_IDX + 1, "endIndex": PRIMARY_NAME_COL_IDX + 2},
                "inheritFromBefore": False,
            }
        }]
    }).execute()

    # Write headers at cols 14 and 15
    first_letter = _col_letter(PRIMARY_NAME_COL_IDX)
    last_letter = _col_letter(PRIMARY_NAME_COL_IDX + 1)
    svc.spreadsheets().values().update(
        spreadsheetId=sid,
        range=f"{tab_name}!{first_letter}1:{last_letter}1",
        valueInputOption="RAW",
        body={"values": [["First Name", "Last Name"]]},
    ).execute()

    # Write split values back
    if existing_values:
        rows_to_write = [[fn, ln] for fn, ln in zip(first_names, last_names)]
        svc.spreadsheets().values().update(
            spreadsheetId=sid,
            range=f"{tab_name}!{first_letter}2:{last_letter}{1 + len(rows_to_write)}",
            valueInputOption="RAW",
            body={"values": rows_to_write},
        ).execute()

    print(f"  {tab_name}: split {len(existing_values)} name rows")
    return len(existing_values)


def main() -> int:
    svc = _sheets_service()
    sid = ensure_master_sheet()
    # Find all campaign tabs (exclude Dashboard, _Data, _Monthly, _Summary)
    meta = svc.spreadsheets().get(spreadsheetId=sid, fields="sheets(properties(title))").execute()
    excluded = {"Dashboard", "_Data", "_Monthly", "_Summary"}
    campaigns = [s["properties"]["title"] for s in meta.get("sheets", []) if s["properties"]["title"] not in excluded]
    print(f"migrating {len(campaigns)} campaign tabs:")
    for t in campaigns:
        migrate_tab(svc, sid, t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
