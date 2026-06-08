---
name: backlink-monitor
description: Monitor Synthesia backlinks for removals and competitor backlinks (HeyGen, Veed.io) for new links via Ahrefs. Run weekly.
---

# Backlink Monitor

Weekly backlink intelligence report. Posts to Notion with charts, tables, and competitive analysis.

## Project Location
`/Users/george.fakorellis/Desktop/SEO Custom Projects/backlink-monitor/`

## Config
Read `config.json` for: `own_domain`, `competitors`, `min_domain_rating` (45), `exclude_spam` (true).

## Notion Page
Post report to: `33cc16d22bf1806d9242cefa5ad1a37d` (BackLink Monitoring)
Fetch `notion://docs/enhanced-markdown-spec` via ReadMcpResourceTool (server: "notion") before writing.

---

## Filters — Applied to ALL Backlink Queries

### Exclude social/low-SEO-value platforms
Add these to every query's `where` clause:
```json
{"not":{"field":"name_source","is":["substring","youtube"]}},
{"not":{"field":"name_source","is":["substring","github"]}},
{"not":{"field":"name_source","is":["substring","apple.com"]}},
{"not":{"field":"name_source","is":["substring","reddit"]}},
{"not":{"field":"name_source","is":["substring","twitter"]}},
{"not":{"field":"name_source","is":["substring","facebook"]}},
{"not":{"field":"name_source","is":["substring","linkedin"]}},
{"not":{"field":"name_source","is":["substring","instagram"]}},
{"not":{"field":"name_source","is":["substring","tiktok"]}},
{"not":{"field":"name_source","is":["substring","bsky"]}},
{"not":{"field":"name_source","is":["substring","medium.com"]}},
{"not":{"field":"name_source","is":["substring","quora"]}},
{"not":{"field":"name_source","is":["substring","play.google"]}},
{"not":{"field":"name_source","is":["substring","pinterest"]}},
{"not":{"field":"name_source","is":["substring","notion.site"]}},
{"not":{"field":"name_source","is":["substring","bing.com"]}}
```

### English only
```json
{"field":"languages","list_is":{"any":["eq","en"]}}
```

### Post-query filtering
After receiving results, discard: embeds on unrelated pages, support tickets (freshdesk/zendesk), forums, Stack Overflow, Product Hunt, marketplaces (gumroad/payhip), podcast RSS, event pages (luma/meetup), privacy/TOS pages, job listings (ashbyhq), low-quality netlify/vercel AI directories, beehiiv/kit.com newsletters, Postman, Telegram, Craigslist, gitnux (noindex).

Keep only: blog posts, articles, guides, tool roundups, news, research/academic pages, review sites, enterprise sites.

---

## Step 0: Read Config & Last Run Date
Read `config.json` and `last-run.json`. If no previous run, use 7 days ago.

## Step 1: Pull All Data

Run queries in parallel batches of 3. Total: ~25 queries, ~7,000-8,000 units.

### Group A — Lost & Gained (6 queries)
For each of synthesia.io, heygen.com, veed.io:
- **Lost:** `site-explorer-all-backlinks` with `is_lost=true`, `history=since:<last_run>`, all filters, `select=url_from,url_to,anchor,domain_rating_source,is_dofollow,is_lost,lost_reason,last_seen,first_seen_link,name_source,traffic,languages`, `order_by=domain_rating_source:desc`, `limit=1000`
- **Gained:** `site-explorer-all-backlinks` with `first_seen_link >= <last_run>T00:00:00Z`, `history=live`, all filters, `select=url_from,url_to,anchor,domain_rating_source,is_dofollow,first_seen_link,name_source,traffic,title,languages`, `order_by=domain_rating_source:desc`, `limit=1000`

### Group B — Historical Trends (6 queries)
- `site-explorer-refdomains-history` for each domain — 6 months back, `history_grouping=weekly`
- `site-explorer-metrics-history` for each domain — 6 months back, `history_grouping=monthly`, `select=date,org_traffic`

### Group C — Backlinks Stats (3 queries)
- `site-explorer-backlinks-stats` for each domain — `date=<today>`

### Group D — Domain Rating History (3 queries)
- `site-explorer-domain-rating-history` for each domain — 6 months back, `history_grouping=weekly`
- Note: DR is usually flat, just grab latest value for each brand

### Group E — Anchors (6 queries)
For each domain, run TWO anchor queries:
1. **Top anchors (branded view):** `select=anchor,refdomains,dofollow_links,links_to_target`, `order_by=refdomains:desc`, `limit=15`, `history=live`
2. **Keyword anchors (filtered):** Same select but add `where` filter to find keyword anchors specifically:
```json
{"or":[
  {"field":"anchor","is":["isubstring","ai video"]},
  {"field":"anchor","is":["isubstring","video generator"]},
  {"field":"anchor","is":["isubstring","video maker"]},
  {"field":"anchor","is":["isubstring","text to video"]},
  {"field":"anchor","is":["isubstring","ai avatar"]},
  {"field":"anchor","is":["isubstring","video editor"]},
  {"field":"anchor","is":["isubstring","video creation"]},
  {"field":"anchor","is":["isubstring","video platform"]},
  {"field":"anchor","is":["isubstring","ai tool"]},
  {"field":"anchor","is":["isubstring","video compressor"]},
  {"field":"anchor","is":["isubstring","ai dubbing"]},
  {"field":"anchor","is":["isubstring","voice clone"]},
  {"field":"anchor","is":["isubstring","screen recorder"]},
  {"field":"anchor","is":["isubstring","subtitle"]},
  {"field":"anchor","is":["isubstring","teleprompter"]}
]}
```
Use keyword anchor query results for Chart 5 (Keyword Anchors Breakdown) — this gives accurate numbers instead of relying on top-15 which is dominated by branded anchors.

### Group F — Link Gap (3 queries)
- `site-explorer-referring-domains` for each domain — `select=domain,domain_rating,dofollow_links,links_to_target,traffic_domain`, `where=DR>=50 AND is_dofollow=true`, `order_by=domain_rating:desc`, `limit=100`, `history=live`
- Then compute gap in Python: domains linking to competitors but NOT synthesia.io (exclude generic/social domains)

### Group G — Pages by Backlinks (3 queries)
- `site-explorer-pages-by-backlinks` for each domain — `select=url_to,refdomains_target,dofollow_to_target,new_links_to_target,title_target`, `order_by=refdomains_target:desc`, `limit=25`
- For Synthesia: add `where` to exclude `share.synthesia.io` and filter `refdomains_target >= 50`
- For HeyGen: exclude `app.heygen.com` and `labs.heygen.com`

### Group H — Synthesia Top Pages by Traffic (1 query)
- `site-explorer-top-pages` for synthesia.io — `select=url,sum_traffic,keywords,referring_domains,top_keyword,top_keyword_best_position,top_keyword_volume,value`, `order_by=sum_traffic:desc`, `limit=25`, `date=<today>`, `country=us`

---

## Step 2: Generate Charts

Generate 8 charts using Python matplotlib. Save to /tmp/. Upload all to Google Drive.

**Colors:** Synthesia=#6366F1, HeyGen=#F97316, Veed=#EC4899

### Chart 1: This Week — Gained vs Lost
Grouped bar chart. Two bars per brand (green=gained, red=lost). Net value annotated below each pair. `figsize=(10, 5)`

### Chart 2: Referring Domains — 6 Month Trend
Line chart, weekly data, all 3 brands. Y-axis in K. Legend with latest value. `figsize=(14, 5)`

### Chart 3: Est. Organic Traffic — 6 Month Trend
Grouped bar chart, monthly, all 3 brands side by side. Value labels on bars. Y-axis in M. `figsize=(14, 5)`

### Chart 4: Anchor Distribution by Type
Grouped bar chart. Categories: Branded, Keyword, URL, Generic. Calculate from anchor data:
- **Branded:** brand name variants (Synthesia, Synthesia.io, Synthesia AI, Try/Visit Synthesia, etc.)
- **Keyword:** descriptive terms (video editor, AI video generator, AI dubbing, AI tools, etc.)
- **URL:** naked URLs (https://www.synthesia.io/, www.synthesia.io, etc.)
- **Generic:** Visit Website, Visit, Visit Site, click here, etc.
Annotate with call-out arrow on keyword gap. `figsize=(12, 6)`

### Chart 5: Keyword Anchors Breakdown
Horizontal bar chart. Show specific keyword anchors: video editor, AI video generator, video compressor, AI dubbing, AI voice cloning, AI video, AI video editor, online video editor, AI tools, AI avatars. All 3 brands. `figsize=(12, 6.5)`

### Chart 6: Synthesia — Top Pages by Referring Domains
Horizontal bar chart. Exclude homepage and share.synthesia.io embeds. Color by page type: blue=#4A90D9 for /post/ (blog), purple=#6366F1 for /features/, gray=#9CA3AF for other. `figsize=(13, 7)`

### Chart 7: All Brands — Top Content Pages Compared
Horizontal bar chart. Mix top non-homepage pages from all 3 brands (exclude affiliate/localized URLs). Color by brand. Sorted descending. `figsize=(13, 7)`

### Upload to Google Drive

```python
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

with open('/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gdrive-token.pickle', 'rb') as f:
    creds = pickle.load(f)

service = build('drive', 'v3', credentials=creds)
folder_id = '1Ay76vQA2rt0PFPZ0RLE5oTklW7Uv4ELe'

media = MediaFileUpload('/tmp/chart.png', mimetype='image/png')
file = service.files().create(
    body={'name': 'backlink-<chart-name>.png', 'parents': [folder_id]},
    media_body=media, fields='id'
).execute()

service.permissions().create(
    fileId=file.get('id'),
    body={'type': 'anyone', 'role': 'reader'}
).execute()

gdrive_url = f"https://lh3.googleusercontent.com/d/{file.get('id')}"
```

If token expires, re-run OAuth:
```python
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file(
    '/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gdrive-oauth-client.json',
    ['https://www.googleapis.com/auth/drive.file']
)
creds = flow.run_local_server(port=0)
with open('/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gdrive-token.pickle', 'wb') as f:
    pickle.dump(creds, f)
```

---

## Step 3: Build Notion Report

Use `mcp__notion__notion-update-page` with `replace_content` command on page `33cc16d22bf1806d9242cefa5ad1a37d`.

### Report Structure (flat, no accordions)

```
*<date range> | DR 45+ | English editorial only*

---

[Chart 1: This Week Gained vs Lost]
[Chart 2: Referring Domains 6mo Trend]
[Chart 3: Organic Traffic 6mo Trend]
[Chart 4: Anchor Distribution by Type]
[Chart 5: Keyword Anchors Breakdown]
[Chart 6: Synthesia Top Pages by Refdomains]
[Chart 7: All Brands Top Pages Compared]

---

## Key Numbers
Table (4 columns): Metric | Synthesia | HeyGen | Veed.io
Rows: DR, Referring Domains, 6mo Refdom Growth %, Est. Organic Traffic, Keyword Anchors (domains), This Week Net

---

# Actions
Numbered list (1-5 max). Each item bold action + context + link. No callout blocks.
Priority: Fix broken URLs > Pitch for re-inclusion > Pitch competitor wins > Monitor.

---

# Synthesia *(week of <dates>)*
Single table with ALL lost and gained links merged. Sorted by date.
Columns: Date / Status / Page | Details
- Lost rows: "Apr X — LOST — [Source](url) DR X — dofollow/nofollow" | "anchor" → target → reason
- Gained rows: "Apr X — NEW — [Source](url) DR X — dofollow/nofollow" | "anchor" → target
- Dofollow lost = pink_bg, dofollow gained = green_bg, nofollow = no color

# HeyGen *(week of <dates>)*
Same format.

# Veed.io *(week of <dates>)*
Same format.

---

## Synthesia Pages — Links vs Traffic Performance
Table correlating refdomains with organic traffic. Color-coded:
- green_bg: high traffic relative to links (good performers)
- yellow_bg: lots of links but moderate traffic (underperforming — content refresh opportunity)
- pink_bg: lots of links but zero/minimal traffic (broken, fallen off rankings, or 404)
Columns: Page | Refdomains → Traffic → Top Keyword (Position)
Data from: cross-referencing Group G (pages-by-backlinks) with Group H (top-pages)

## Synthesia — Top Pages by Traffic Value
Bulleted list of top pages sorted by traffic value (value field from top-pages).
Format: **/page-path** — X traffic — **$YK value** — Z refdoms
Highlight high-value-per-visit pages (L&D, tools pages with high CPC).

---

## Link-Earning Content Breakdown
Bullets analyzing which types of Synthesia pages earn the most links:
- Blog posts (list top 5 by refdoms)
- Feature pages (list top 5)
- Note absence of tool pages vs Veed

## Pages at Risk
List Synthesia pages with high refdoms but issues:
- 404s (immediate fix needed)
- Dropped rankings despite links
- Old URL variants (/home, /home-update) with orphaned link equity

## How Competitors Earn Links Differently
Bullets comparing strategies:
- Synthesia: blog content, PR, embeds
- HeyGen: free tool pages, localized versions, partnerships
- Veed: massive tool page ecosystem, keyword-rich anchors

---

# Link Gap — Who Links to Them But Not Us
Table: Domain | Opportunity
From Group F cross-reference. Exclude generic domains (google.com, t.me, etc.).
Highlight top 3 with blue_bg.

---

## Content Opportunities
Bullets with specific recommendations based on the data.
```

### Table Rules
- 2-3 columns max. `fit-page-width="true"`, `header-row="true"`
- Dofollow lost = `pink_bg`, dofollow gained = `green_bg`, top opportunities = `blue_bg`
- Show anchor text in quotes, target URL path, dofollow/nofollow, traffic if notable
- Each link table row starts with date: "Apr X — LOST/NEW"
- No callout blocks for action items — use numbered list instead

---

## Step 4: Save Run Metadata

Write `last-run.json`:
```json
{
  "last_run": "<YYYY-MM-DD>",
  "period": "<start> to <end>",
  "synthesia": { "lost": N, "gained": N, "net": N, "live_backlinks": N, "referring_domains": N },
  "heygen": { "lost": N, "gained": N, "net": N, "live_backlinks": N, "referring_domains": N },
  "veed": { "lost": N, "gained": N, "net": N, "live_backlinks": N, "referring_domains": N },
  "ahrefs_units_consumed": N
}
```

---

## Important Notes
- Domain-wide queries MUST use `mode: subdomains`
- Monetary values from Ahrefs are in USD cents — divide by 100
- Charts uploaded to Google Drive (folder `1Ay76vQA2rt0PFPZ0RLE5oTklW7Uv4ELe`), NOT imgur
- DR is usually flat — don't chart it, show inline in Key Numbers table
- Total API cost ~7,000-8,000 units per run
- Run queries in parallel batches of 3 where possible
- Always show anchor text + target URL in link tables
- For top-pages query, `traffic` column is called `sum_traffic`, position is `best_position`
