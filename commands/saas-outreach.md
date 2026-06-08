# SaaS Video Outreach Pipeline

You are managing a SaaS video outreach pipeline. The goal is to find SaaS companies with video content, dub their videos to Spanish using Synthesia, enrich with contact emails, and prepare for outreach via Reply.io.

## Project Location
`/Users/george.fakorellis/Desktop/SEO Custom Projects/saas-video-outreach/`

## Status File
Always read `OUTREACH_STATUS.md` first to understand current progress and what's been done.

## The Full Pipeline (in order)

### Step 1: Discover Companies
Companies are already in the SQLite DB (`data/saas_outreach.db`). If more are needed:
```bash
python3 pipeline.py discover-capterra --category <category> --limit 50
python3 pipeline.py dedup
```

### Step 2: Find YouTube Channels
Scrape company homepages for YouTube channel links (no API quota needed):
```bash
python3 find_youtube_links.py
```
Then pull recent videos from those channels (uses YouTube API quota):
```bash
python3 pull_channel_videos.py
```
**Important**: YouTube API quota is 10,000 units/day. Channel ID resolution via search costs 100 units each. Video pull via playlistItems costs 1 unit. Always check quota first:
```python
from googleapiclient.discovery import build as yt_build
youtube = yt_build('youtube', 'v3', developerKey=api_key)
youtube.search().list(q='test', type='channel', part='snippet', maxResults=1).execute()
```

### Step 3: Review Companies (Web App)
```bash
python3 review_websites.py --port 8889
```
- **Review tab**: Shows companies with videos side-by-side. Approve or reject. Select which video to dub. Set trim start/end times.
- **Dashboard tab**: Shows all approved companies, their dubbed videos, contacts, outreach status.
- Edit domain with the pencil button if the website is wrong.
- Decisions saved to `data/review_decisions.json`
- Companies from the DB are filtered: DR 20-85, traffic < 500K, must have YouTube channel.
- Companies from `data/saas_300_outreach_ready.csv` are also shown.

### Step 4: Customer Dedup (CRITICAL — do before dubbing)
Cross-reference ALL approved companies against `data/Customers.csv` (24,971 records, 8,477 unique email domains).
Check by:
1. Exact domain match against `Email Domain` column
2. Root domain match (e.g., company.ca vs company.com)
3. Company name match against `Clean Parent Name` column

Block any confirmed customers by setting their status to `rejected` with `block_reason: 'existing_customer'` in review_decisions.json.

### Step 5: Dub Videos with Synthesia
```bash
python3 batch_dub.py           # Dub all approved companies without Synthesia links
python3 batch_dub.py --dry-run # Preview what will be dubbed
python3 batch_dub.py --limit 5 # Only dub first 5
```
Process: download video → trim to specified range → upload to Synthesia → dub to Spanish with lip sync → poll for completion → set visibility to public → save share link + GIF URL.

GIF URL pattern: `https://synthesia-ttv-data.s3.amazonaws.com/video_data/{asset_id}/transfers/rendered_video.gif`

After dubbing, backfill GIF URLs for any that are missing:
```python
import json
with open('data/review_decisions.json') as f:
    decisions = json.load(f)
for domain, d in decisions.items():
    asset_id = d.get('synthesia_asset_id', '')
    if asset_id and not d.get('synthesia_gif_url'):
        d['synthesia_gif_url'] = f'https://synthesia-ttv-data.s3.amazonaws.com/video_data/{asset_id}/transfers/rendered_video.gif'
with open('data/review_decisions.json', 'w') as f:
    json.dump(decisions, f, indent=2)
```

### Step 6: Enrich with Contacts (AirOps MCP)
Use the AirOps MCP tools — do NOT upload CSVs manually.

1. Prepare rows from review_decisions.json (approved companies with Synthesia links, no hunter_contact yet)
2. Write to AirOps grid:
   - Grid ID: **60558**
   - Table ID: **78167**
   - Use `mcp__airops__write_grid` with mode `create`
   - Columns: Company Name, Domain, Website, Category, Domain Rating, Organic Traffic, Organic Keywords, Selected Video URL, Video Source, Dubbed To, Synthesia Share Link, Synthesia GIF URL, Trim Start, Trim End, Outreached
3. The "Simple Email Extraction - George" power agent column runs automatically and extracts up to 3 contacts (First Name, Last Name, Email, Position)
4. Export results — the user will download the CSV from AirOps

### Step 7: Prepare for Reply.io
The final CSV for Reply.io needs these columns:
- Company Name, Domain, Website
- Contact First Name, Contact Last Name, Contact Email, Contact Job Title
- Selected Video URL, Synthesia Share Link, Synthesia GIF URL
- Domain Rating, Organic Traffic

### Step 8: Mark as Outreached
After sending via Reply.io, mark companies in `data/review_decisions.json`:
```python
decisions[domain]['outreached'] = True
```
This shows as checked in the Dashboard tab.

## Key Rules
1. **NEVER outreach to existing customers** — always check against Customers.csv first
2. **Don't show already-reviewed companies** — review_decisions.json tracks all approve/reject decisions
3. **Clean up local video files** — batch_dub.py deletes downloaded videos after uploading to Synthesia
4. **YouTube API quota** — resets daily at midnight Pacific. Homepage scraping (`find_youtube_links.py`) uses zero quota.
5. **Duplicate check in AirOps grid** — before writing new rows, check which domains already exist in the grid to avoid duplicates

## Quick Status Check
```python
import json, sqlite3
conn = sqlite3.connect('data/saas_outreach.db')
with open('data/review_decisions.json') as f:
    d = json.load(f)
print(f"DB companies: {conn.execute('SELECT COUNT(*) FROM companies').fetchone()[0]}")
print(f"Approved: {sum(1 for v in d.values() if v.get('status')=='approved')}")
print(f"Dubbed: {sum(1 for v in d.values() if v.get('synthesia_share_link'))}")
print(f"Outreached: {sum(1 for v in d.values() if v.get('outreached'))}")
```
