#!/usr/bin/env python3
"""Build / refresh the Dashboard tab of the Link Building Master Tracker.

Layout (Synthesia brand, 10-column wide canvas A:J):

  A1:J2   — title strip (dark, white Inter bold) + subtitle band
  A4:J7   — 5 KPI tiles (each spans 2 cols). All tiles share a light card
            background; "BUILT THIS MONTH" gets the accent treatment via
            number color.
  A9:J9   — "Links built by month" section header
  A11:J27 — embedded column chart sourced from _Monthly
  A29:J29 — "Campaigns" section header
  A30:J…  — per-campaign table (live QUERY from _Data with display labels)
  A52:J52 — "Recent wins" section header
  A53:J…  — recent wins (placed links across all campaigns)

The hidden _Monthly tab is recomputed by this script. KPI tiles and the
campaigns table are live formulas that don't need a rebuild.

Usage:
  python3 setup_dashboard.py            # full build / refresh
  python3 setup_dashboard.py refresh    # only refresh _Monthly data
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sheets_helper import (  # noqa: E402
    ACCENT,
    COLUMNS,
    DASHBOARD_TAB,
    DATA_TAB,
    FONT,
    HEADER_BG,
    HEADER_FG,
    KPI_BG,
    _all_tabs,
    _campaign_tab_names,
    _col_letter,
    _get_tab_id,
    _sheets_service,
    ensure_master_sheet,
    read_campaign_rows,
    ensure_data_tab,
)


def _list_monthly_link_tab_names(sheet_id: str) -> list[str]:
    """Return tab names whose first row matches the monthly-link-tab header signature.
    Lets the user name tabs anything (May 2026, June 26', etc.) and still be discovered."""
    from build_monthly_link_tabs import MONTHLY_HEADERS  # type: ignore
    svc = _sheets_service()
    meta = svc.spreadsheets().get(spreadsheetId=sheet_id, fields="sheets(properties(title))").execute()
    out = []
    for s in meta.get("sheets", []):
        name = s["properties"]["title"]
        if name in {"Dashboard", "_Data", "_Monthly", "_LinksData", "_Summary"}:
            continue
        try:
            v = svc.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=f"'{name.replace(chr(39), chr(39)+chr(39))}'!A1:H1",
            ).execute()
            header_row = v.get("values", [[]])[0] if v.get("values") else []
            if header_row == MONTHLY_HEADERS:
                out.append(name)
        except Exception:
            continue
    return out


def _column_letter_map() -> dict:
    """Live column-letter mapping based on the current COLUMNS list.
    Use this everywhere — never hardcode column letters that can shift."""
    return {col: _col_letter(COLUMNS.index(col)) for col in COLUMNS}

MONTHLY_TAB = "_Monthly"
N_COLS = 12  # canvas width (A:L) — 6 KPI tiles at 2 cols each


def _ensure_tab(sheet_id: str, name: str, hidden: bool = False) -> int:
    tab_id = _get_tab_id(sheet_id, name)
    if tab_id is not None:
        return tab_id
    props = {"title": name}
    if hidden:
        props["hidden"] = True
    resp = _sheets_service().spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": [{"addSheet": {"properties": props}}]},
    ).execute()
    return resp["replies"][0]["addSheet"]["properties"]["sheetId"]


def _clear_tab(sheet_id: str, tab_name: str) -> None:
    _sheets_service().spreadsheets().values().clear(
        spreadsheetId=sheet_id, range=f"{tab_name}!A1:Z200",
    ).execute()


def _write(sheet_id: str, tab: str, a1: str, values: list[list]) -> None:
    _sheets_service().spreadsheets().values().update(
        spreadsheetId=sheet_id, range=f"{tab}!{a1}",
        valueInputOption="USER_ENTERED", body={"values": values},
    ).execute()


def _last_12_months() -> list[tuple[int, int]]:
    today = date.today()
    out: list[tuple[int, int]] = []
    y, m = today.year, today.month
    for _ in range(12):
        out.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    out.reverse()
    return out


MONTH_ABBR = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}


def _compute_monthly_breakdown(sheet_id: str) -> list[dict]:
    """For last 12 months, aggregate across every campaign tab:
      - discovered: rows where discovered_at[:7] == month
      - emails_sent: rows where email_sent=TRUE AND last_activity_at[:7] == month
      - replied: rows where reply_status=='replied' AND last_activity_at[:7] == month
      - built: rows where link_placed_at[:7] == month
      - avg_dr_built: average DR of rows placed in that month
    """
    months = _last_12_months()
    keys = [f"{y:04d}-{mm:02d}" for y, mm in months]
    agg = {k: {"discovered": 0, "emails_sent": 0, "replied": 0, "built": 0, "dr_sum": 0, "dr_count": 0} for k in keys}

    for campaign in _campaign_tab_names(sheet_id):
        try:
            rows = read_campaign_rows(sheet_id, campaign)
        except Exception:
            continue
        for r in rows:
            disc = (r.get("discovered_at") or "").strip()[:7]
            last = (r.get("last_activity_at") or "").strip()[:7]
            placed_date_raw = (r.get("link_placed_at") or "").strip()
            placed_url = (r.get("link_placed_url") or "").strip()
            # "Built" requires BOTH a date AND a destination URL
            placed = placed_date_raw[:7] if (placed_date_raw and placed_url and len(placed_date_raw) >= 7 and placed_date_raw[4] == "-") else ""
            # "Contacted" = added to a Reply.io sequence (we initiated outreach),
            # not "delivered" — delivery is a Reply.io-internal milestone we don't care about for outreach volume.
            sent = str(r.get("added_to_sequence")).strip().upper() == "TRUE"
            replied = (r.get("reply_status") or "").strip().lower() == "replied"
            try:
                dr = int(float(r.get("dr") or 0))
            except (TypeError, ValueError):
                dr = 0

            # Sent/replied attribution: prefer Reply.io's last_activity_at month;
            # fall back to discovered_at if the user ticked the checkbox manually
            # without sync_replyio writing a date.
            sent_month = last if last in agg else (disc if disc in agg else None)
            replied_month = last if last in agg else (disc if disc in agg else None)

            if disc in agg:
                agg[disc]["discovered"] += 1
            if sent and sent_month:
                agg[sent_month]["emails_sent"] += 1
            if replied and replied_month:
                agg[replied_month]["replied"] += 1
            if placed in agg:
                agg[placed]["built"] += 1
                if dr > 0:
                    agg[placed]["dr_sum"] += dr
                    agg[placed]["dr_count"] += 1

    out: list[dict] = []
    for (y, mm), key in zip(months, keys):
        a = agg[key]
        avg_dr = round(a["dr_sum"] / a["dr_count"]) if a["dr_count"] else ""
        out.append({
            "month_label": f"{MONTH_ABBR[mm]} {str(y)[2:]}",
            "month_key": key,
            "discovered": a["discovered"],
            "emails_sent": a["emails_sent"],
            "replied": a["replied"],
            "built": a["built"],
            "avg_dr": avg_dr,
        })
    return out


def _build_monthly_formulas(campaign_names: list[str]) -> list[list[str]]:
    """Generate 13 rows for _Monthly (header + 12 months) using live formulas across all campaigns.

    Columns:
      A = month_label (text, e.g. "May 26") for the chart
      B = links_placed  (built — requires date in S AND url in T)
      C = emails_sent   (email_sent=TRUE in C, last_activity in Q within month, fallback to discovered_at in R)
      D = replied       (reply_status='replied', last_activity in month or fallback to discovered_at)
      E = discovered    (discovered_at in R within month)
      F = avg_dr_built  (avg DR of rows placed in this month)
      G = month_start   (date, hidden — used for COUNTIFS bounds)
    """
    rows = [["month", "links_placed", "contacted", "replied", "discovered", "avg_dr_built", "month_start"]]

    if not campaign_names:
        for i in range(12):
            offset = 11 - i
            ms = f"=DATE(YEAR(TODAY()),MONTH(TODAY())-{offset},1)"
            rows.append([f"=TEXT(G{i+2},\"mmm yy\")", 0, 0, 0, 0, "—", ms])
        return rows

    # Resolve column letters at runtime so they stay correct after schema shifts.
    letters = _column_letter_map()
    PLACED = letters["link_placed_at"]
    PLACED_URL = letters["link_placed_url"]
    # "Contacted" = added to a Reply.io sequence, not "delivered". See agg loop above.
    SENT_CB = letters["added_to_sequence"]
    REPLY_STATUS = letters["reply_status"]
    LAST_ACT = letters["last_activity_at"]
    DISCOVERED = letters["discovered_at"]
    DR_COL = letters["dr"]

    def sum_across(formula_per_camp):
        return "=" + "+".join(formula_per_camp(c) for c in campaign_names)

    def safe(name: str) -> str:
        return name.replace("'", "''")

    for i in range(12):
        offset = 11 - i
        row_num = i + 2
        ms_formula = f"=DATE(YEAR(TODAY()),MONTH(TODAY())-{offset},1)"
        ms_ref = f"G{row_num}"
        me_ref = f"EOMONTH({ms_ref},0)"

        built = sum_across(lambda c: f"COUNTIFS('{safe(c)}'!{PLACED}:{PLACED},\">=\"&{ms_ref},'{safe(c)}'!{PLACED}:{PLACED},\"<=\"&{me_ref},'{safe(c)}'!{PLACED_URL}:{PLACED_URL},\"<>\")")
        sent = sum_across(lambda c: (
            f"COUNTIFS('{safe(c)}'!{SENT_CB}:{SENT_CB},TRUE,'{safe(c)}'!{LAST_ACT}:{LAST_ACT},\">=\"&{ms_ref},'{safe(c)}'!{LAST_ACT}:{LAST_ACT},\"<=\"&{me_ref})"
            f"+COUNTIFS('{safe(c)}'!{SENT_CB}:{SENT_CB},TRUE,'{safe(c)}'!{LAST_ACT}:{LAST_ACT},\"\",'{safe(c)}'!{DISCOVERED}:{DISCOVERED},\">=\"&{ms_ref},'{safe(c)}'!{DISCOVERED}:{DISCOVERED},\"<=\"&{me_ref})"
        ))
        replied_f = sum_across(lambda c: (
            f"COUNTIFS('{safe(c)}'!{REPLY_STATUS}:{REPLY_STATUS},\"replied\",'{safe(c)}'!{LAST_ACT}:{LAST_ACT},\">=\"&{ms_ref},'{safe(c)}'!{LAST_ACT}:{LAST_ACT},\"<=\"&{me_ref})"
            f"+COUNTIFS('{safe(c)}'!{REPLY_STATUS}:{REPLY_STATUS},\"replied\",'{safe(c)}'!{LAST_ACT}:{LAST_ACT},\"\",'{safe(c)}'!{DISCOVERED}:{DISCOVERED},\">=\"&{ms_ref},'{safe(c)}'!{DISCOVERED}:{DISCOVERED},\"<=\"&{me_ref})"
        ))
        discovered = sum_across(lambda c: f"COUNTIFS('{safe(c)}'!{DISCOVERED}:{DISCOVERED},\">=\"&{ms_ref},'{safe(c)}'!{DISCOVERED}:{DISCOVERED},\"<=\"&{me_ref})")
        # Avg DR built: weighted avg = total DR / total count, dash if zero
        built_count_clauses = "+".join(f"COUNTIFS('{safe(c)}'!{PLACED}:{PLACED},\">=\"&{ms_ref},'{safe(c)}'!{PLACED}:{PLACED},\"<=\"&{me_ref},'{safe(c)}'!{PLACED_URL}:{PLACED_URL},\"<>\")" for c in campaign_names)
        dr_sum_clauses = "+".join(f"SUMIFS('{safe(c)}'!{DR_COL}:{DR_COL},'{safe(c)}'!{PLACED}:{PLACED},\">=\"&{ms_ref},'{safe(c)}'!{PLACED}:{PLACED},\"<=\"&{me_ref},'{safe(c)}'!{PLACED_URL}:{PLACED_URL},\"<>\")" for c in campaign_names)
        avg_dr = f"=IFERROR(IF(({built_count_clauses})=0,\"—\",ROUND(({dr_sum_clauses})/({built_count_clauses}),0)),\"—\")"

        rows.append([
            f"=TEXT({ms_ref},\"mmm yy\")",
            built,
            sent,
            replied_f,
            discovered,
            avg_dr,
            ms_formula,
        ])
    return rows


def _refresh_monthly(sheet_id: str) -> None:
    """(Re)install live formulas in _Monthly. The Dashboard's visible Monthly Breakdown
    table references _Monthly via formulas (written by build_dashboard) so we don't have
    to touch the Dashboard tab here — it stays in sync automatically."""
    _ensure_tab(sheet_id, MONTHLY_TAB, hidden=True)
    _clear_tab(sheet_id, MONTHLY_TAB)

    campaigns = _campaign_tab_names(sheet_id)
    formula_rows = _build_monthly_formulas(campaigns)
    _write(sheet_id, MONTHLY_TAB, "A1", formula_rows)


def _monthly_breakdown_formulas() -> list[list[str]]:
    """Formulas for Dashboard rows 26-37 that mirror _Monthly with the column order
    expected by the visible table (Month, Discovered, Emails sent, Replied, Links built, Avg DR built)."""
    out = []
    for i in range(12):
        r = i + 2
        out.append([
            f"=_Monthly!A{r}",  # Month label
            f"=_Monthly!E{r}",  # Discovered
            f"=_Monthly!C{r}",  # Emails sent
            f"=_Monthly!D{r}",  # Replied
            f"=_Monthly!B{r}",  # Links built
            f"=_Monthly!F{r}",  # Avg DR built
        ])
    return out


def _delete_existing_chart(sheet_id: str, tab_id: int) -> None:
    meta = _sheets_service().spreadsheets().get(
        spreadsheetId=sheet_id, fields="sheets(properties,charts)").execute()
    chart_ids = []
    for s in meta.get("sheets", []):
        if s["properties"]["sheetId"] != tab_id:
            continue
        for c in s.get("charts", []) or []:
            chart_ids.append(c["chartId"])
    if not chart_ids:
        return
    requests = [{"deleteEmbeddedObject": {"objectId": cid}} for cid in chart_ids]
    _sheets_service().spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": requests}).execute()


def _reset_formatting(sheet_id: str, tab_id: int) -> None:
    """Wipe any stale conditional formats / banded ranges / merges on the Dashboard tab
    before rebuilding so the new layout doesn't get layered on top of the old one."""
    meta = _sheets_service().spreadsheets().get(
        spreadsheetId=sheet_id,
        fields="sheets(properties,conditionalFormats,bandedRanges,merges)",
    ).execute()
    cleanup: list[dict] = []
    for s in meta.get("sheets", []):
        if s["properties"]["sheetId"] != tab_id:
            continue
        for _ in range(len(s.get("conditionalFormats", []))):
            cleanup.append({"deleteConditionalFormatRule": {"sheetId": tab_id, "index": 0}})
        for b in s.get("bandedRanges", []) or []:
            cleanup.append({"deleteBanding": {"bandedRangeId": b["bandedRangeId"]}})
    # unmerge everything in the affected ranges
    cleanup.append({"unmergeCells": {"range": {"sheetId": tab_id, "startRowIndex": 0, "endRowIndex": 200, "startColumnIndex": 0, "endColumnIndex": N_COLS}}})
    # clear all formats
    cleanup.append({"updateCells": {
        "range": {"sheetId": tab_id, "startRowIndex": 0, "endRowIndex": 200, "startColumnIndex": 0, "endColumnIndex": N_COLS},
        "fields": "userEnteredFormat",
    }})
    if cleanup:
        _sheets_service().spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": cleanup}).execute()


def build_dashboard(sheet_id: str) -> None:
    dash_id = _ensure_tab(sheet_id, DASHBOARD_TAB, hidden=False)
    ensure_data_tab(sheet_id)
    _refresh_monthly(sheet_id)
    monthly_tab_id = _get_tab_id(sheet_id, MONTHLY_TAB)

    _delete_existing_chart(sheet_id, dash_id)
    _reset_formatting(sheet_id, dash_id)
    _clear_tab(sheet_id, DASHBOARD_TAB)

    # ─── content ──────────────────────────────────────────────────────
    # Title + subtitle
    _write(sheet_id, DASHBOARD_TAB, "A1", [["Link Building Master Tracker"]])
    _write(sheet_id, DASHBOARD_TAB, "A2", [["Discovery → outreach → placement, tracked across every campaign"]])

    # KPI tiles: 6 tiles spanning 2 cols each (A:B, C:D, E:F, G:H, I:J, K:L)
    # Row 4 = label, Row 5 = big number, Row 6 = sublabel
    tile_data = [
        # (start_col, label, value_formula, sublabel_formula)
        (0, "DISCOVERED",
         f"=SUM({DATA_TAB}!B2:B)",
         f"=IFERROR(SUM({DATA_TAB}!C2:C)&\" with DR ≥ 30\",\"\")"),
        (2, "WITH EMAILS",
         f"=SUM({DATA_TAB}!D2:D)",
         f"=IFERROR(IF(SUM({DATA_TAB}!B2:B)=0,\"\",ROUND(SUM({DATA_TAB}!D2:D)/SUM({DATA_TAB}!B2:B)*100,0)&\"% of discovered\"),\"\")"),
        (4, "CONTACTED",
         f"=SUM({DATA_TAB}!E2:E)",
         f"=IFERROR(IF(SUM({DATA_TAB}!D2:D)=0,\"awaiting emails\",ROUND(SUM({DATA_TAB}!E2:E)/SUM({DATA_TAB}!D2:D)*100,0)&\"% of reachable\"),\"\")"),
        (6, "REPLIED",
         f"=SUM({DATA_TAB}!F2:F)",
         f"=IFERROR(IF(SUM({DATA_TAB}!E2:E)=0,\"awaiting contact\",ROUND(SUM({DATA_TAB}!F2:F)/SUM({DATA_TAB}!E2:E)*100,1)&\"% reply rate\"),\"\")"),
        (8, "LINKS BUILT",
         "=IFERROR(_LinksData!B1,0)",
         f"=IFERROR(IF(SUM({DATA_TAB}!E2:E)=0,\"no outreach yet\",ROUND(IFERROR(_LinksData!B1,0)/SUM({DATA_TAB}!E2:E)*100,1)&\"% placement rate\"),\"\")"),
        (10, "BUILT THIS MONTH",
         "=IFERROR(VLOOKUP(DATE(YEAR(TODAY()),MONTH(TODAY()),1),_LinksData!E:F,2,FALSE),0)",
         "=IFERROR(SUM(_LinksData!F:F)&\" trailing 12 months\",\"\")"),
    ]

    for col, label, val, sub in tile_data:
        col_a = _col_letter(col)
        col_b = _col_letter(col + 1)
        _write(sheet_id, DASHBOARD_TAB, f"{col_a}4", [[label]])
        _write(sheet_id, DASHBOARD_TAB, f"{col_a}5", [[val]])
        _write(sheet_id, DASHBOARD_TAB, f"{col_a}6", [[sub]])

    # Section headers
    _write(sheet_id, DASHBOARD_TAB, "A9", [["MONTHLY TRENDS"]])

    # Monthly breakdown section (rows 24-37) — live formulas that reference _Monthly
    _write(sheet_id, DASHBOARD_TAB, "A24", [["MONTHLY BREAKDOWN"]])
    _write(sheet_id, DASHBOARD_TAB, "A25", [["Month", "Discovered", "Emails sent", "Replied", "Links built", "Avg DR built"]])
    _write(sheet_id, DASHBOARD_TAB, "A26", _monthly_breakdown_formulas())

    # Campaigns (shifted from row 29 → row 39)
    _write(sheet_id, DASHBOARD_TAB, "A39", [["CAMPAIGNS"]])
    _write(sheet_id, DASHBOARD_TAB, "A40", [["Campaign", "Discovered", "Qualified", "With emails", "Contacted", "Replied", "Links built", "Last activity"]])
    _write(sheet_id, DASHBOARD_TAB, "A41", [[
        f"=IFERROR(QUERY({DATA_TAB}!A2:H,\"select A,B,C,D,E,F,G,H where A is not null order by G desc, E desc\",0),\"\")"
    ]])

    # Recent wins (shifted from row 52 → row 60)
    _write(sheet_id, DASHBOARD_TAB, "A60", [["RECENT WINS"]])
    _write(sheet_id, DASHBOARD_TAB, "A61", [["Date placed", "Campaign", "Domain", "DR", "Source page"]])

    # Recent wins: VSTACK across all monthly link tabs. Reads each tab's columns:
    # A=Date Built, B=Page where link sits, E=DR, F=Campaign / Source.
    # Output columns: Date placed | Campaign | Domain | DR | Source page
    parts = []
    for tab_name in _list_monthly_link_tab_names(sheet_id):
        safe = tab_name.replace("'", "''")
        parts.append(
            f"IFERROR(FILTER({{ '{safe}'!A2:A, "
            f"'{safe}'!F2:F, "
            f"IFERROR(ARRAYFORMULA(REGEXEXTRACT('{safe}'!B2:B,\"https?://(?:www\\.)?([^/]+)\")),\"\"), "
            f"'{safe}'!E2:E, "
            f"'{safe}'!B2:B }}, '{safe}'!A2:A<>\"\"))"
        )
    if parts:
        stack_formula = "=IFERROR(SORT(VSTACK(" + "; ".join(parts) + "),1,FALSE),\"(no placed links yet)\")"
        _write(sheet_id, DASHBOARD_TAB, "A62", [[stack_formula]])
    else:
        _write(sheet_id, DASHBOARD_TAB, "A62", [["(no placed links yet)"]])

    # ─── styling ──────────────────────────────────────────────────────
    requests: list[dict] = []

    # Default Inter font on the whole canvas
    requests.append({
        "repeatCell": {
            "range": {"sheetId": dash_id, "startRowIndex": 0, "endRowIndex": 200, "startColumnIndex": 0, "endColumnIndex": N_COLS},
            "cell": {"userEnteredFormat": {"textFormat": {"fontFamily": FONT, "fontSize": 10}}},
            "fields": "userEnteredFormat.textFormat(fontFamily,fontSize)",
        }
    })

    # Title strip A1:J1 (merged, dark, bold)
    requests.append({"mergeCells": {"range": _r(dash_id, 0, 1, 0, N_COLS), "mergeType": "MERGE_ALL"}})
    requests.append({"repeatCell": {
        "range": _r(dash_id, 0, 1, 0, N_COLS),
        "cell": {"userEnteredFormat": {
            "backgroundColor": HEADER_BG,
            "textFormat": {"fontFamily": FONT, "foregroundColor": HEADER_FG, "bold": True, "fontSize": 18},
            "horizontalAlignment": "LEFT",
            "verticalAlignment": "MIDDLE",
            "padding": {"top": 18, "bottom": 18, "left": 24, "right": 24},
        }},
        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,padding)",
    }})
    requests.append(_dim_request(dash_id, "ROWS", 0, 1, 64))

    # Subtitle band A2:J2 (slightly darker than KPI bg, muted text)
    requests.append({"mergeCells": {"range": _r(dash_id, 1, 2, 0, N_COLS), "mergeType": "MERGE_ALL"}})
    requests.append({"repeatCell": {
        "range": _r(dash_id, 1, 2, 0, N_COLS),
        "cell": {"userEnteredFormat": {
            "backgroundColor": {"red": 0.13, "green": 0.13, "blue": 0.13},
            "textFormat": {"fontFamily": FONT, "foregroundColor": {"red": 0.7, "green": 0.7, "blue": 0.7}, "fontSize": 10},
            "horizontalAlignment": "LEFT",
            "padding": {"top": 8, "bottom": 8, "left": 24, "right": 24},
        }},
        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,padding)",
    }})

    # Row 3: empty white spacer
    requests.append(_dim_request(dash_id, "ROWS", 2, 3, 16))

    # KPI tiles — 5 tiles, each spans 2 cols
    label_color = {"red": 0.45, "green": 0.45, "blue": 0.45}
    value_color = {"red": 0.06, "green": 0.06, "blue": 0.06}
    sub_color = {"red": 0.4, "green": 0.4, "blue": 0.4}
    last_tile_idx = len(tile_data) - 1
    for ti, (col, label, val, sub) in enumerate(tile_data):
        is_accent = (ti == last_tile_idx)
        # merge label row across 2 cols
        for row_off in (3, 4, 5):
            requests.append({"mergeCells": {"range": _r(dash_id, row_off, row_off + 1, col, col + 2), "mergeType": "MERGE_ALL"}})
        # Background for all three rows
        requests.append({"repeatCell": {
            "range": _r(dash_id, 3, 6, col, col + 2),
            "cell": {"userEnteredFormat": {"backgroundColor": KPI_BG}},
            "fields": "userEnteredFormat.backgroundColor",
        }})
        # Label
        requests.append({"repeatCell": {
            "range": _r(dash_id, 3, 4, col, col + 2),
            "cell": {"userEnteredFormat": {
                "textFormat": {"fontFamily": FONT, "foregroundColor": label_color, "bold": True, "fontSize": 9},
                "horizontalAlignment": "LEFT",
                "verticalAlignment": "MIDDLE",
                "padding": {"top": 14, "bottom": 4, "left": 16, "right": 16},
            }},
            "fields": "userEnteredFormat(textFormat,horizontalAlignment,verticalAlignment,padding)",
        }})
        # Big number — accent color for tile 5
        big_color = ACCENT if is_accent else value_color
        requests.append({"repeatCell": {
            "range": _r(dash_id, 4, 5, col, col + 2),
            "cell": {"userEnteredFormat": {
                "textFormat": {"fontFamily": FONT, "foregroundColor": big_color, "bold": True, "fontSize": 30},
                "horizontalAlignment": "LEFT",
                "verticalAlignment": "MIDDLE",
                "padding": {"top": 0, "bottom": 0, "left": 16, "right": 16},
                "numberFormat": {"type": "NUMBER", "pattern": "#,##0"},
            }},
            "fields": "userEnteredFormat(textFormat,horizontalAlignment,verticalAlignment,padding,numberFormat)",
        }})
        # Sublabel
        requests.append({"repeatCell": {
            "range": _r(dash_id, 5, 6, col, col + 2),
            "cell": {"userEnteredFormat": {
                "textFormat": {"fontFamily": FONT, "foregroundColor": sub_color, "fontSize": 9},
                "horizontalAlignment": "LEFT",
                "verticalAlignment": "MIDDLE",
                "padding": {"top": 0, "bottom": 14, "left": 16, "right": 16},
            }},
            "fields": "userEnteredFormat(textFormat,horizontalAlignment,verticalAlignment,padding)",
        }})
        # Borders: tile separators (light gray vertical lines between tiles)
        if ti < last_tile_idx:
            requests.append({"updateBorders": {
                "range": _r(dash_id, 3, 6, col + 1, col + 2),
                "right": {"style": "SOLID", "width": 1, "color": {"red": 0.9, "green": 0.9, "blue": 0.91}},
            }})
        # Accent tile gets a 3px top accent border
        if is_accent:
            requests.append({"updateBorders": {
                "range": _r(dash_id, 3, 4, col, col + 2),
                "top": {"style": "SOLID_THICK", "color": ACCENT},
            }})

    # Tile row heights
    requests.append(_dim_request(dash_id, "ROWS", 3, 4, 30))
    requests.append(_dim_request(dash_id, "ROWS", 4, 5, 52))
    requests.append(_dim_request(dash_id, "ROWS", 5, 6, 28))
    requests.append(_dim_request(dash_id, "ROWS", 6, 7, 16))   # spacer row

    # Section header rows (0-based): row 9 (chart), 24 (monthly breakdown), 39 (campaigns), 60 (recent wins)
    for row_idx in (8, 23, 38, 59):
        requests.append({"mergeCells": {"range": _r(dash_id, row_idx, row_idx + 1, 0, N_COLS), "mergeType": "MERGE_ALL"}})
        requests.append({"repeatCell": {
            "range": _r(dash_id, row_idx, row_idx + 1, 0, N_COLS),
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 1, "green": 1, "blue": 1},
                "textFormat": {"fontFamily": FONT, "foregroundColor": {"red": 0.35, "green": 0.35, "blue": 0.35}, "bold": True, "fontSize": 10},
                "horizontalAlignment": "LEFT",
                "verticalAlignment": "BOTTOM",
                "padding": {"top": 8, "bottom": 6, "left": 0, "right": 0},
            }},
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,padding)",
        }})
        requests.append({"updateBorders": {
            "range": _r(dash_id, row_idx, row_idx + 1, 0, N_COLS),
            "bottom": {"style": "SOLID", "width": 1, "color": HEADER_BG},
        }})
        requests.append(_dim_request(dash_id, "ROWS", row_idx, row_idx + 1, 32))

    # Table headers: monthly breakdown (row 25, idx 24, 6 cols), campaigns (row 40, idx 39, 8 cols), recent wins (row 61, idx 60, 5 cols)
    for row_idx, last_col in [(24, 6), (39, 8), (60, 5)]:
        requests.append({"repeatCell": {
            "range": _r(dash_id, row_idx, row_idx + 1, 0, last_col),
            "cell": {"userEnteredFormat": {
                "backgroundColor": HEADER_BG,
                "textFormat": {"fontFamily": FONT, "foregroundColor": HEADER_FG, "bold": True, "fontSize": 9},
                "horizontalAlignment": "LEFT",
                "verticalAlignment": "MIDDLE",
                "padding": {"top": 6, "bottom": 6, "left": 12, "right": 12},
            }},
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,padding)",
        }})
        requests.append(_dim_request(dash_id, "ROWS", row_idx, row_idx + 1, 28))

    # Monthly breakdown table data formatting (rows 26-37, idx 25-36, cols B-F numeric)
    requests.append({
        "repeatCell": {
            "range": _r(dash_id, 25, 37, 1, 6),
            "cell": {"userEnteredFormat": {
                "textFormat": {"fontFamily": FONT, "fontSize": 10},
                "horizontalAlignment": "CENTER",
                "padding": {"top": 6, "bottom": 6, "left": 8, "right": 8},
            }},
            "fields": "userEnteredFormat(textFormat,horizontalAlignment,padding)",
        }
    })
    # First column (month) left-aligned with subtle weight
    requests.append({
        "repeatCell": {
            "range": _r(dash_id, 25, 37, 0, 1),
            "cell": {"userEnteredFormat": {
                "textFormat": {"fontFamily": FONT, "fontSize": 10, "bold": True, "foregroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2}},
                "horizontalAlignment": "LEFT",
                "padding": {"top": 6, "bottom": 6, "left": 12, "right": 8},
            }},
            "fields": "userEnteredFormat(textFormat,horizontalAlignment,padding)",
        }
    })
    # Highlight the current-month row (row 37, idx 36) — accent left border
    requests.append({"updateBorders": {
        "range": _r(dash_id, 36, 37, 0, 1),
        "left": {"style": "SOLID_THICK", "color": ACCENT},
    }})

    # Campaigns table — number formatting (B-G), date format (H)
    requests.append({
        "repeatCell": {
            "range": _r(dash_id, 40, 59, 1, 7),
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}}},
            "fields": "userEnteredFormat.numberFormat",
        }
    })
    requests.append({
        "repeatCell": {
            "range": _r(dash_id, 40, 59, 7, 8),
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "yyyy-mm-dd"}}},
            "fields": "userEnteredFormat.numberFormat",
        }
    })
    # Recent wins date col
    requests.append({
        "repeatCell": {
            "range": _r(dash_id, 61, 110, 0, 1),
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "yyyy-mm-dd"}}},
            "fields": "userEnteredFormat.numberFormat",
        }
    })
    # Recent wins DR col (idx 3)
    requests.append({
        "repeatCell": {
            "range": _r(dash_id, 61, 110, 3, 4),
            "cell": {"userEnteredFormat": {
                "numberFormat": {"type": "NUMBER", "pattern": "0"},
                "horizontalAlignment": "CENTER",
                "textFormat": {"fontFamily": FONT, "bold": True},
            }},
            "fields": "userEnteredFormat(numberFormat,horizontalAlignment,textFormat)",
        }
    })

    # Column widths (A:L) — 12 cols of equal 145px width
    for idx in range(N_COLS):
        requests.append(_dim_request(dash_id, "COLUMNS", idx, idx + 1, 145))

    # Hide gridlines, make Dashboard the first tab
    requests.append({"updateSheetProperties": {
        "properties": {"sheetId": dash_id, "gridProperties": {"hideGridlines": True}, "index": 0},
        "fields": "gridProperties.hideGridlines,index",
    }})

    # Three side-by-side charts: Emails sent | Replied | Links built
    # _Monthly columns: A=month, B=links_placed, C=emails_sent, D=replied
    def _chart_spec(series_col_idx: int, color: dict, anchor_col: int, width_cols: int, title_text: str) -> dict:
        return {
            "addChart": {
                "chart": {
                    "spec": {
                        "title": title_text,
                        "titleTextFormat": {"fontFamily": FONT, "fontSize": 10, "bold": True, "foregroundColor": {"red": 0.35, "green": 0.35, "blue": 0.35}},
                        "basicChart": {
                            "chartType": "COLUMN",
                            "legendPosition": "NO_LEGEND",
                            "axis": [
                                {"position": "BOTTOM_AXIS", "title": "",
                                 "format": {"fontFamily": FONT, "fontSize": 9, "foregroundColor": {"red": 0.4, "green": 0.4, "blue": 0.4}}},
                                {"position": "LEFT_AXIS", "title": "",
                                 "format": {"fontFamily": FONT, "fontSize": 9, "foregroundColor": {"red": 0.4, "green": 0.4, "blue": 0.4}}},
                            ],
                            "domains": [{
                                "domain": {"sourceRange": {"sources": [{
                                    "sheetId": monthly_tab_id,
                                    "startRowIndex": 1, "endRowIndex": 13,
                                    "startColumnIndex": 0, "endColumnIndex": 1,
                                }]}},
                            }],
                            "series": [{
                                "series": {"sourceRange": {"sources": [{
                                    "sheetId": monthly_tab_id,
                                    "startRowIndex": 1, "endRowIndex": 13,
                                    "startColumnIndex": series_col_idx, "endColumnIndex": series_col_idx + 1,
                                }]}},
                                "targetAxis": "LEFT_AXIS",
                                "color": color,
                            }],
                            "headerCount": 0,
                        },
                        "fontName": FONT,
                        "backgroundColor": {"red": 1, "green": 1, "blue": 1},
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {"sheetId": dash_id, "rowIndex": 10, "columnIndex": anchor_col},
                            "widthPixels": width_cols * 145,
                            "heightPixels": 240,
                            "offsetXPixels": 0,
                            "offsetYPixels": 0,
                        }
                    },
                }
            }
        }

    # Three charts side-by-side at 4 cols each across the 12-col canvas:
    # Emails sent → A:D  | Replied → E:H  | Links built → I:L (accent color)
    NEUTRAL_DARK = {"red": 0.2, "green": 0.2, "blue": 0.22}
    NEUTRAL_MID = {"red": 0.5, "green": 0.5, "blue": 0.52}
    requests.append(_chart_spec(series_col_idx=2, color=NEUTRAL_DARK, anchor_col=0, width_cols=4, title_text="People contacted"))
    requests.append(_chart_spec(series_col_idx=3, color=NEUTRAL_MID, anchor_col=4, width_cols=4, title_text="Replied"))
    requests.append(_chart_spec(series_col_idx=1, color=ACCENT, anchor_col=8, width_cols=4, title_text="Links built"))

    _sheets_service().spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": requests}).execute()


def _r(sheet_id: int, r0: int, r1: int, c0: int, c1: int) -> dict:
    return {"sheetId": sheet_id, "startRowIndex": r0, "endRowIndex": r1, "startColumnIndex": c0, "endColumnIndex": c1}


def _dim_request(sheet_id: int, dim: str, i0: int, i1: int, px: int) -> dict:
    return {
        "updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": dim, "startIndex": i0, "endIndex": i1},
            "properties": {"pixelSize": px},
            "fields": "pixelSize",
        }
    }


def refresh(sheet_id: str) -> None:
    """Cheap refresh: just recompute the monthly aggregation table."""
    _refresh_monthly(sheet_id)


def main() -> int:
    sid = ensure_master_sheet()
    arg = sys.argv[1] if len(sys.argv) > 1 else "build"
    if arg == "refresh":
        refresh(sid)
        print(f"refreshed monthly aggregation")
    else:
        build_dashboard(sid)
        print(f"dashboard built: https://docs.google.com/spreadsheets/d/{sid}/edit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
