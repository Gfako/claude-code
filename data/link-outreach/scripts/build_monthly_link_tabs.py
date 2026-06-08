#!/usr/bin/env python3
"""Build/refresh per-month 'Links YYYY-MM' tabs from all campaign tabs.

For each campaign row with both `link_placed_at` AND `link_placed_url` filled,
upserts a row into the monthly tab matching the link_placed_at month.

Auto-managed fields (overwritten on every run):
  - Date Built, Page where link sits, Target URL, Anchor, DR, Campaign / Source

Manual fields (NEVER overwritten — user can edit freely):
  - Cost, Partner

Manual rows (a row whose source_page URL doesn't appear in any campaign tab)
are also left alone — useful for personal-network entries.

Upsert key: source_page URL.

Usage: python3 build_monthly_link_tabs.py
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sheets_helper import (  # noqa: E402
    ensure_master_sheet, _sheets_service, read_campaign_rows, _get_tab_id, _col_letter,
    FONT, HEADER_BG, HEADER_FG, BAND_PRIMARY, BAND_ALT,
)

import calendar

DATA_TAB = "_Data"
EXCLUDED_TABS = {"Dashboard", "_Data", "_Monthly", "_Summary", "Sheet1", "Sheet3"}

# Map YYYY-MM → human-readable tab name (default for new tabs).
# Existing tabs are discovered by header signature, never renamed.
MONTH_FULL = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
              7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"}

def default_tab_name(month_key: str) -> str:
    """'2026-05' → 'May 2026'."""
    y, m = month_key.split("-")
    return f"{MONTH_FULL[int(m)]} {y}"

# Monthly tab columns. Auto-managed fields first, manual fields at the end.
MONTHLY_HEADERS = [
    "Date Built",       # A
    "Page where link sits",  # B
    "Target URL",       # C
    "Anchor",           # D
    "DR",               # E
    "Campaign / Source",  # F  (auto on first insert; editable)
    "Cost",             # G  (manual)
    "Partner",          # H  (manual)
]
MANUAL_COLUMNS = {"Cost", "Partner"}
URL_KEY_COL = "Page where link sits"  # column B is the upsert key

WIDTHS = {
    "Date Built": 100,
    "Page where link sits": 360,
    "Target URL": 280,
    "Anchor": 180,
    "DR": 50,
    "Campaign / Source": 200,
    "Cost": 90,
    "Partner": 160,
}


def _list_campaign_tabs(svc, sid, monthly_tab_names: set[str]):
    meta = svc.spreadsheets().get(spreadsheetId=sid, fields="sheets(properties(title))").execute()
    out = []
    for s in meta.get("sheets", []):
        name = s["properties"]["title"]
        if name in EXCLUDED_TABS or name in monthly_tab_names:
            continue
        out.append(name)
    return out


def _month_key(date_str: str) -> str | None:
    """Return 'YYYY-MM' if the input is a valid ISO date prefix, else None."""
    d = (date_str or "").strip()
    if len(d) < 7 or d[4] != "-":
        return None
    return d[:7]


import re

MONTH_LOOKUP = {
    **{name.lower(): i for i, name in MONTH_FULL.items()},
    **{name.lower()[:3]: i for i, name in MONTH_FULL.items()},  # 3-letter abbreviations
}


def _month_key_from_tab_name(name: str) -> str | None:
    """Parse a tab name like 'May 2026', 'June 26', 'June 26\\'', 'Links 2026-05',
    'Jun-2026', or '2026-05' into 'YYYY-MM'. Returns None if no clear month/year found."""
    s = name.strip().lower().rstrip("'").rstrip("’")
    # Try YYYY-MM directly
    m = re.search(r"\b(\d{4})[-/](\d{1,2})\b", s)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            return f"{y:04d}-{mo:02d}"
    # Try MonthName + year (year can be 2 or 4 digits)
    m = re.search(r"\b([a-z]+)\s*[-,/ ]?\s*(\d{2,4})\b", s)
    if m:
        month_word, year_str = m.group(1), m.group(2)
        mo = MONTH_LOOKUP.get(month_word)
        if mo:
            y = int(year_str)
            if y < 100:
                y += 2000
            return f"{y:04d}-{mo:02d}"
    return None


def _find_monthly_tabs_by_header(svc, sid: str) -> dict[str, tuple[int, str]]:
    """Return {month_key (YYYY-MM): (tab_id, tab_name)} for all tabs whose header
    matches MONTHLY_HEADERS. Month is parsed PRIMARILY from the tab name (e.g.
    'May 2026', 'June 26\\'', 'Links 2026-05'); falls back to first data row's date
    only if the name can't be parsed."""
    meta = svc.spreadsheets().get(spreadsheetId=sid, fields="sheets(properties(title,sheetId))").execute()
    found: dict[str, tuple[int, str]] = {}
    for s in meta.get("sheets", []):
        name = s["properties"]["title"]
        tab_id = s["properties"]["sheetId"]
        if name in EXCLUDED_TABS:
            continue
        # Cheap header peek
        try:
            v = svc.spreadsheets().values().get(
                spreadsheetId=sid, range=f"'{name.replace(chr(39), chr(39)+chr(39))}'!A1:H1"
            ).execute()
            header_row = v.get("values", [[]])[0] if v.get("values") else []
            if header_row != MONTHLY_HEADERS:
                continue
        except Exception:
            continue
        # Prefer month parsed from the tab name
        mk = _month_key_from_tab_name(name)
        if not mk:
            # Fallback: infer from first data row's Date Built
            v2 = svc.spreadsheets().values().get(
                spreadsheetId=sid, range=f"'{name.replace(chr(39), chr(39)+chr(39))}'!A2:A2"
            ).execute()
            date_row = v2.get("values", [[""]])[0]
            mk = _month_key(date_row[0] if date_row else "")
        if mk:
            found.setdefault(mk, (tab_id, name))
    return found


def _ensure_monthly_tab(svc, sid: str, month: str, existing_by_month: dict) -> tuple[int, str]:
    """Return (sheetId, tab_name) for the monthly tab. Uses existing tab if found
    (regardless of its current name), creates a new one with default 'Month YYYY'
    naming if not."""
    if month in existing_by_month:
        return existing_by_month[month]
    tab_name = default_tab_name(month)
    tab_id = _get_tab_id(sid, tab_name)
    if tab_id is not None:
        return tab_id, tab_name

    # Create the tab
    resp = svc.spreadsheets().batchUpdate(spreadsheetId=sid, body={
        "requests": [{"addSheet": {"properties": {"title": tab_name}}}]
    }).execute()
    tab_id = resp["replies"][0]["addSheet"]["properties"]["sheetId"]

    # Write header
    last_col = _col_letter(len(MONTHLY_HEADERS) - 1)
    svc.spreadsheets().values().update(
        spreadsheetId=sid,
        range=f"{tab_name}!A1:{last_col}1",
        valueInputOption="RAW",
        body={"values": [MONTHLY_HEADERS]},
    ).execute()

    # Style: dark header, frozen row, banded rows, column widths, Inter font
    requests = [
        # Inter font everywhere
        {"repeatCell": {
            "range": {"sheetId": tab_id, "startRowIndex": 0, "endRowIndex": 2000, "startColumnIndex": 0, "endColumnIndex": len(MONTHLY_HEADERS)},
            "cell": {"userEnteredFormat": {"textFormat": {"fontFamily": FONT, "fontSize": 10}}},
            "fields": "userEnteredFormat.textFormat(fontFamily,fontSize)",
        }},
        # Dark header
        {"repeatCell": {
            "range": {"sheetId": tab_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": len(MONTHLY_HEADERS)},
            "cell": {"userEnteredFormat": {
                "backgroundColor": HEADER_BG,
                "textFormat": {"fontFamily": FONT, "foregroundColor": HEADER_FG, "bold": True, "fontSize": 10},
                "horizontalAlignment": "LEFT", "verticalAlignment": "MIDDLE",
                "padding": {"top": 8, "bottom": 8, "left": 10, "right": 10},
            }},
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,padding)",
        }},
        # Reset rows 1+ to white so banded ranges show
        {"repeatCell": {
            "range": {"sheetId": tab_id, "startRowIndex": 1, "endRowIndex": 5000, "startColumnIndex": 0, "endColumnIndex": len(MONTHLY_HEADERS)},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                "textFormat": {"fontFamily": FONT, "bold": False, "fontSize": 10},
                "horizontalAlignment": "LEFT", "verticalAlignment": "MIDDLE",
            }},
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)",
        }},
        # Freeze header
        {"updateSheetProperties": {
            "properties": {"sheetId": tab_id, "gridProperties": {"frozenRowCount": 1}},
            "fields": "gridProperties.frozenRowCount",
        }},
        # Banded rows
        {"addBanding": {
            "bandedRange": {
                "range": {"sheetId": tab_id, "startRowIndex": 0, "startColumnIndex": 0, "endColumnIndex": len(MONTHLY_HEADERS)},
                "rowProperties": {"headerColor": HEADER_BG, "firstBandColor": BAND_PRIMARY, "secondBandColor": BAND_ALT},
            }
        }},
        # Date format on column A
        {"repeatCell": {
            "range": {"sheetId": tab_id, "startRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 1},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "yyyy-mm-dd"}}},
            "fields": "userEnteredFormat.numberFormat",
        }},
        # DR centered + integer
        {"repeatCell": {
            "range": {"sheetId": tab_id, "startRowIndex": 1, "startColumnIndex": 4, "endColumnIndex": 5},
            "cell": {"userEnteredFormat": {
                "numberFormat": {"type": "NUMBER", "pattern": "0"},
                "horizontalAlignment": "CENTER", "textFormat": {"bold": True},
            }},
            "fields": "userEnteredFormat(numberFormat,horizontalAlignment,textFormat)",
        }},
        # Cost as USD
        {"repeatCell": {
            "range": {"sheetId": tab_id, "startRowIndex": 1, "startColumnIndex": 6, "endColumnIndex": 7},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "CURRENCY", "pattern": "\"$\"#,##0.00"}}},
            "fields": "userEnteredFormat.numberFormat",
        }},
    ]
    # Column widths
    for i, h in enumerate(MONTHLY_HEADERS):
        requests.append({
            "updateDimensionProperties": {
                "range": {"sheetId": tab_id, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
                "properties": {"pixelSize": WIDTHS.get(h, 120)},
                "fields": "pixelSize",
            }
        })
    svc.spreadsheets().batchUpdate(spreadsheetId=sid, body={"requests": requests}).execute()
    return tab_id, tab_name


def _read_monthly_tab(svc, sid: str, tab_name: str) -> list[dict]:
    """Read existing rows from a monthly tab so we can preserve manual edits."""
    rng = f"{tab_name}!A1:H"
    resp = svc.spreadsheets().values().get(spreadsheetId=sid, range=rng).execute()
    values = resp.get("values", [])
    if not values:
        return []
    headers = values[0]
    rows = []
    for row in values[1:]:
        padded = row + [""] * (len(headers) - len(row))
        rows.append({headers[i]: padded[i] for i in range(len(headers))})
    return rows


def main():
    import argparse
    p = argparse.ArgumentParser(description="Build/refresh per-month link tabs.")
    p.add_argument("--import-from-campaigns", action="store_true",
                   help="One-time bulk import: pull all campaign-tab rows with link_placed_at+link_placed_url into monthly tabs. By default the script does NOT auto-sync — monthly tabs are user-managed.")
    args = p.parse_args()

    svc = _sheets_service()
    sid = ensure_master_sheet()

    # 0. Discover existing monthly tabs by header signature
    existing_by_month = _find_monthly_tabs_by_header(svc, sid)
    monthly_tab_names = {n for _, n in existing_by_month.values()}
    if existing_by_month:
        print(f"existing monthly tabs: {[(m, n) for m, (_, n) in existing_by_month.items()]}")

    # 1. Ensure the CURRENT month tab exists (auto-create as months roll over).
    from datetime import datetime
    current_mk = datetime.now().strftime("%Y-%m")
    if current_mk not in existing_by_month:
        tab_id, tab_name = _ensure_monthly_tab(svc, sid, current_mk, existing_by_month)
        existing_by_month[current_mk] = (tab_id, tab_name)
        monthly_tab_names.add(tab_name)
        print(f"  auto-created current-month tab: {tab_name}")

    # 2. (Optional) bulk import from campaign tabs — DISABLED by default to prevent
    # the script from re-adding rows the user has deleted from monthly tabs.
    if args.import_from_campaigns:
        campaign_tabs = _list_campaign_tabs(svc, sid, monthly_tab_names)
        print(f"--import-from-campaigns: scanning {len(campaign_tabs)} campaign tabs...")
        links_by_month: dict[str, list[dict]] = defaultdict(list)
        for camp in campaign_tabs:
            try:
                rows = read_campaign_rows(sid, camp)
            except Exception as e:
                print(f"  warn: failed to read '{camp}': {e}")
                continue
            for r in rows:
                placed_at = (r.get("link_placed_at") or "").strip()
                placed_url = (r.get("link_placed_url") or "").strip()
                if not (placed_at and placed_url):
                    continue
                mk = _month_key(placed_at)
                if not mk:
                    continue
                links_by_month[mk].append({
                    "Date Built": placed_at,
                    "Page where link sits": (r.get("source_page") or "").strip(),
                    "Target URL": placed_url,
                    "Anchor": (r.get("anchor_text") or "").strip(),
                    "DR": r.get("dr", ""),
                    "Campaign / Source": camp,
                })
        total = sum(len(v) for v in links_by_month.values())
        print(f"  found {total} campaign-tab links to import")

        for month in sorted(links_by_month.keys()):
            new_records = links_by_month[month]
            tab_id, tab_name = _ensure_monthly_tab(svc, sid, month, existing_by_month)
            existing = _read_monthly_tab(svc, sid, tab_name)

            def norm(u: str) -> str:
                return (u or "").strip().rstrip("/").lower()
            existing_by_key = {norm(r.get(URL_KEY_COL, "")): r for r in existing if r.get(URL_KEY_COL)}

            merged = []
            seen_keys = set()
            for new_r in new_records:
                key = norm(new_r[URL_KEY_COL])
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                ex = existing_by_key.get(key, {})
                row = {}
                for h in MONTHLY_HEADERS:
                    if h in MANUAL_COLUMNS:
                        row[h] = ex.get(h, "")
                    else:
                        new_v = new_r.get(h, "")
                        row[h] = new_v if new_v not in ("", None) else ex.get(h, "")
                merged.append(row)
            for key, ex in existing_by_key.items():
                if key in seen_keys:
                    continue
                merged.append({h: ex.get(h, "") for h in MONTHLY_HEADERS})
            merged.sort(key=lambda r: (r.get("Date Built") or ""))

            values = [[r.get(h, "") for h in MONTHLY_HEADERS] for r in merged]
            svc.spreadsheets().values().clear(spreadsheetId=sid, range=f"{tab_name}!A2:H").execute()
            if values:
                last_col = _col_letter(len(MONTHLY_HEADERS) - 1)
                svc.spreadsheets().values().update(
                    spreadsheetId=sid,
                    range=f"{tab_name}!A2:{last_col}{1 + len(values)}",
                    valueInputOption="USER_ENTERED",
                    body={"values": values},
                ).execute()
            print(f"  {tab_name}: {len(merged)} rows after import")
    else:
        print("  (auto-sync from campaign tabs is OFF — monthly tabs are user-managed. "
              "Use --import-from-campaigns for one-off bulk import.)")

    # 3. Refresh _LinksData with LIVE formulas so the dashboard reflects any add/remove
    # in monthly tabs immediately, without re-running this script.
    _refresh_links_data_tab(svc, sid, existing_by_month, {})

    return 0


def _refresh_links_data_tab(svc, sid, existing_by_month, links_by_month):
    """Write a hidden _LinksData tab with LIVE FORMULAS aggregating from monthly tabs.
    The dashboard reads from here — when you add/remove rows in any monthly tab,
    the dashboard updates immediately (no script re-run needed).

    Layout:
      A1: 'total'         B1: total formula (sums all monthly tab rows)
      A2+: campaign names + COUNTIF formula across all monthly tabs (column F)
      E2+: month_key + COUNTA formula for that month's tab (column A2:A)
    """
    LINKS_DATA_TAB = "_LinksData"
    lt_id = _get_tab_id(sid, LINKS_DATA_TAB)
    if lt_id is None:
        resp = svc.spreadsheets().batchUpdate(spreadsheetId=sid, body={
            "requests": [{"addSheet": {"properties": {"title": LINKS_DATA_TAB, "hidden": True}}}]
        }).execute()
        lt_id = resp["replies"][0]["addSheet"]["properties"]["sheetId"]

    # Refresh discovery in case we just created new tabs in step 2
    by_month = _find_monthly_tabs_by_header(svc, sid)
    # Discover all unique Campaign / Source values across all monthly tabs so we can
    # build per-campaign COUNTIF formulas. Also include any campaign tab name (so
    # campaigns with 0 placements still show 0, not blank).
    campaign_values: set[str] = set()
    for mk, (_, tab_name) in by_month.items():
        rows = _read_monthly_tab(svc, sid, tab_name)
        for r in rows:
            v = (r.get("Campaign / Source") or "").strip()
            campaign_values.add(v if v else "(manual)")
    # Also include all known campaign tab names so 0-placement campaigns show
    for c in _list_campaign_tabs(svc, sid, {n for _, n in by_month.values()}):
        campaign_values.add(c)

    # Build formulas
    def quote_tab(n: str) -> str:
        return "'" + n.replace("'", "''") + "'"

    if by_month:
        # total = sum of COUNTA(A2:A) across all monthly tabs
        total_formula = "=" + "+".join(f"COUNTA({quote_tab(n)}!A2:A)" for _, n in by_month.values())
    else:
        total_formula = "=0"

    out_rows = [["total", total_formula, "", "", "month", "count"]]

    camps_sorted = sorted(campaign_values, key=lambda x: x.lower())
    months_sorted = sorted(by_month.keys())
    max_rows = max(len(camps_sorted), len(months_sorted), 1)
    for i in range(max_rows):
        if i < len(camps_sorted):
            camp = camps_sorted[i]
            # For "(manual)" we count rows where Campaign / Source is blank
            if camp == "(manual)":
                camp_formula = "=" + "+".join(
                    f'COUNTIFS({quote_tab(n)}!F2:F,"",{quote_tab(n)}!A2:A,"<>")'
                    for _, n in by_month.values()
                ) if by_month else "=0"
            else:
                escaped = camp.replace('"', '""')
                camp_formula = "=" + "+".join(
                    f'COUNTIF({quote_tab(n)}!F2:F,"{escaped}")' for _, n in by_month.values()
                ) if by_month else "=0"
        else:
            camp, camp_formula = "", ""
        if i < len(months_sorted):
            mk = months_sorted[i]
            _, tab_name = by_month[mk]
            month_formula = f"=COUNTA({quote_tab(tab_name)}!A2:A)"
        else:
            mk, month_formula = "", ""
        out_rows.append([camp, camp_formula, "", "", mk, month_formula])

    svc.spreadsheets().values().clear(spreadsheetId=sid, range=f"{LINKS_DATA_TAB}!A1:F").execute()
    svc.spreadsheets().values().update(
        spreadsheetId=sid,
        range=f"{LINKS_DATA_TAB}!A1",
        valueInputOption="USER_ENTERED",
        body={"values": out_rows},
    ).execute()
    print(f"  _LinksData refreshed with live formulas: {len(camps_sorted)} campaigns, {len(months_sorted)} months")


if __name__ == "__main__":
    sys.exit(main())
