---
name: feedback-keep-language-column
description: "The master sheet has a `language` column (between `domain` and `dr`) — when ingesting any Ahrefs export or scrape, always populate it. Filter non-English using the source's authoritative Language field, never URL/title heuristics."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e7ca726f-d584-49eb-922e-49f9724cfa48
---

The Link Building Master Tracker schema includes a `language` column (column J, index 9) on every campaign tab. Any script that ingests raw data into a campaign tab must populate this column from the source's authoritative Language field.

**Why:** When filtering non-English pages, heuristics on ccTLDs or title characters wrongly drop legitimate English sites on `.co`, `.io`, `.in`, etc. Ahrefs already classifies pages by language — use that directly. Storing it on the sheet lets the user filter visually later without re-fetching.

**How to apply:**
- When importing an Ahrefs backlinks export, map the export's `Language` column to the campaign row's `language` field.
- To drop non-English rows, filter rows where `language` is set AND != "en". Never use ccTLD heuristics as the primary filter (they're wrong for `.co`, `.io`, `.in`, etc.).
- For sources without a Language field (raw scrapes, SERP results), leave `language` empty rather than guessing — the user can fill it later.
- The column is in `link-outreach/scripts/sheets_helper.py:COLUMNS` and `DISPLAY_LABELS`. Never remove it.
