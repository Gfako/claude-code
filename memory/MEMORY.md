# Project Memory

## PageCopy Tool
When the user asks to "copy a page" or "clone a page" with a URL, run the pagecopy script:
```bash
/Users/george.fakorellis/Desktop/SEO\ Custom\ Projects/page-editor-tools/pagecopy <URL> [port]
```
- Located at: `/Users/george.fakorellis/Desktop/SEO Custom Projects/page-editor-tools/`
- Two files: `pagecopy` (bash script) and `editor.js` (inline editing tools)
- Downloads HTML, adds `<base href>` for assets, injects editor tools, starts local server, opens browser
- Page gets two buttons: **Edit Text** (Alt+E) for inline text editing, **Inspect** (Alt+I) to copy element selectors to clipboard
- Default port: 8000. User can specify a different port.
- The cloned page folder is created in the current working directory as `pagecopy-<slug>/`

## Synthesia Clone
- Existing clone at: `/Users/george.fakorellis/Desktop/SEO Custom Projects/synthesia-clone/`
- Backup saved at: `/Users/george.fakorellis/Desktop/SEO Custom Projects/synthesia-video-translator/`

## SaaS Video Outreach - YouTube Video Pull (pending)
- [Pending work details](project_youtube_video_pull.md) — 208 channels ready for video pull + 311 need ID resolution. Resume when YouTube API quota resets.

## SaaS Video Outreach - Process & Skill
- Claude skill at: `~/.claude/projects/-Users-george-fakorellis-Desktop-SEO-Custom-Projects/commands/saas-outreach.md`
- Status file at: `/Users/george.fakorellis/Desktop/SEO Custom Projects/saas-video-outreach/OUTREACH_STATUS.md`
- Use `/saas-outreach` to invoke the skill for context on the full pipeline
- AirOps grid for Hunter enrichment: Grid ID 60558, Table ID 78167
- [Process preferences](feedback_outreach_process.md) — scraping before API, AirOps MCP, customer dedup, GIF URLs

## Guest Post Workflow (autonomous — use /guest-post)
- Single skill: `/guest-post <notion-url-or-id>` runs end-to-end (brief → draft → humanize → score → pricing verify → keyword check → section balance → links → Doc → Notion update)
- Skill file: `/Users/george.fakorellis/Desktop/SEO Custom Projects/.claude/skills/guest-post/SKILL.md`
- Runbook: `/Users/george.fakorellis/Desktop/SEO Custom Projects/guest-posts/WORKFLOW.md`
- Helper scripts: `guest-posts/scripts/{section_balance,keyword_check,score_ai,verify_pricing,doc_roundtrip}.py`
- Articles tracked in Notion DB "Synthesia Guest Posts" (collection `373c16d2-2bf1-81ee-a093-000bd006743e`)
- [Process rule](feedback_guest_post_workflow.md) — invoke /guest-post, don't break into separate skill calls; resumes from latest completed step if folder exists

## Content Brief Skill
- Use `/content-brief` to generate a full SEO content brief
- Automates: keyword research, SERP analysis, competitor content scraping, off-page/backlink analysis, AEO optimisation, internal linking, and recommendations
- Uses Ahrefs MCP, AirOps MCP (AEO), Firecrawl MCP, and GSC API (service account)
- Output saved to `content-briefs/content-brief-<slug>.md`
- Default brand: synthesia.io
- [GSC access details](reference_gsc_access.md) — service account at `.credentials/gsc-service-account.json`
- [Brief format rules](feedback_brief_format.md) — bullet lists, no tables, opinionated tone
- [GSC metrics rules](feedback_gsc_metrics.md) — no page-level avg CTR/position; show per-keyword metrics instead
- [AirOps scrape grid](reference_airops_scrape_grid.md) — Grid ID 61652 for Firecrawl scraping via AirOps workflow (replaces direct Firecrawl MCP)
- [Always use AirOps grid for scraping](feedback_airops_scrape_grid.md) — AirOps grid is the default for competitor scraping, never use Firecrawl MCP unless explicitly told

## Content Brief Simplified Skill
- Use `/content-brief-simplified` for a concise, skimmable brief (same data, shorter output)
- Same data pipeline as `/content-brief` — keyword universe, AEO, off-page, GSC, scraping
- Output is TL;DR-first: pain points → why it matters → recommended changes → content direction
- Designed for a writer to read in under 1 minute and start writing

## Edit Review Skill
- Use `/edit-review` to review drafted content against a content brief + Synthesia blog content guidelines
- Checks: brief alignment, expertise/information gain, voice/humanization, structure/clarity, AEO readiness, embedded content
- Based on Synthesia Blog Content Guidelines (Notion): editing checklist, 3-pass system, AEO tips, content type rules
- Output saved to `content-reviews/edit-review-<slug>.md`
- Provides publish-readiness score (X/60) and top 3 priority actions
- Interactive: writer can ask for elaboration or rewrites after review
- [Always ask for brief](feedback_always_ask_for_brief.md) — never skip the brief question, even if no local match found

## Google Drive + Sheets access
- [Gdrive + Sheets API reference](reference_gdrive_sheets.md) — OAuth token at `.credentials/gdrive-token.pickle` has both `drive.file` and `spreadsheets` scopes; re-auth script at `.credentials/reauth_gdrive_sheets.py`

## Weekly SEO Report Skill
- Use `/weekly-seo-report` to generate the weekly SEO meeting report and post to Notion
- Pulls data from Omni MCP: cohort LTV, clicks, contacts, MQLs, HI MQLs, AI search referral, self-reported lead source
- Posts as a new toggle dropdown on Notion page `214c16d22bf1806ea205fc82085149a8`
- Omni model ID: `6a5202c7-3bf0-4daa-8a48-3aaa6cca1eea`
- Key Omni topics: `d_marketing__seo_page_performance`, `d_marketing__seo_aggregated_performance`, `Contact & Account Intent`, `fct_google_analytics_4_daily_web_report`, `rep_marketing__return_on_organic`
- Roadmap section always links to `https://www.notion.so/synthesia/21fc16d22bf18067b241f4d9fa02c309`
- Requires Omni MCP connection — run `! /mcp` if disconnected
- [Always include current month cohort](feedback_weekly_report_current_month.md) — cohort summary + chart must include the current calendar month even when in formation, never stop at previous complete month
- [Target page is the Reports sub-page](feedback_weekly_report_target_page.md) — toggle posts to Reports (18th May Onward) sub-page (`364c16d22bf1805886affcafbf9fe64b`), not the parent; cohort WoW deltas computed vs that sub-page's most recent toggle, not Omni's "1 week ago" snapshot

## Backlink Monitor Skill
- Use `/backlink-monitor` to run the weekly backlink check
- Monitors: Synthesia lost backlinks + HeyGen/Veed.io new backlinks via Ahrefs MCP
- Config at: `backlink-monitor/config.json` — competitors, DR threshold, page URLs
- Snapshots saved to `backlink-monitor/snapshots/`
- User will provide specific competitor page URLs later to narrow monitoring scope

## Link Discover System
- [Never overwrite manual sheet data](feedback_never_overwrite_manual_data.md) — automated stages must skip cells with existing values; match by source_page URL not domain
- [Sheet tab styling must reset data rows](feedback_sheet_tab_styling_reset.md) — apply_campaign_tab_styling must include explicit row 1+ reset to white/non-bold or new tabs render with dark header bleeding into data rows
- [Always use OVERWRITE on values.append](feedback_sheets_append_overwrite.md) — INSERT_ROWS silently shifts formula refs in _Data, breaking dashboard KPIs
- [Always populate the Language column](feedback_keep_language_column.md) — use the source's Language field; filter non-en by `language != "en"`, never ccTLD heuristics
- [Never auto-filter by language](feedback_no_auto_language_filter.md) — populate the language column but keep all rows; user filters manually in the sheet
- Use `/link-discover` for high-volume page discovery + filter + Hunter enrich + Reply.io sync
- [System reference](reference_link_discover.md) — single master Google Sheet (one tab per campaign), 17-column schema, native checkbox sync, Reply.io v3 `/v3/sequences/{id}/contacts/state` for per-person status
- Scripts: `sheets_helper.py` `discover.py` `filter.py` `enrich.py` `sync_replyio.py` under `link-outreach/scripts/`
- Master sheet ID: `1kR_s9hWca53jMMjNeVtIVrqmVHYSk3fLq0mSBZheZSc` (in `link-outreach/config.json` under `link_discover.master_sheet_id`)
- Phase 1 ships only `scrape:broken-outbounds`; other sources (google-footprints, reddit-hn, ahrefs:*) to be added on request

## Link Building Outreach System
- Use `/link-outreach` to run automated link building campaigns (niche edits)
- [System reference](reference_link_outreach.md) — full pipeline, tools, config, Reply.io API, two outreach tracks
- [Campaign rules](feedback_link_outreach_rules.md) — search by use case not tool name, no URL filtering, competitor mentions are opportunities, two outreach tracks
- Project at: `link-outreach/` — config, master tracker, campaign logs, templates, scripts
- Python script: `link-outreach/scripts/scrape_and_analyze.py` — bulk Firecrawl scraping + heuristic fit analysis
- AirOps enrichment grid: ID 64148, Table ID 82974 (current, in config.json — older 61680/79677 is legacy)
- Reply.io API key at: `.credentials/reply-io-api-key.txt`
- Firecrawl API key: stored at `.credentials/firecrawl-api-key.txt` — all link-outreach scripts read from this file at runtime (not hardcoded). Rotate by editing that single file.
- Reply.io sequence IDs stored in `link-outreach/config.json` (set on first run per campaign type)
- [AirOps grid push rule](feedback_airops_grid_push.md) — never push large datasets via MCP tool calls, use Python scripts to avoid truncation
- [Reply.io name split rule](feedback_replyio_name_split.md) — always split full name into firstName + lastName before pushing; never send full name as firstName

## Content Brief Output Rules
- [No internal references in briefs](feedback_brief_no_internal_refs.md) — never mention team members, internal reviews, or conversations in brief content or comments

## Deliverable Style Rules
- [No emojis in deliverables](feedback_no_emojis_in_deliverables.md) — plain text only in sheets, Notion pages, briefs, audit reports, anything user-facing

## Blog Content Guidelines
- [Synthesia Blog Guidelines reference](reference_blog_guidelines.md) — Notion source + local copy at `blog-guidelines/synthesia-blog-guidelines.md`
- `/blog-guidelines` skill fetches latest from Notion; `/edit-review` reads local copy at Step 0

## Light Content Refresh
- [System reference](reference_content_refresh.md) — two skills, Notion DB, Slack channels, cron, scoring
- `/content-refresh <url>` — on-demand single-URL; posts findings to Notion + Slack (no interactive accept/reject)
- `/content-refresh-daily` — autonomous daily crawl (15 URLs), posts to Notion + #light-content-refreshes
- [Findings rules](feedback_content_refresh_findings.md) — strict "confirmed" threshold + every finding needs a short title
