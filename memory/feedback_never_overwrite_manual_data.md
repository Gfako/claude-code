---
name: never-overwrite-manual-data
description: Never overwrite manually-entered values in the link-discover master sheet or related artifacts. Automated stages must skip cells that already have a value.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e7ca726f-d584-49eb-922e-49f9724cfa48
---

Never overwrite manually-entered data in the link-discover master sheet (or any related artifact like Reply.io contact custom fields).

**Why:** The user actively edits rows by hand — adding new prospects, fixing domains, ticking checkboxes ahead of automation, adjusting titles. A 2026-05-21 incident: my `enrich.py` matched contacts by domain only, found two rows with `domain=subscribed.fyi` (one was the user's manual `aivideotoolspro.com/detail/synthesia` prospect with the wrong domain typed), and overwrote the manual row with Mary Cincoflores's contact data. Then `push_replyio.py` pushed Mary twice; the second push's customFields were silently accepted by Reply.io, polluting Mary's record with the aivideotoolspro `article_url`.

**How to apply:**

In every script that writes back to the sheet:
- `enrich.py apply-contacts` — skip rows where ANY of `emails`, `primary_contact_name`, `primary_contact_title` is non-empty. Don't just check `emails`.
- `push_replyio.py` — dedup candidates by email before iterating (don't push the same email twice in one run).
- `sync_replyio.py` — only update checkbox / status columns when Reply.io has fresh data. Never CLEAR a manually-set value (e.g., if a user ticks `email_sent` ahead of the API knowing about it, don't untick).
- `filter_articles.py` — when re-writing rows after a filter, preserve every existing column value verbatim. Don't normalize or rewrite anything.
- In general: when matching AirOps/Ahrefs results to sheet rows, match by `source_page` URL (unique) rather than domain (can collide), and if a row already has the field we'd write, leave it alone.

When in doubt, ASK the user before touching a cell that already has a value, rather than silently overwriting.
