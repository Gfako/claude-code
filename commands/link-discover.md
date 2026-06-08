---
description: Modular link-building discovery pipeline — discover pages by topic/niche, filter by DR, enrich with Hunter contacts via AirOps, and sync Reply.io status. Everything writes to one master Google Sheet, one tab per campaign, with native checkboxes for added_to_sequence and email_sent.
---

# /link-discover

You are running the link-building discovery pipeline. Every campaign writes into the **same master Google Sheet** ("Link Building Master Tracker"), with one tab per campaign slug. The sheet ID is stored in `link-outreach/config.json` under `link_discover.master_sheet_id` (created on first use).

**Tab schema** (per row = one discovered page):
`source_technique, source_page, source_page_title, domain, dr, traffic, broken_url, anchor_text, emails, primary_contact_name, primary_contact_title, added_to_sequence, email_sent, reply_status, reply_sequence, last_activity_at, discovered_at, link_placed_at`

Both `added_to_sequence` and `email_sent` are native Sheets checkboxes, synced one-way from Reply.io. `link_placed_at` is a date column — the writer fills it the day a link goes live. The Dashboard charts wins per month from this column.

**Dashboard tab** (first tab) shows live KPIs (total prospects, contacted, replied, links built, built this month), a 12-month bar chart, a per-campaign table, and a recent-wins list. Hidden `_Data` and `_Monthly` tabs power the aggregations.

## Project location
`/Users/george.fakorellis/Desktop/SEO Custom Projects/link-outreach/`

Scripts: `scripts/sheets_helper.py`, `scripts/discover.py`, `scripts/filter.py`, `scripts/enrich.py`, `scripts/sync_replyio.py`

## Subcommands

Parse the user's args to pick a subcommand. If none given, ask which they want and what campaign slug to use.

### `find` — discover pages

```bash
python3 link-outreach/scripts/discover.py \
    --source <source> --campaign <slug> --topic "<query>" [--limit N]
```

Available sources:
- `scrape:broken-outbounds` — Firecrawl search by topic → scrape each result → HEAD-check every outbound link → write a row per broken link. Discovery applies an article-URL filter (drops platform homepages, listing pages, etc.). Default `--limit 20`.
- `ahrefs:broken-backlinks` / `ahrefs:all-backlinks` (defunct competitor) — call `mcp__ahrefs__site-explorer-all-backlinks` (or `-broken-backlinks`) with `select=url_from,title,anchor,url_to,domain_rating_source,traffic_domain,root_name_source,first_seen_link,is_dofollow,languages,page_type_source` and `aggregation=1_per_domain`. Save JSON to `link-outreach/campaigns/ahrefs-broken/<slug>.json`. Then run:
  ```bash
  python3 link-outreach/scripts/apply_ahrefs_backlinks.py <campaign> --file <path-to-json> --technique ahrefs:backlinks-defunct
  ```
  This applies all filters automatically — exclude_domains, platform hosts (notion.site, webflow.io, etc.), non-English, **and the article-only classifier** (uses Ahrefs `page_type_source` as primary signal, URL patterns as fallback).

Future sources to add: `scrape:google-footprints`, `scrape:reddit-hn`, `ahrefs:content-explorer`. Tell the user if they ask for one not yet implemented.

**Article filter** (`filter_articles.py`): every source applies this — articles are pages with `page_type_source` starting `/Article/`, or URL paths containing markers like `/blog/`, `/post/`, `/news/`, `/article/`, `/guide/`, etc. Excludes company-profile pages, vendor listings, marketplace/directory entries, core pages (about/pricing/contact), API docs, tweets, search/category pages. Re-filter an existing tab anytime with:
```bash
python3 link-outreach/scripts/filter_articles.py <campaign> --ahrefs-json <optional-path> [--dry-run]
```

After the run, share the printed sheet URL with the user and summarise: pages scraped, broken links found, rows appended.

### `filter` — DR/traffic enrichment (uses Ahrefs MCP)

Three steps:

1. **List domains needing DR:**
   ```bash
   python3 link-outreach/scripts/filter.py list-domains <campaign>
   ```
   Parse the JSON output to get `domains_needing_dr`.

2. **Batch-query Ahrefs** for those domains using the MCP tool, in chunks of ≤100:
   ```
   mcp__ahrefs__batch-analysis with the list of domains
   ```
   Save the response to a temp file like `/tmp/ahrefs_<campaign>.json`. If the response includes a `render_with`, also call the render tool (per ahrefs MCP rules), but the file is what we feed back into the script.

3. **Apply the results:**
   ```bash
   python3 link-outreach/scripts/filter.py apply-results <campaign> --file /tmp/ahrefs_<campaign>.json
   ```

Then optionally show the qualification stats:
```bash
python3 link-outreach/scripts/filter.py mark-qualified <campaign>
```

Report to the user: # of rows hydrated, # qualified (DR within window), # below threshold.

### `enrich` — Hunter contact enrichment (uses AirOps MCP)

Three steps:

1. **Prepare the push** — get unique domains to enrich:
   ```bash
   python3 link-outreach/scripts/enrich.py prepare-push <campaign>
   ```
   The output JSON has `airops_grid_id`, `airops_table_id`, and `to_push` (list of `{domain, source_pages}`).

2. **Push to AirOps** via the MCP write_grid tool, then poll until rows complete, then read back. Use the grid + table IDs from the prepare-push output (currently 64148 / 82974). Use the existing `write_grid` → wait → `read_grid` pattern from `saas-outreach`. Save the read_grid output to `/tmp/airops_<campaign>.json`.

3. **Apply the contacts** back to the sheet:
   ```bash
   python3 link-outreach/scripts/enrich.py apply-contacts <campaign> --file /tmp/airops_<campaign>.json
   ```

Report: # domains pushed, # with contacts returned, # rows updated.

### `dashboard` — rebuild / refresh the executive Dashboard

```bash
python3 link-outreach/scripts/setup_dashboard.py           # full rebuild (layout + chart + data)
python3 link-outreach/scripts/setup_dashboard.py refresh   # refresh _Monthly only (fast)
```

Run `build` whenever you want to redo the layout (rare) or when the tab order is wrong. Run `refresh` after any campaign updates `link_placed_at` so the monthly chart picks up the new wins. KPI tiles and per-campaign table are live formulas — they always reflect current state without a rebuild.

### `sync-status` — Reply.io checkbox sync

```bash
python3 link-outreach/scripts/sync_replyio.py <campaign>
```

This is a self-contained Python script (no MCP needed). It pulls all contacts from each sequence in `config.reply_io.sequences` via `/v3/sequences/{id}/contacts/state` with extended state, then updates each row's two checkboxes plus `reply_status`, `reply_sequence`, `last_activity_at`.

Run this whenever you want the sheet to reflect current Reply.io state. Safe to run anytime; one-way (Reply.io → Sheet).

Report: rows updated, # added, # sent.

## Typical campaign flow

```bash
# 1. Discover
python3 link-outreach/scripts/discover.py --source scrape:broken-outbounds \
    --campaign video-translation --topic "video translation tools" --limit 30

# 2. Filter (via Ahrefs MCP — see filter section above)

# 3. Enrich (via AirOps MCP — see enrich section above)

# 4. Sync once Reply.io is running
python3 link-outreach/scripts/sync_replyio.py video-translation
```

## Behavior rules

- **Campaign slug** is the tab name. Use kebab-case. If user gives a longer name, slugify it (lowercase, hyphens, no punctuation).
- **One tab per campaign**, all techniques mixed in the same tab (distinguish by `source_technique` column). Don't create separate tabs per technique.
- **Dedup is automatic** — `append_rows` skips any `source_page` URL already present in that tab.
- **Never push large datasets through MCP tool calls one-row-at-a-time** — always have the user's Python scripts read/write the bulk and just use MCP for batch read/write operations (per existing AirOps push rule).
- After every stage, print the sheet URL so the user can inspect.
- If a step fails, surface the error and stop — don't try to recover by guessing. The pipeline is designed so each stage can be re-run independently.

## Config

`link-outreach/config.json` keys we use:
- `link_discover.master_sheet_id` — master sheet (auto-set on first run)
- `link_discover.dr_min` / `link_discover.dr_max` — DR window for `mark-qualified` and `enrich.prepare-push`
- `link_discover.outbound_check_concurrency` / `outbound_check_timeout_sec` — broken-link checker tuning
- `airops.enrichment_grid_id` / `airops.enrichment_table_id` — Hunter grid (currently 64148 / 82974)
- `reply_io.sequences` — name → sequence ID map, used by sync_replyio.py
- `exclude_domains` — never flag these as targets (competitors, social, etc.)
