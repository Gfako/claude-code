#!/usr/bin/env python3
"""Master sheet helper for /link-discover.

Owns the single 'Link Building Master Tracker' Google Sheet:
- Creates it on first use, persists ID in link-outreach/config.json.
- Ensures a campaign tab exists with the agreed schema + native checkboxes.
- Appends rows (dedup by source_page across the campaign tab).
- Reads / updates rows for filter, enrich, sync stages.
- Maintains a hidden _Data tab that aggregates per-campaign KPIs for the Dashboard.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build

PROJECT_ROOT = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects")
CONFIG_PATH = PROJECT_ROOT / "link-outreach" / "config.json"
TOKEN_PATH = PROJECT_ROOT / ".credentials" / "gdrive-token.pickle"
MASTER_SHEET_TITLE = "Link Building Master Tracker"

COLUMNS = [
    "source_technique",
    "added_to_sequence",
    "email_sent",
    "enrichment_ran",
    "blocked_by_replyio",
    "source_page",
    "excluded",
    "source_page_title",
    "domain",
    "language",
    "dr",
    "traffic",
    "broken_url",
    "anchor_text",
    "emails",
    "first_name",
    "last_name",
    "primary_contact_title",
    "reply_status",
    "reply_sequence",
    "last_activity_at",
    "discovered_at",
    "link_placed_at",
    "link_placed_url",
]
# Human-readable header labels — internal keys keep snake_case.
DISPLAY_LABELS = {
    "source_technique": "Source",
    "added_to_sequence": "Added in Sequence",
    "email_sent": "Sent",
    "enrichment_ran": "Enrichment ran",
    "blocked_by_replyio": "Blocked by Reply.io",
    "source_page": "Page",
    "excluded": "Excluded",
    "source_page_title": "Title",
    "domain": "Domain",
    "language": "Language",
    "dr": "DR",
    "traffic": "Traffic",
    "broken_url": "Target URL",
    "anchor_text": "Anchor",
    "emails": "Emails",
    "first_name": "First Name",
    "last_name": "Last Name",
    "primary_contact_title": "Role",
    "reply_status": "Status",
    "reply_sequence": "Sequence",
    "last_activity_at": "Last activity",
    "discovered_at": "Discovered",
    "link_placed_at": "Link placed date",
    "link_placed_url": "Link placed URL",
}
CHECKBOX_COLUMNS = ("added_to_sequence", "email_sent", "enrichment_ran", "blocked_by_replyio", "excluded")
DATE_COLUMNS = ("last_activity_at", "discovered_at", "link_placed_at")
FONT = "Inter"

DASHBOARD_TAB = "Dashboard"
DATA_TAB = "_Data"
SUMMARY_TAB = "_Summary"  # legacy; kept for back-compat

# Synthesia brand palette
HEADER_BG = {"red": 15 / 255, "green": 15 / 255, "blue": 15 / 255}
HEADER_FG = {"red": 1.0, "green": 1.0, "blue": 1.0}
BAND_PRIMARY = {"red": 1.0, "green": 1.0, "blue": 1.0}
BAND_ALT = {"red": 0.965, "green": 0.965, "blue": 0.969}
ACCENT = {"red": 1.0, "green": 0.31, "blue": 0.21}  # #FF4F35
KPI_BG = {"red": 0.98, "green": 0.98, "blue": 0.98}  # #FAFAFA

# DR conditional-format colors
DR_GREEN = {"red": 0.835, "green": 0.945, "blue": 0.851}
DR_YELLOW = {"red": 0.988, "green": 0.945, "blue": 0.749}
DR_AMBER = {"red": 0.988, "green": 0.871, "blue": 0.749}
DR_RED = {"red": 0.988, "green": 0.831, "blue": 0.831}


def _load_creds():
    with open(TOKEN_PATH, "rb") as f:
        return pickle.load(f)


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def _sheets_service():
    return build("sheets", "v4", credentials=_load_creds(), cache_discovery=False)


def _col_letter(idx: int) -> str:
    letters = ""
    n = idx
    while True:
        letters = chr(ord("A") + (n % 26)) + letters
        n = n // 26 - 1
        if n < 0:
            break
    return letters


def ensure_master_sheet() -> str:
    """Return master sheet ID, creating the sheet on first use."""
    cfg = _load_config()
    sheet_id = cfg.get("link_discover", {}).get("master_sheet_id")
    if sheet_id:
        return sheet_id

    sheets = _sheets_service()
    created = sheets.spreadsheets().create(
        body={
            "properties": {"title": MASTER_SHEET_TITLE},
            "sheets": [{"properties": {"title": DASHBOARD_TAB}}],
        },
        fields="spreadsheetId",
    ).execute()
    sheet_id = created["spreadsheetId"]
    cfg.setdefault("link_discover", {})["master_sheet_id"] = sheet_id
    _save_config(cfg)
    return sheet_id


def _get_tab_id(sheet_id: str, tab_name: str) -> int | None:
    meta = _sheets_service().spreadsheets().get(spreadsheetId=sheet_id, fields="sheets.properties").execute()
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == tab_name:
            return s["properties"]["sheetId"]
    return None


def _all_tabs(sheet_id: str) -> list[tuple[str, int]]:
    meta = _sheets_service().spreadsheets().get(spreadsheetId=sheet_id, fields="sheets.properties").execute()
    return [(s["properties"]["title"], s["properties"]["sheetId"]) for s in meta.get("sheets", [])]


def _campaign_tab_names(sheet_id: str) -> list[str]:
    """Public-facing campaign tabs (excludes hidden / dashboard / summary)."""
    skip = {DASHBOARD_TAB, DATA_TAB, SUMMARY_TAB}
    return [name for name, _ in _all_tabs(sheet_id) if name not in skip and not name.startswith("_")]


def _build_styling_requests(tab_id: int) -> list[dict[str, Any]]:
    """Return requests to apply Synthesia branding + conditional formatting to a campaign tab."""
    n_cols = len(COLUMNS)
    last_col = n_cols  # endColumnIndex is exclusive

    dr_col = COLUMNS.index("dr")
    traffic_col = COLUMNS.index("traffic")
    email_sent_col = COLUMNS.index("email_sent")
    link_placed_col = COLUMNS.index("link_placed_at")

    requests: list[dict[str, Any]] = []

    # Default Inter font across the whole sheet
    requests.append({
        "repeatCell": {
            "range": {"sheetId": tab_id, "startRowIndex": 0, "endRowIndex": 2000, "startColumnIndex": 0, "endColumnIndex": last_col},
            "cell": {"userEnteredFormat": {"textFormat": {"fontFamily": FONT, "fontSize": 10}}},
            "fields": "userEnteredFormat.textFormat(fontFamily,fontSize)",
        }
    })

    # Header: dark bg + white bold text + Inter
    requests.append({
        "repeatCell": {
            "range": {"sheetId": tab_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": last_col},
            "cell": {"userEnteredFormat": {
                "backgroundColor": HEADER_BG,
                "textFormat": {"fontFamily": FONT, "foregroundColor": HEADER_FG, "bold": True, "fontSize": 10},
                "horizontalAlignment": "LEFT",
                "verticalAlignment": "MIDDLE",
                "padding": {"top": 8, "bottom": 8, "left": 10, "right": 10},
            }},
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,padding)",
        }
    })

    # Reset data rows: clear any stale background/bold so banded ranges take effect cleanly.
    # Without this, rows that previously had header styling (from a prior buggy state) keep the dark bg.
    requests.append({
        "repeatCell": {
            "range": {"sheetId": tab_id, "startRowIndex": 1, "endRowIndex": 5000, "startColumnIndex": 0, "endColumnIndex": last_col},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                "textFormat": {"fontFamily": FONT, "foregroundColor": {"red": 0.0, "green": 0.0, "blue": 0.0}, "bold": False, "fontSize": 10},
                "horizontalAlignment": "LEFT",
                "verticalAlignment": "MIDDLE",
            }},
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)",
        }
    })

    # Freeze header
    requests.append({"updateSheetProperties": {
        "properties": {"sheetId": tab_id, "gridProperties": {"frozenRowCount": 1}},
        "fields": "gridProperties.frozenRowCount",
    }})

    # Banded rows for the data area
    requests.append({
        "addBanding": {
            "bandedRange": {
                "range": {"sheetId": tab_id, "startRowIndex": 0, "startColumnIndex": 0, "endColumnIndex": last_col},
                "rowProperties": {
                    "headerColor": HEADER_BG,
                    "firstBandColor": BAND_PRIMARY,
                    "secondBandColor": BAND_ALT,
                },
            }
        }
    })

    # DR conditional formats (lowest priority first; Sheets applies them in order)
    def cf_request(min_v: float, max_v: float | None, bg: dict) -> dict:
        if max_v is None:
            cond = {"type": "NUMBER_GREATER_THAN_EQ", "values": [{"userEnteredValue": str(min_v)}]}
        else:
            cond = {"type": "NUMBER_BETWEEN", "values": [
                {"userEnteredValue": str(min_v)},
                {"userEnteredValue": str(max_v)},
            ]}
        return {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": tab_id, "startRowIndex": 1, "startColumnIndex": dr_col, "endColumnIndex": dr_col + 1}],
                    "booleanRule": {"condition": cond, "format": {"backgroundColor": bg}},
                },
                "index": 0,
            }
        }

    requests.append(cf_request(70, None, DR_GREEN))
    requests.append(cf_request(50, 69, DR_YELLOW))
    requests.append(cf_request(30, 49, DR_AMBER))
    requests.append(cf_request(0, 29, DR_RED))

    # Row-level highlight: light-green when email_sent is TRUE
    requests.append({
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": tab_id, "startRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": last_col}],
                "booleanRule": {
                    "condition": {"type": "CUSTOM_FORMULA", "values": [
                        {"userEnteredValue": f"=AND(${_col_letter(email_sent_col)}2=TRUE, ${_col_letter(link_placed_col)}2=\"\")"}
                    ]},
                    "format": {"backgroundColor": {"red": 0.91, "green": 0.97, "blue": 0.91}},
                },
            },
            "index": 0,
        }
    })

    # Row-level highlight: dark-green tint ONLY when BOTH link_placed_at (date) AND
    # link_placed_url are filled. "Built" requires both — Reply.io 'won' alone isn't enough.
    link_placed_url_col = COLUMNS.index("link_placed_url")
    requests.append({
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": tab_id, "startRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": last_col}],
                "booleanRule": {
                    "condition": {"type": "CUSTOM_FORMULA", "values": [
                        {"userEnteredValue": f"=AND(${_col_letter(link_placed_col)}2<>\"\", ${_col_letter(link_placed_url_col)}2<>\"\")"}
                    ]},
                    "format": {
                        "backgroundColor": {"red": 0.78, "green": 0.92, "blue": 0.78},
                        "textFormat": {"bold": True},
                    },
                },
            },
            "index": 0,
        }
    })

    # Number formatting: traffic with thousands separator
    requests.append({
        "repeatCell": {
            "range": {"sheetId": tab_id, "startRowIndex": 1, "startColumnIndex": traffic_col, "endColumnIndex": traffic_col + 1},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}}},
            "fields": "userEnteredFormat.numberFormat",
        }
    })
    # DR as plain integer
    requests.append({
        "repeatCell": {
            "range": {"sheetId": tab_id, "startRowIndex": 1, "startColumnIndex": dr_col, "endColumnIndex": dr_col + 1},
            "cell": {"userEnteredFormat": {
                "numberFormat": {"type": "NUMBER", "pattern": "0"},
                "horizontalAlignment": "CENTER",
                "textFormat": {"bold": True},
            }},
            "fields": "userEnteredFormat(numberFormat,horizontalAlignment,textFormat)",
        }
    })
    # Dates
    for col_name in DATE_COLUMNS:
        idx = COLUMNS.index(col_name)
        requests.append({
            "repeatCell": {
                "range": {"sheetId": tab_id, "startRowIndex": 1, "startColumnIndex": idx, "endColumnIndex": idx + 1},
                "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "yyyy-mm-dd"}}},
                "fields": "userEnteredFormat.numberFormat",
            }
        })

    # Column widths (approx, in pixels).
    widths = {
        "source_technique": 130,
        "added_to_sequence": 75,
        "email_sent": 60,
        "enrichment_ran": 90,
        "blocked_by_replyio": 95,
        "source_page": 320,
        "excluded": 75,
        "source_page_title": 280,
        "domain": 160,
        "language": 70,
        "dr": 50,
        "traffic": 90,
        "broken_url": 280,
        "anchor_text": 160,
        "emails": 240,
        "first_name": 110,
        "last_name": 130,
        "primary_contact_title": 160,
        "reply_status": 100,
        "reply_sequence": 140,
        "last_activity_at": 110,
        "discovered_at": 100,
        "link_placed_at": 120,
        "link_placed_url": 280,
    }
    for col_name, px in widths.items():
        idx = COLUMNS.index(col_name)
        requests.append({
            "updateDimensionProperties": {
                "range": {"sheetId": tab_id, "dimension": "COLUMNS", "startIndex": idx, "endIndex": idx + 1},
                "properties": {"pixelSize": px},
                "fields": "pixelSize",
            }
        })

    # Header row a bit taller
    requests.append({
        "updateDimensionProperties": {
            "range": {"sheetId": tab_id, "dimension": "ROWS", "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 34},
            "fields": "pixelSize",
        }
    })

    return requests


def apply_campaign_tab_styling(sheet_id: str, campaign: str) -> None:
    """Idempotent: (re)apply Synthesia branding + conditional formatting to a campaign tab.
    Also rewrites the header row with human-readable display labels."""
    tab_id = _get_tab_id(sheet_id, campaign)
    if tab_id is None:
        raise RuntimeError(f"tab not found: {campaign}")
    sheets = _sheets_service()

    last_col = _col_letter(len(COLUMNS) - 1)
    sheets.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{campaign}!A1:{last_col}1",
        valueInputOption="RAW",
        body={"values": [[DISPLAY_LABELS[c] for c in COLUMNS]]},
    ).execute()

    meta = sheets.spreadsheets().get(spreadsheetId=sheet_id, fields="sheets(properties,conditionalFormats,bandedRanges)").execute()
    cleanup: list[dict[str, Any]] = []
    for s in meta.get("sheets", []):
        if s["properties"]["sheetId"] != tab_id:
            continue
        for i in range(len(s.get("conditionalFormats", []))):
            cleanup.append({"deleteConditionalFormatRule": {"sheetId": tab_id, "index": 0}})
        for b in s.get("bandedRanges", []) or []:
            cleanup.append({"deleteBanding": {"bandedRangeId": b["bandedRangeId"]}})
    if cleanup:
        sheets.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": cleanup}).execute()
    sheets.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": _build_styling_requests(tab_id)}).execute()


def ensure_data_tab(sheet_id: str) -> int:
    """Ensure the hidden _Data aggregation tab exists with header. Returns its tabId."""
    tab_id = _get_tab_id(sheet_id, DATA_TAB)
    if tab_id is not None:
        return tab_id
    sheets = _sheets_service()
    resp = sheets.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": [{"addSheet": {"properties": {"title": DATA_TAB, "hidden": True}}}]},
    ).execute()
    tab_id = resp["replies"][0]["addSheet"]["properties"]["sheetId"]
    header = ["campaign", "rows", "qualified", "with_emails", "contacted", "replied", "placed", "last_activity"]
    sheets.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{DATA_TAB}!A1",
        valueInputOption="RAW",
        body={"values": [header]},
    ).execute()
    return tab_id


def _register_campaign_in_data(sheet_id: str, campaign: str) -> None:
    """Append a formula row in _Data for this campaign (idempotent)."""
    ensure_data_tab(sheet_id)
    sheets = _sheets_service()
    existing = sheets.spreadsheets().values().get(spreadsheetId=sheet_id, range=f"{DATA_TAB}!A2:A").execute().get("values", [])
    names = [r[0] for r in existing if r]
    if campaign in names:
        return

    def cidx(col: str) -> str:
        return _col_letter(COLUMNS.index(col))

    sp = cidx("source_page")
    dr = cidx("dr")
    emails = cidx("emails")
    # "Contacted" = added to a Reply.io sequence, not "email delivered".
    sent = cidx("added_to_sequence")
    reply = cidx("reply_status")
    placed = cidx("link_placed_at")
    placed_url = cidx("link_placed_url")
    last_act = cidx("last_activity_at")

    safe_name = campaign.replace("'", "''")
    ref = f"'{safe_name}'"
    # "placed" reads from _LinksData (the monthly-tabs aggregate), so manual rows added
    # directly to monthly tabs count too. Falls back to 0 if _LinksData doesn't exist yet.
    placed_formula = f'=IFERROR(VLOOKUP("{safe_name}",_LinksData!A:B,2,FALSE),0)'
    formulas = [
        campaign,
        f"=COUNTA({ref}!{sp}2:{sp})",
        f"=COUNTIFS({ref}!{dr}2:{dr},\">=30\")",
        f"=COUNTIFS({ref}!{emails}2:{emails},\"<>\")",
        f"=COUNTIFS({ref}!{sent}2:{sent},TRUE)",
        f"=COUNTIFS({ref}!{reply}2:{reply},\"replied\")",
        placed_formula,
        f"=IFERROR(IF(COUNTA({ref}!{last_act}2:{last_act})=0,\"\",MAX({ref}!{last_act}2:{last_act})),\"\")",
    ]
    sheets.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=f"{DATA_TAB}!A2",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [formulas]},
    ).execute()


def ensure_campaign_tab(sheet_id: str, campaign: str) -> int:
    """Return the tab's sheetId; create tab + headers + Synthesia branding on first call."""
    tab_id = _get_tab_id(sheet_id, campaign)
    if tab_id is not None:
        return tab_id

    sheets = _sheets_service()
    resp = sheets.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": [{"addSheet": {"properties": {"title": campaign}}}]},
    ).execute()
    tab_id = resp["replies"][0]["addSheet"]["properties"]["sheetId"]

    last_col = _col_letter(len(COLUMNS) - 1)
    sheets.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{campaign}!A1:{last_col}1",
        valueInputOption="RAW",
        body={"values": [[DISPLAY_LABELS[c] for c in COLUMNS]]},
    ).execute()

    sheets.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": _build_styling_requests(tab_id)}).execute()
    _register_campaign_in_data(sheet_id, campaign)
    # Refresh the _Monthly tab so the new campaign is included in the live monthly formulas.
    # Lazy import to avoid a circular dependency with setup_dashboard.
    try:
        from setup_dashboard import _refresh_monthly  # type: ignore
        _refresh_monthly(sheet_id)
    except Exception:
        pass
    return tab_id


def read_campaign_rows(sheet_id: str, campaign: str) -> list[dict[str, str]]:
    ensure_campaign_tab(sheet_id, campaign)
    last_col = _col_letter(len(COLUMNS) - 1)
    resp = _sheets_service().spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"{campaign}!A2:{last_col}",
    ).execute()
    rows = resp.get("values", [])
    sp_idx = COLUMNS.index("source_page")
    out = []
    for r in rows:
        padded = r + [""] * (len(COLUMNS) - len(r))
        if not padded[sp_idx]:
            continue
        out.append({col: padded[i] for i, col in enumerate(COLUMNS)})
    return out


def existing_source_pages(sheet_id: str, campaign: str) -> set[str]:
    return {r["source_page"].strip().rstrip("/") for r in read_campaign_rows(sheet_id, campaign) if r.get("source_page")}


def _apply_checkbox_validation(sheet_id: str, tab_id: int, start_row: int, end_row: int) -> None:
    requests = []
    for col_name in CHECKBOX_COLUMNS:
        col_idx = COLUMNS.index(col_name)
        requests.append({
            "setDataValidation": {
                "range": {"sheetId": tab_id, "startRowIndex": start_row, "endRowIndex": end_row, "startColumnIndex": col_idx, "endColumnIndex": col_idx + 1},
                "rule": {"condition": {"type": "BOOLEAN"}, "strict": True, "showCustomUi": True},
            }
        })
    _sheets_service().spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": requests}).execute()


def _parse_updated_range(rng: str) -> tuple[int, int]:
    after_bang = rng.split("!", 1)[1] if "!" in rng else rng
    parts = after_bang.split(":")
    def row_of(cell: str) -> int:
        return int("".join(c for c in cell if c.isdigit()))
    start = row_of(parts[0])
    end = row_of(parts[1]) if len(parts) > 1 else start
    return start, end


def append_rows(sheet_id: str, campaign: str, rows: list[dict[str, Any]]) -> int:
    tab_id = ensure_campaign_tab(sheet_id, campaign)
    existing = existing_source_pages(sheet_id, campaign)

    to_append: list[list[Any]] = []
    seen_in_batch: set[str] = set()
    for r in rows:
        sp = (r.get("source_page") or "").strip().rstrip("/")
        if not sp or sp in existing or sp in seen_in_batch:
            continue
        seen_in_batch.add(sp)
        row_values = []
        for col in COLUMNS:
            v = r.get(col, "")
            if col in CHECKBOX_COLUMNS:
                row_values.append(bool(v))
            else:
                row_values.append("" if v is None else v)
        to_append.append(row_values)

    if not to_append:
        return 0

    last_col = _col_letter(len(COLUMNS) - 1)
    # Use OVERWRITE (default) — INSERT_ROWS shifts formula references in other tabs (e.g. _Data).
    resp = _sheets_service().spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=f"{campaign}!A2:{last_col}",
        valueInputOption="USER_ENTERED",
        insertDataOption="OVERWRITE",
        body={"values": to_append},
    ).execute()
    updated_range = resp.get("updates", {}).get("updatedRange")
    if updated_range:
        start, end = _parse_updated_range(updated_range)
        _apply_checkbox_validation(sheet_id, tab_id, start - 1, end)
    return len(to_append)


def update_row_by_source_page(sheet_id: str, campaign: str, source_page: str, patch: dict[str, Any]) -> bool:
    rows = read_campaign_rows(sheet_id, campaign)
    sp_target = source_page.strip().rstrip("/")
    row_idx = None
    for i, r in enumerate(rows):
        if r.get("source_page", "").strip().rstrip("/") == sp_target:
            row_idx = i + 2
            break
    if row_idx is None:
        return False

    sheets = _sheets_service()
    data = []
    for col, val in patch.items():
        if col not in COLUMNS:
            continue
        col_letter = _col_letter(COLUMNS.index(col))
        cell_value = bool(val) if col in CHECKBOX_COLUMNS else ("" if val is None else val)
        data.append({"range": f"{campaign}!{col_letter}{row_idx}", "values": [[cell_value]]})

    if not data:
        return True
    sheets.spreadsheets().values().batchUpdate(
        spreadsheetId=sheet_id,
        body={"valueInputOption": "USER_ENTERED", "data": data},
    ).execute()
    return True


def update_summary(sheet_id: str, campaign: str) -> None:
    """No-op kept for back-compat: the Dashboard reads live from _Data formulas."""
    _register_campaign_in_data(sheet_id, campaign)


def sheet_url(sheet_id: str, campaign: str | None = None) -> str:
    base = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
    if not campaign:
        return base
    tab_id = _get_tab_id(sheet_id, campaign)
    return f"{base}#gid={tab_id}" if tab_id is not None else base


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("usage: sheets_helper.py {init|ensure-tab <campaign>|style <campaign>|url [campaign]|list-campaigns}")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "init":
        sid = ensure_master_sheet()
        print(f"master_sheet_id: {sid}")
        print(f"url: {sheet_url(sid)}")
    elif cmd == "ensure-tab":
        sid = ensure_master_sheet()
        ensure_campaign_tab(sid, sys.argv[2])
        print(sheet_url(sid, sys.argv[2]))
    elif cmd == "style":
        sid = ensure_master_sheet()
        apply_campaign_tab_styling(sid, sys.argv[2])
        _register_campaign_in_data(sid, sys.argv[2])
        print(f"styled: {sys.argv[2]}")
    elif cmd == "url":
        sid = ensure_master_sheet()
        print(sheet_url(sid, sys.argv[2] if len(sys.argv) > 2 else None))
    elif cmd == "list-campaigns":
        sid = ensure_master_sheet()
        for name in _campaign_tab_names(sid):
            print(name)
    else:
        print(f"unknown command: {cmd}")
        sys.exit(1)
