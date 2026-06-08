# YouTube Outreach Project

## Pipeline Overview

This project discovers YouTube channels using auto-dubbing, enriches them with contact info and SEO metrics, reviews videos for dubbing, and prepares them for outreach via Synthesia.

## Architecture

```
pipeline.py  (CLI orchestrator — runs steps in order or individually)
    ↓
utils.py     (shared: config from .env, HTTP session, retry decorator, logging, domain cleaning)
db.py        (SQLite with context managers, column whitelists, migration)
    ↓
discover.py → enrich.py → ahrefs_enrich.py → lusha_enrich.py → review.py → dub.py → export.py
```

## Channel Status Workflow
```
discovered → enriched → reviewed → approved → dubbed → pitched → responded
```

## Pipeline Steps

### Step 1: Discovery
```bash
cd "/Users/george.fakorellis/Desktop/SEO Custom Projects/Youtube outreach"
python3 pipeline.py discover
```
Finds channels via YouTube API, filters by 5K-50K subscribers, checks 10 videos per channel (by date + by views) for auto-dubbing.

### Step 2: YouTube Enrichment
```bash
python3 pipeline.py enrich --dubbed-only
```
Scrapes YouTube About pages for websites, social links, emails. Computes `website_domain` for Ahrefs matching.

### Step 3: Ahrefs Enrichment (MUST USE MCP)
**IMPORTANT**: The Ahrefs REST API returns "Insufficient plan" for domain lookups. You MUST use the Ahrefs MCP tools directly.

After Step 2 completes, do the following automatically:

1. Run `python3 ahrefs_enrich.py --domains` to get the list of domains needing enrichment
2. For each batch of domains (up to 100), call the MCP tool `mcp__ahrefs__batch-analysis` with:
   - `select`: `["domain_rating", "org_traffic", "org_keywords"]`
   - `targets`: array of `{"url": "domain.com", "mode": "subdomains", "protocol": "both"}`
3. Save the results to the database by running Python:
   ```python
   import db
   from datetime import datetime
   db.upsert_contact(channel_id, website_dr=DR, website_traffic=TRAFFIC, website_keywords=KEYWORDS, ahrefs_enriched_at=datetime.now().isoformat())
   ```
   Match domains to channel_ids by querying: `SELECT channel_id, website_domain FROM contacts WHERE website_domain = 'domain.com'`

### Step 4: Lusha Email Enrichment
```bash
python3 pipeline.py lusha
```
Requires `LUSHA_API_KEY` in `.env`. Use `--dry-run` to preview without API calls.

### Step 5: Video Review
```bash
python3 pipeline.py review
```
Interactive CLI to approve/reject/select videos for dubbing. Non-interactive options:
- `--list` — list pending videos
- `--approve-all` — approve and select all pending
- `--approve VIDEO_ID` — approve a specific video
- `--reject VIDEO_ID` — reject a specific video

### Step 6: Dubbing
```bash
python3 pipeline.py dub --video VIDEO_ID --target-lang es
```
Only dubs videos with `review_status='approved'`. Use `--channel CHANNEL_ID` to auto-pick best video.

### Step 7: Export
```bash
python3 pipeline.py export
```
Exports `data/final_leads.csv` with all columns including DR, traffic, keywords, emails, review status, Lusha data.

## Configuration

- **API keys**: Stored in `.env` (gitignored), NOT in config.yaml
- **Settings**: `config.yaml` for discovery targets, keywords, rate limits
- **Database**: `data/outreach.db` (SQLite with WAL mode)

### Required .env keys
```
YOUTUBE_API_KEY=...
AHREFS_API_KEY=...
LUSHA_API_KEY=...
SYNTHESIA_API_KEY=...
```

## Key Files

| File | Purpose |
|------|---------|
| `.env` | API keys (gitignored) |
| `config.yaml` | Discovery targets, keywords, rate limits |
| `utils.py` | Shared config, HTTP session, retry, logging, domain cleaning |
| `db.py` | SQLite with context managers, migrations, column whitelists |
| `discover.py` | Channel discovery + dubbing detection (10 videos) |
| `enrich.py` | YouTube About page scraping |
| `ahrefs_enrich.py` | Ahrefs SEO metrics (use MCP, not REST) |
| `lusha_enrich.py` | Lusha email enrichment |
| `review.py` | Video review workflow (approve/reject/select) |
| `dub.py` | Synthesia video dubbing (with review gate) |
| `export.py` | CSV export (single JOIN, no N+1) |
| `pipeline.py` | CLI orchestrator |
| `enrich_csv.py` | Standalone CSV enricher (for one-off lists) |

## Quick Commands
```bash
python3 pipeline.py stats                              # Show pipeline stats
python3 pipeline.py discover --country ES --keyword "tutorial"  # Discover channels
python3 pipeline.py enrich --dubbed-only               # Enrich dubbed channels
python3 pipeline.py ahrefs --domains                   # List domains for MCP enrichment
python3 pipeline.py lusha --dry-run                    # Preview Lusha lookups
python3 pipeline.py review --list                      # List videos pending review
python3 pipeline.py review                             # Interactive review
python3 pipeline.py dub --video VIDEO_ID --target-lang es  # Dub a video
python3 pipeline.py export                             # Export final CSV
python3 pipeline.py export --zoominfo                  # Export for ZoomInfo
```
