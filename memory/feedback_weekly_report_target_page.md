---
name: feedback-weekly-report-target-page
description: "Weekly SEO report toggle goes on the Reports (18th May Onward) sub-page, not the parent Weekly SEO Meeting page. Cohort WoW deltas must be computed vs that sub-page's most recent toggle."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c3026f34-6e50-4cd5-880b-cb7c31d91297
---

The weekly SEO report toggle must be posted to the "Reports (18th May Onward)" sub-page (id `364c16d22bf1805886affcafbf9fe64b`), NOT the parent Weekly SEO Meeting page (id `214c16d22bf1806ea205fc82085149a8`).

**Why:** All reports from 18th May 2026 onward live on the sub-page. The parent page's last date toggle (currently "11th May 2026") is leftover from before the split — anchoring to it puts the report in the wrong place AND uses the wrong baseline for cohort WoW deltas. In the 25th May 2026 run, anchoring to the parent caused (a) report posted on the wrong page (user had to manually move it) and (b) May 2026 cohort wrongly labelled "(new)" when in fact the 18th May report already had May at £97k, so the correct delta was +£106k.

**How to apply:** In the `/weekly-seo-report` skill workflow:
1. The target `page_id` for `update_content` is `364c16d22bf1805886affcafbf9fe64b` (Reports sub-page), not `214c16d22bf1806ea205fc82085149a8` (parent).
2. To compute cohort WoW deltas, fetch the sub-page and read the LATEST existing toggle's cohort values (e.g. the 18th May 2026 toggle for the 25th May run). Subtract those from the current 1A values. Do not rely solely on Omni's "1 week ago" snapshot — it doesn't necessarily match what was actually published in the previous report.
3. Only use "(new)" for a cohort month that was NOT present in the previous report's cohort list. If May 2026 was already in the 18th May toggle, it's "+Xk", not "(new)".

Related: [[reference_weekly_seo_report]] if/when written.
