---
name: feedback-replyio-name-split
description: Names must always be stored as separate first_name + last_name columns in the master sheet AND pushed as separate firstName + lastName fields to Reply.io. Never store or send a combined full-name.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e7ca726f-d584-49eb-922e-49f9724cfa48
---

In the Link Building Master Tracker, contact names are split across two columns: `first_name` (column O) and `last_name` (column P). When any enrichment script writes contact data (e.g., `enrich.py apply-contacts`), it must populate these two columns separately — never combine into a single column. When pushing to Reply.io, send `firstName` and `lastName` separately by reading the sheet columns directly.

**Why:** Reply.io email templates use `{{FirstName}}` in greetings ("Hi Justin,"). If the full name "Justin Maury" is in a single column and gets shoved into `firstName`, the email reads "Hi Justin Maury," which looks robotic and breaks personalization. Splitting in the sheet also makes filtering/sorting by surname possible.

**How to apply:**
- Schema: `link-outreach/scripts/sheets_helper.py` COLUMNS includes both `first_name` and `last_name` (replacing the old `primary_contact_name`).
- Enrichment: `enrich.py:_extract_contact_fields()` returns `first_name` and `last_name` separately from the AirOps payload. If AirOps returns only a combined name, split on first whitespace.
- Push: `push_replyio.py` reads `first_name` and `last_name` directly from the sheet; a fallback splits inline only if `first_name` accidentally contains a full name and `last_name` is empty.
- Verify after each enrichment/push by sampling rows in the sheet and confirming both columns are populated. See [[reference-link-outreach]].
