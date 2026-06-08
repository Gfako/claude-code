---
name: link-outreach-system
description: "Automated link building outreach system — niche edits with two outreach tracks. Uses Firecrawl discovery + Python scraping script, Ahrefs qualification, AirOps enrichment, Reply.io API push."
metadata: 
  node_type: memory
  type: reference
  originSessionId: e7ca726f-d584-49eb-922e-49f9724cfa48
---

## Link Outreach System

- Skill: `/link-outreach` — runs full pipeline
- Project root: `/Users/george.fakorellis/Desktop/SEO Custom Projects/link-outreach/`
- Config: `link-outreach/config.json` — competitors, exclude list, DR thresholds, Reply.io sequence IDs
- Master tracker: `link-outreach/master-tracker.csv` — every domain ever discovered, used for dedup
- Templates: `link-outreach/templates/` — email templates per outreach track
- Scripts: `link-outreach/scripts/scrape_and_analyze.py` — bulk scraping + heuristic analysis

### Pipeline (proven workflow from first run)
1. User provides target Synthesia URL
2. Firecrawl scrapes target page → extract use cases, pain points, fit keywords
3. Firecrawl search (Google operators) discovers prospect articles — search by USE CASE not tool name (25-40 queries, ~300 raw results)
4. Dedup against master tracker + exclude list → ~250-300 unique domains
5. Ahrefs qualification — if API units available use MCP, otherwise export CSV for manual Ahrefs batch analysis (DR >= 20)
6. Python script `scrape_and_analyze.py` runs in background — scrapes all pages via Firecrawl SDK, heuristic keyword analysis, classifies fit strength (~20-30 min for 250 pages)
7. Post-processing: reclassify competitors as opportunities, exclude Synthesia-mentioned pages, assign outreach tracks
8. AirOps Grid 61680 enriches contacts (Hunter via power agent)
9. Reply.io API pushes contacts into two sequences (niche edit + generic pitch)
10. Master tracker updated

### Two Outreach Tracks
- **Niche edit** (strong + medium fit): personalized email referencing specific section of their article where link fits
- **Generic pitch** (weak + no fit): topic-adjacent email about their audience benefiting from video translator

### Key Rules (learned from first campaign)
- Discovery searches USE CASES not the tool name — "multilingual training video" not "video translator"
- Do NOT filter pages by word count or URL pattern — discovery already targets articles
- Pages mentioning Synthesia → EXCLUDE (don't outreach)
- Pages mentioning competitors → OPPORTUNITY (pitch replacing/adding Synthesia)
- Ahrefs API units may run out — always have CSV export fallback ready
- Firecrawl Python SDK: use `app.scrape(url, formats=["markdown"], only_main_content=True)` — NOT `scrape_url` or `params={}`
- Firecrawl API key: `fc-677951d30ea84d2b922b132670e92068` (configured in `~/.claude.json`)

### Key Details
- AirOps enrichment grid (Hunter): ID 64148, Table ID 82974 — current authoritative IDs in `link-outreach/config.json` under `airops.enrichment_grid_id`. (Older IDs 61680/79677 and 63328/81833 are legacy.)
- Reply.io API key: `.credentials/reply-io-api-key.txt`
- Reply.io endpoint: `POST https://api.reply.io/v1/actions/addandpushtocampaign`
- Competitors: heygen, veed, d-id, elai, colossyan, hourone, invideo, deepbrain, vyond, descript, runway, luma, kling
- Campaigns stored in: `link-outreach/campaigns/niche-edits/{date}-{slug}/`

### First Campaign (2026-04-08 video-translator)
- Target: https://www.synthesia.io/features/video-translator
- 301 discovered → 262 qualified (DR >= 20) → 73 strong + 47 medium + 70 weak + 62 no fit + 9 excluded
- ~287 Firecrawl credits used (45 searches + 242 scrapes)
- Files in: `link-outreach/campaigns/niche-edits/2026-04-08-video-translator/`
