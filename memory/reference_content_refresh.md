---
name: Light Content Refresh system
description: Two skills (/content-refresh single-URL interactive, /content-refresh-daily autonomous cron) that flag pages with outdated pricing/stats/links/AI-model/feature mentions. Writes findings to Notion DB + Slack.
type: reference
originSessionId: 17d50050-daa6-4718-af24-2dc1a65b0018
---
# Light Content Refresh system

Two-skill system for catching outdated content on the Synthesia blog + alternatives pages.

## Skills
- `/content-refresh <url>` — interactive single-URL review. Walks user through accept/reject/edit for each finding. Outputs updated markdown locally. Does NOT push anywhere.
- `/content-refresh-daily` — autonomous crawl (15 URLs/day). Writes findings to Notion + posts a summary to Slack. Fires from cron, no user interaction.

## Project location
`/Users/george.fakorellis/Desktop/SEO Custom Projects/content-refresh/`

Layout:
- `config.json` — sitemap URL, competitors + pricing URLs, AI model terms, scoring weights, severity thresholds, Notion/Slack IDs, AirOps grid ID
- `scripts/sitemap_fetch.py` — fetch Synthesia sitemap, filter to `/post/*` + `/alternatives/*`
- `scripts/extract_claims.py` — regex-extract pricing (near brand), stats, external links, AI-model mentions
- `scripts/crawl_state.py` — pick next URLs, content-hash state, update after each URL
- `scripts/score.py` — weighted score 0-100 → severity tier
- `scripts/format_notion_page.py` — build DB row properties + markdown body
- `scripts/format_slack_summary.py` — build the daily Slack summary text
- `state/crawl_state.json` — per-URL last_checked, content_hash, score
- `logs/run-YYYY-MM-DD.json` — per-run full log
- `drafts/<slug>.{original,updated}.{md,html}` — single-URL skill outputs

## Notion DB
"Light Content Updates Suggestions" — created at workspace root (not nested).
- DB ID: `a9aac15246ef4b6ea8383033f5a82f8c`
- Data source ID: `2ad51d70-d7de-4085-b031-d6089beaa5b4`
- URL: `https://www.notion.so/a9aac15246ef4b6ea8383033f5a82f8c`
- Schema: Title, URL, Outdatedness score (0-100), Severity (Clean/Low/Medium/High/Critical), Findings count, Types (pricing/stat/link/ai-news/feature), Status (New/Reviewing/Updated/Ignored), Last checked, Last change detected, Section (blog/alternatives), **Findings page** (URL — click to open the row's detailed findings view directly)
- Each row's page body = formatted findings view with quotes + suggestions. `Findings page` column holds the same URL as the row's own page (set via a follow-up update-page call after create).

## Slack channels
- `#product-changelog` (C029EFJ65NF, public) — source for feature verification (90-day lookback)
- `#light-content-refreshes` (C0AUZFBGR29, private) — daily run summary posts here

## Scoring
Weights: pricing 15, link 12, feature 10, stat 7, ai-news 5. Severity multiplier: confirmed 1.0, likely 0.6, unconfirmed 0.0.
Tiers: 0=Clean, 1-15=Low, 16-35=Medium, 36-60=High, 61+=Critical. Score cap 100.

## Cron
CronCreate job `718a2033` at 07:07 daily running `/content-refresh-daily`. Auto-expires after 7 days — re-register weekly, or replace with launchd for true durability.
