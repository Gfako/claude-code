---
name: feedback-sheet-tab-styling-reset
description: "When restyling a campaign tab in the Link Building Master Tracker, the apply_campaign_tab_styling function must explicitly reset data rows (1+) to a clean state — header repeatCell on row 0 does NOT clear stale formatting that leaked onto row 1 during tab creation."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e7ca726f-d584-49eb-922e-49f9724cfa48
---

Whenever a new campaign tab is added or restyled in `link-outreach/scripts/sheets_helper.py`, the styling function must include an explicit `repeatCell` that resets backgroundColor to white, bold to False, and foregroundColor to black for rows 1+ across all columns.

**Why:** Without this reset, rows 1+ on freshly created tabs keep the dark header background (#0F0F0F) and white text, making data invisible. User has flagged this multiple times as "bad formatting." The repeat-offender bug is that Sheets does not auto-clear cell formats when you only update row 0 — leftover formats on row 1+ stay and block the banded range from rendering.

**How to apply:** Any change to `_build_styling_requests` or `apply_campaign_tab_styling` must keep the "reset rows 1-5000 to white, non-bold" repeatCell request immediately after the header repeatCell. Verify after restyling by reading row 1 cells and confirming `backgroundColor == #ffffff` and `bold == False`. See [[reference-link-discover]] for sheet schema context.
