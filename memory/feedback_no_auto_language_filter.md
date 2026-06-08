---
name: feedback-no-auto-language-filter
description: "Never auto-filter rows out of a campaign tab based on language (or any other criterion) without explicit instruction. Populate the `language` column and let the user filter manually in the sheet."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e7ca726f-d584-49eb-922e-49f9724cfa48
---

When ingesting data into any campaign tab in the Link Building Master Tracker, do NOT drop rows based on language by default. Populate the `language` column with whatever the source reports, and stop there. The user filters manually in the sheet.

**Why:** The `language` column was added to the schema specifically so the user could filter non-English rows themselves at the moment they want to. Auto-dropping non-en rows loses data the user may want to review for local-market outreach (e.g., German, Spanish opportunities). The user pushed back when I auto-filtered metaphysic-defunct from 1,737 → 932 without being asked.

**How to apply:**
- For any new campaign ingest (Ahrefs exports, scrapes, AEO citations), keep all rows regardless of language.
- Map the source's language field to the `language` column. Leave blank only if the source has no language data.
- Only filter language if the user explicitly asks (e.g., "remove non-en pages" — past examples: aeo-listicle-gap, original guest-posts-automation).
- See [[feedback-keep-language-column]] — same principle: language is stored for filtering, not auto-filtered.
