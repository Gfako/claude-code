---
name: link-discover-system
description: "Modular link-building discovery pipeline (/link-discover) — discovers pages via Firecrawl scraping or Ahrefs sources, filters by DR, enriches with Hunter via AirOps, and syncs Reply.io status into a single master Google Sheet with native checkboxes per row."
metadata: 
  node_type: memory
  type: reference
  originSessionId: e7ca726f-d584-49eb-922e-49f9724cfa48
---

## /link-discover system

Sibling to [[reference_link_outreach]] but built for high-volume *discovery* — bring in many candidate pages from multiple sources, filter, enrich, push to Reply.io, sync status. Everything writes into **one master Google Sheet** with **one tab per campaign**.

### Slash command and scripts
- Skill: `/link-discover` at `~/.claude/projects/-Users-george-fakorellis-Desktop-SEO-Custom-Projects/commands/link-discover.md`
- Scripts under `link-outreach/scripts/`:
  - `sheets_helper.py` — master sheet creation, tab + checkbox formatting, append/dedup
  - `discover.py` — discovery sources (Phase 1: `scrape:broken-outbounds`)
  - `filter.py` — Ahrefs DR/traffic hydration (list-domains / apply-results / mark-qualified)
  - `enrich.py` — AirOps Hunter push prep + contact backfill (prepare-push / apply-contacts)
  - `sync_replyio.py` — Reply.io status sync, updates two checkboxes + status columns

### Master sheet
- Title: "Link Building Master Tracker"
- ID stored in `link-outreach/config.json` under `link_discover.master_sheet_id`
- `_Summary` tab + one tab per campaign slug
- Created automatically on first `/link-discover find` run
- Auth via OAuth token at `.credentials/gdrive-token.pickle` (drive.file + spreadsheets scopes)

### Tab schema (17 columns)
`source_technique, source_page, source_page_title, domain, dr, traffic, broken_url, anchor_text, emails, primary_contact_name, primary_contact_title, added_to_sequence (checkbox), email_sent (checkbox), reply_status, reply_sequence, last_activity_at, discovered_at`

Both checkbox columns are native Sheets checkboxes (BOOLEAN data validation, applied only to appended rows to keep reads clean).

### Subcommands
- `find <source> <campaign> <topic> [--limit N]` — pure Python (Firecrawl)
- `filter <campaign>` — three-step: Python lists domains → Claude calls `mcp__ahrefs__batch-analysis` → Python applies results
- `enrich <campaign>` — three-step: Python preps push → Claude calls AirOps MCP `write_grid` / `read_grid` → Python applies contacts
- `sync-status <campaign>` — pure Python (Reply.io v3 `/v3/sequences/{id}/contacts/state` with `additionalColumns=CurrentStep,LastStepCompletedAt,Status`)

### Reply.io v3 endpoint (critical for sync)
`GET /v3/sequences/{id}/contacts/state?additionalColumns=CurrentStep,LastStepCompletedAt,Status&skip=N&take=200`
Auth: `Authorization: Bearer <api-key>` (Bearer or `x-api-key` both work)
Returns `items[]` with `email, currentStep.stepNumber, lastStepCompletedAt, status.{status,replied,delivered,bounced,opened,clicked}`. Pagination via `skip/take`, `hasMore` indicates more pages. v1 statistics endpoints (`/v1/people/{id}/statistics` etc.) do NOT exist — only v3 surface provides per-person extended state.

### Config keys (`link-outreach/config.json`)
- `link_discover.master_sheet_id` — auto-set on first run
- `link_discover.dr_min` / `dr_max` — DR window for enrich qualification (default 30 / 90)
- `link_discover.outbound_check_concurrency` / `outbound_check_timeout_sec` — broken-link checker
- `airops.enrichment_grid_id` / `enrichment_table_id` — 64148 / 82974 (Hunter)
- `reply_io.sequences` — sequence name → ID map, used by sync_replyio.py

### Article-only filter (always on)
`filter_articles.py` runs on every source. Classifier rules:
- Primary: Ahrefs `page_type_source` starting with `/Article/`, plus `/Video/Tutorial_or_Guide`, `/Audio/Podcast`. Drops `/Listing*`, `/Core_Page*`, `/User_Generated*`, `/Search*`.
- Fallback (no page_type): URL must contain a marker like `/blog/`, `/post/`, `/news/`, `/article/`, `/guide/`, `/tutorial/`, `/learn/`, `/insights/`, `/resources/`, OR have a `/20YY/` year segment, OR end with a 2+ hyphen slug of 12+ chars. Explicit NO patterns: `/company/`, `/companies/`, `/profile/`, `/directory/`, `/marketplace/`, `/reviews/product/`, `/tools/<slug>`, `/apps/<slug>`, `/sites/<slug>`, `/page/<num>`, `/tag/`, `/topic/`, `/reference/`, `/docs/`, `/about`, `/pricing`, `/careers`, `/jobs`, `/privacy`, `/security`, `/thread/`.
- Use `filter_articles.py <campaign> --ahrefs-json <path>` to retroactively clean an existing tab.

### Defunct-competitor backlinks workflow (one-off)
For a defunct competitor (e.g., rephrase.ai):
1. Claude calls `mcp__ahrefs__site-explorer-all-backlinks` with `select=...,page_type_source`, `aggregation=1_per_domain`, `history=live`, filter `is_dofollow=true AND domain_rating_source >= 30`
2. Save JSON to `link-outreach/campaigns/ahrefs-broken/<slug>.json`
3. `python3 apply_ahrefs_backlinks.py <campaign> --file <path>` — applies platform/lang/article filters
4. Continue with `enrich`, `sync-status`, etc.

Cost: ~5000 Ahrefs units per 250-row pull. Use `1_per_domain` aggregation to avoid duplicate-domain rows.

### Phase 1 vs future
Phase 1 ships `scrape:broken-outbounds` (article-filtered) and the Ahrefs defunct-backlinks loader above. Future sources to add when the user asks:
- `scrape:google-footprints` — Firecrawl search with operators like `inurl:resources "topic"`, `intitle:"write for us"`
- `scrape:reddit-hn` — pull URLs being shared in relevant subreddits / HN
- `ahrefs:content-explorer` — Ahrefs Content Explorer by keyword
- `ahrefs:broken-backlinks` — Ahrefs broken-backlinks of a competitor or dead URL
- `ahrefs:all-backlinks` — replication of a competitor's backlinks

All new sources write the same 17-column row shape, dedup by `source_page`, and reuse filter / enrich / sync untouched.

### Design rules
- One tab per campaign, all techniques mixed (distinguish by `source_technique`)
- Dedup by `source_page` URL (rstrip trailing slash) — handled inside `append_rows`
- Native Sheets checkboxes via BOOLEAN data validation applied per-batch (not whole-column — caused 1000 ghost rows in initial build)
- Reply.io sync is one-way: Reply.io → Sheet. Manual checkbox edits get overwritten on next sync.
- `email_sent` ticks when `status.delivered=true` OR `lastStepCompletedAt` is set OR `currentStep.stepNumber > 1` (any of these). `added_to_sequence` ticks when the contact appears in any configured sequence at all.
