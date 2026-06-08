# SaaS Video Outreach Pipeline

## Pipeline Overview

Discover SaaS companies from software directories, detect video content, enrich with SEO metrics and contacts, review videos via web UI, and export for outreach.

## Architecture

```
pipeline.py  (CLI orchestrator)
    |
utils.py     (config, logging, retry, domain cleaning, column whitelists)
db.py        (SQLite: companies, discovery_sources, company_videos, contacts)
    |
discover_capterra.py -> dedup.py -> detect_video.py -> ahrefs_enrich.py -> lusha_enrich.py -> review_server.py -> export.py
```

## Company Status Workflow
```
discovered -> video_checked -> enriched -> exported
```

## Pipeline Steps

### Step 1: Discovery (Capterra via Apify)
```bash
cd "/Users/george.fakorellis/Desktop/SEO Custom Projects/saas-video-outreach"
python3 pipeline.py discover-capterra
python3 pipeline.py discover-capterra --category crm-software --limit 50
```
Uses Apify's Capterra Scraper actor. Handles Cloudflare automatically.
10 categories: CRM, project management, marketing automation, video conferencing, help desk, HR, accounting, ecommerce, LMS, customer success.

### Step 2: Dedup
```bash
python3 pipeline.py dedup
```
Merges companies found in multiple sources/categories.

### Step 3: Video Detection
```bash
python3 pipeline.py detect-video
python3 pipeline.py detect-video --youtube-only --limit 100
python3 pipeline.py detect-video --google-only
```
**Tier 1**: YouTube Data API — searches for company's official channel, verifies domain match.
**Tier 2**: Google Video Search via Serper.dev — fallback for companies without YouTube channels.

### Step 4: Ahrefs Enrichment (USE MCP)
**IMPORTANT**: Use the Ahrefs MCP tools directly for enrichment.

1. Run `python3 ahrefs_enrich.py --domains` to get domains list
2. Call `mcp__ahrefs__batch-analysis` in batches of 100:
   - `select`: `["domain_rating", "org_traffic", "org_keywords"]`
   - `targets`: `[{"url": "domain.com", "mode": "subdomains", "protocol": "both"}]`
3. Save results:
   ```python
   from ahrefs_enrich import save_ahrefs_results
   save_ahrefs_results({"domain.com": {"dr": 45, "traffic": 10000, "keywords": 500}})
   ```

### Step 5: Lusha Contact Enrichment
```bash
python3 pipeline.py lusha
python3 pipeline.py lusha --dry-run
python3 pipeline.py lusha --credits
```
Searches by company domain + job title. Target roles: VP Marketing, Head of Marketing, CMO, Head of Video, Head of Content, CEO, Founder, Co-founder, CTO.
Max 3 contacts per company.

### Step 6: Video Review (Web UI)
```bash
python3 pipeline.py review --port 8080
```
Opens browser with embedded videos. Approve/reject per video.
Filter by: pending, approved, rejected, all.

### Step 7: Export
```bash
python3 pipeline.py export
python3 pipeline.py export --approved-only --min-dr 20
python3 pipeline.py export --output data/filtered.csv
```

## Configuration

- **API keys**: `.env` (YOUTUBE_API_KEY, AHREFS_API_KEY, LUSHA_API_KEY, APIFY_API_TOKEN, SERPER_API_KEY)
- **Settings**: `config.yaml` (categories, rate limits, enrichment params)
- **Database**: `data/saas_outreach.db` (SQLite with WAL mode)

## Database Schema

### companies (PK: domain)
Main entity. Tracks: name, website, category, YouTube channel info, website video info, Ahrefs metrics, status.

### discovery_sources
Which directory (capterra/g2/crunchbase) found each company.

### company_videos
Individual videos found per company. Has review_status (pending/approved/rejected).

### contacts
Decision makers from Lusha. Multiple per company (up to 3).

## Key Files

| File | Purpose |
|------|---------|
| `utils.py` | Config, logging, retry, domain cleaning, column whitelists |
| `db.py` | SQLite with context managers, migrations, column whitelists |
| `discover_base.py` | Abstract base for discovery sources |
| `discover_capterra.py` | Capterra scraping via Apify |
| `dedup.py` | Cross-source deduplication |
| `detect_video.py` | YouTube API + Google Video search |
| `search_base.py` | Abstract base for search providers |
| `search_serper.py` | Serper.dev implementation |
| `ahrefs_enrich.py` | Ahrefs SEO metrics (MCP or REST) |
| `lusha_enrich.py` | Lusha contact enrichment |
| `review_server.py` | Web UI for video review |
| `export.py` | CSV export |
| `pipeline.py` | CLI orchestrator |

## Quick Commands
```bash
python3 pipeline.py stats
python3 pipeline.py discover-capterra --category crm-software
python3 pipeline.py dedup
python3 pipeline.py detect-video --limit 50
python3 pipeline.py ahrefs --domains
python3 pipeline.py lusha --dry-run
python3 pipeline.py review
python3 pipeline.py export --approved-only --min-dr 20
```
