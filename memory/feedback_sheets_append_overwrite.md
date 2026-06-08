---
name: feedback-sheets-append-overwrite
description: "When appending rows to a campaign tab via Sheets API values.append(), always use insertDataOption=\"OVERWRITE\", never \"INSERT_ROWS\" — INSERT_ROWS shifts formula references in other tabs (e.g., _Data dashboard KPIs)."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e7ca726f-d584-49eb-922e-49f9724cfa48
---

In `link-outreach/scripts/sheets_helper.py:append_rows()`, the values.append() call must use `insertDataOption="OVERWRITE"`. Never use `INSERT_ROWS`. The same applies to any new script that appends rows to a campaign tab in the Link Building Master Tracker.

**Why:** `INSERT_ROWS` causes Google Sheets to physically insert new rows, which shifts row references in formulas living in OTHER tabs. The dashboard `_Data` tab has formulas like `=COUNTA('campaign-name'!F2:F)` that count campaign rows. When the campaign tab grows via INSERT_ROWS, Sheets silently shifts the `F2:F` reference to `F1148:F` (or wherever the new data lands), making the dashboard show zero rows even though the campaign tab has thousands. `OVERWRITE` writes to the next empty rows without shifting any references.

**How to apply:**
- Existing `append_rows()` in `sheets_helper.py:581` uses OVERWRITE — keep it that way.
- If you ever see dashboard KPIs showing 0 for a campaign that has data, check the _Data tab formulas — if they reference a row far below row 2, run a repair: rewrite the formulas to start at row 2.
- Repair pattern: read campaigns from `_Data!A2:A`, regenerate each row with formulas anchored at `!F2:F` etc., and write back via `values.update()`. See [[reference-link-discover]].
