---
name: link-outreach
description: Manage the SaaS link building outreach pipeline — discover prospects, qualify via Ahrefs, scrape + analyze, enrich contacts via AirOps, push to Reply.io sequences. Supports niche edit, broken link, and generic pitch campaigns.
---

# Link Building Outreach

You are running the automated link building outreach pipeline. This skill handles end-to-end: prospect discovery, qualification, contact enrichment, and Reply.io push.

## Project Location

`/Users/george.fakorellis/Desktop/SEO Custom Projects/link-outreach/`

## Config

Read `config.json` for:
- `brand` / `brand_domain`: Target brand (default: synthesia.io)
- `competitors`: Competitor domains (used for classification — competitor mentions = opportunities)
- `exclude_domains`: Domains to skip entirely (platforms, review sites, competitors, etc.)
- `qualification.min_dr`: Minimum Domain Rating (default: 20)
- `airops.outreach_grid_id`: AirOps enrichment grid ID (61680)
- `airops.outreach_table_id`: AirOps enrichment table ID (81833)
- `reply_io.sequences`: Reply.io sequence IDs per campaign type
- `reply_io.api_key_file`: Path to Reply.io API key

## Campaign Types

### 1. Niche Edit Campaign
Find articles where a Synthesia link naturally fits. Two outreach tracks:
- **Strong/medium fit** → personalized niche edit email (reference specific section)
- **Weak/no fit** → generic pitch (offer free video for their article)

### 2. Broken Link Campaign
Find sites linking to a dead competitor domain. Pitch Synthesia as a replacement.
- Lead with "you have a broken link" (helping them)
- Suggest a relevant Synthesia URL as replacement

### 3. Generic / Convert Article to Video
Topic-adjacent articles. Offer to create a free Synthesia video for their article in exchange for embed + mention.

## Templates

All email templates are in `link-outreach/templates/`:
- `broken-link.md` — Broken link outreach email structure
- `niche-edit.md` — Niche edit email structure
- `guest-post.md` — Guest post pitch
- `llm-brief-sequence-1-niche-edit.md` — Full LLM brief for Reply.io Sequence 1 (niche edit + free plan offer)
- `llm-brief-sequence-2-generic-pitch.md` — Full LLM brief for Reply.io Sequence 2 (free video offer)

## Master Tracker

`link-outreach/master-tracker.csv` — every domain ever contacted. Check this for dedup before any new campaign.

---

## Pipeline

### Step 1: Input & Campaign Setup

Ask the user:
1. **Campaign type**: niche edit, broken link, or generic pitch?
2. **Target Synthesia URL**: which Synthesia page should we link to?
3. **Prospect source**: 
   - Niche edit: search queries (Firecrawl) → discover articles
   - Broken link: Ahrefs export CSV or Ahrefs MCP → backlinks to dead domain
   - Manual: user provides a CSV/list of URLs

Create campaign directory: `link-outreach/campaigns/{type}/{date}-{slug}/`

### Step 2: Discovery (varies by campaign type)

#### Niche Edit Discovery
1. Scrape the target Synthesia page to extract use cases, pain points, and keywords
2. Build 25-40 search queries around USE CASES, not tool names
   - WRONG: "ai video translator tool"
   - RIGHT: "how to translate training videos for global teams"
3. Run Firecrawl search for each query (Google operators)
4. Collect ~300 raw results

**Critical rule:** Search by USE CASE, never by tool name. Tool name searches find competitor pages, not link opportunities.

#### Broken Link Discovery
1. User provides an Ahrefs backlink export CSV (or we pull via Ahrefs MCP)
2. Parse CSV — extract: URL, domain, DR, traffic, anchor, page type, dofollow status
3. Filter out: spam, platforms, competitors, non-200 pages
4. Score and rank by: DR, traffic, dofollow, page type, language

No Firecrawl discovery needed — the backlink data IS the prospect list.

### Step 3: Dedup & Qualification

1. Dedup against `master-tracker.csv` and `config.json` exclude list
2. Qualify via Ahrefs (MCP or batch CSV):
   - DR >= 20 (configurable in config.json)
   - Filter spam domains
3. Save qualified list to `{campaign_dir}/qualified.json`

### Step 4: Scrape & Analyze (niche edit campaigns only)

Run the Python script for bulk scraping + heuristic analysis:
```
python3 link-outreach/scripts/scrape_and_analyze.py
```

This script:
- Scrapes each prospect page via Firecrawl SDK
- Searches for fit keywords in content
- Classifies fit strength: strong / medium / weak / no fit
- Flags competitor mentions as OPPORTUNITIES (reclassify to strong fit)
- Flags Synthesia mentions → EXCLUDE from outreach
- Saves results to `{campaign_dir}/analyzed.json`

**For broken link campaigns**: skip this step — fit is implicit (they linked to a dead competitor).

### Step 5: Assign Outreach Tracks

**Niche edit campaigns:**
- Strong + medium fit → Sequence 1 (niche edit + free plan offer)
- Weak + no fit → Sequence 2 (generic pitch + free video offer)

**Broken link campaigns:**
- All prospects → Broken link sequence (pitch replacement link)
- High-value prospects (DR 70+, listicles, comparison articles) → priority outreach

### Step 6: AirOps Enrichment (find email contacts)

Push prospect domains to AirOps Grid **61680** (Table **81833**) for Hunter email enrichment.

Grid columns (writable):
- `Title` — page title or article topic
- `Company` — company/brand name (human-readable, not domain)
- `Domain` — root domain (e.g. "wyzowl.com")

The grid's automation ("Simple Email Extraction - George") runs automatically and populates:
- `First Name`, `Last Name`, `Email`, `Position` (x3 contacts per domain)

**CRITICAL: For 50+ rows, use a Python script to push data. Never push large datasets via MCP tool calls — they truncate fields.**

Write a Python script like this:
```python
import requests
import json
import time

AIROPS_API = "https://app.airops.com/public_api/airops_apps/grid"
# Get the API auth from the MCP connection — or use the write_grid MCP for small batches

# For large batches, chunk into groups of 50 and call write_grid MCP per chunk
# Each chunk: [{"Title": "...", "Company": "...", "Domain": "..."}, ...]
```

Or use the `mcp__airops__write_grid` tool in batches of 20-30 rows max, ensuring ALL fields are complete in every batch.

After pushing, wait for enrichment to complete (check grid for populated email fields).

### Step 7: Reply.io Push

Read the Reply.io API key from: `/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/reply-io-api-key.txt`

API endpoint: `POST https://api.reply.io/v1/actions/addandpushtocampaign`

Headers:
```
X-Api-Key: {api_key}
Content-Type: application/json
```

Payload per contact:
```json
{
  "campaignId": {sequence_id},
  "firstName": "...",
  "lastName": "...",
  "email": "...",
  "company": "...",
  "customFields": {
    "article_url": "https://...",
    "article_topic": "...",
    "synthesia_target_page": "https://www.synthesia.io/...",
    "broken_url": "https://hourone.ai/...",
    "anchor_text": "..."
  }
}
```

**For broken link campaigns**, the custom fields should include:
- `article_url` — the prospect's page URL
- `article_topic` — the page title/topic
- `broken_url` — the dead hourone.ai (or other) URL on their page
- `anchor_text` — what the broken link's anchor text is
- `synthesia_target_page` — the Synthesia URL we're suggesting as replacement

Reply.io sequence IDs are stored in `config.json` under `reply_io.sequences`. If a sequence doesn't exist for the campaign type yet, tell the user they need to create one in Reply.io first and provide the ID.

Write a Python script for bulk pushing (never push 50+ contacts one-by-one via individual tool calls):
```python
import requests
import json
import time

API_KEY = open("/path/to/reply-io-api-key.txt").read().strip()
SEQUENCE_ID = 12345  # from config.json

for contact in contacts:
    resp = requests.post(
        "https://api.reply.io/v1/actions/addandpushtocampaign",
        headers={"X-Api-Key": API_KEY, "Content-Type": "application/json"},
        json={
            "campaignId": SEQUENCE_ID,
            "firstName": contact["first_name"],
            "lastName": contact["last_name"],
            "email": contact["email"],
            "company": contact["company"],
            "customFields": contact["custom_fields"]
        }
    )
    time.sleep(0.5)  # rate limit
```

### Step 8: Update Master Tracker

Append all contacted domains to `master-tracker.csv` with:
- Domain, DR, Campaign Type, Campaign Slug, Date, Outreach Track, Contact Email

---

## Key Rules (learned from past campaigns)

1. **Discovery searches USE CASES, not tool names** — "multilingual training video" not "video translator"
2. **Don't filter pages by URL pattern or word count** — trust the discovery queries
3. **Pages mentioning Synthesia → EXCLUDE** — don't outreach to sites already aware
4. **Pages mentioning competitors → OPPORTUNITY** — pitch replacing/adding Synthesia
5. **All prospects get outreached** — the email template changes by fit strength, not whether they're contacted
6. **Never push 50+ rows via MCP tool calls** — use Python scripts to avoid truncation
7. **Always verify AirOps data completeness** — read a sample from middle/end of grid after pushing
8. **Firecrawl SDK syntax**: `app.scrape(url, formats=["markdown"], only_main_content=True)` — NOT `scrape_url` or `params={}`

## File Structure

```
link-outreach/
  config.json                          # Global config
  master-tracker.csv                   # All-time domain dedup list
  templates/
    broken-link.md                     # Broken link email template
    niche-edit.md                      # Niche edit email template
    guest-post.md                      # Guest post template
    llm-brief-sequence-1-niche-edit.md # Full LLM brief for Sequence 1
    llm-brief-sequence-2-generic-pitch.md # Full LLM brief for Sequence 2
  scripts/
    scrape_and_analyze.py              # Bulk Firecrawl scraping + fit analysis
  campaigns/
    niche-edits/{date}-{slug}/         # Niche edit campaign data
    hourone-broken-links/              # Broken link campaign data
      prospects.md                     # Qualitative prospect analysis
      ranked-prospects.csv             # Scored + ranked prospect list
```

## Credentials

- **Reply.io API key**: `/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/reply-io-api-key.txt`
- **Firecrawl API key**: `fc-677951d30ea84d2b922b132670e92068` (also in `~/.claude.json`)
- **AirOps**: Connected via MCP (no separate key needed)
- **Ahrefs**: Connected via MCP (no separate key needed)
