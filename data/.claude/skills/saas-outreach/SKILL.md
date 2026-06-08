---
name: saas-outreach
description: Manage the SaaS video outreach pipeline — discover companies, find YouTube channels, review videos, check against customer list, dub with Synthesia, enrich contacts via AirOps, prepare Reply.io CSVs. Use when working on the SaaS video dubbing outreach campaign.
argument-hint: [step or action, e.g. "check status", "dub approved", "enrich contacts"]
---

# SaaS Video Outreach Pipeline

You are managing a SaaS video outreach pipeline for Synthesia. The goal: find SaaS companies with video content on their YouTube channel, dub a 30-second clip to Spanish using Synthesia, enrich with decision-maker contact emails, and send personalised outreach via Reply.io showing the dubbed sample.

---

## Project Location
```
/Users/george.fakorellis/Desktop/SEO Custom Projects/saas-video-outreach/
```

## First Action — Always Check Status
Before doing anything, read `OUTREACH_STATUS.md` in the project directory to understand current progress, what's been done, and what's pending.

Then run a quick status check:
```python
import json, sqlite3
conn = sqlite3.connect('data/saas_outreach.db')
with open('data/review_decisions.json') as f:
    d = json.load(f)
print(f"DB companies: {conn.execute('SELECT COUNT(*) FROM companies').fetchone()[0]}")
print(f"Approved: {sum(1 for v in d.values() if v.get('status')=='approved')}")
print(f"Rejected: {sum(1 for v in d.values() if v.get('status')=='rejected')}")
print(f"Dubbed: {sum(1 for v in d.values() if v.get('synthesia_share_link'))}")
print(f"Outreached: {sum(1 for v in d.values() if v.get('outreached'))}")
print(f"Need dubbing: {sum(1 for v in d.values() if v.get('status')=='approved' and v.get('selected_video_url') and not v.get('synthesia_share_link'))}")
```

---

## The Full Pipeline

### Step 1: Discover Companies
Companies are scraped from Capterra via Apify and stored in SQLite (`data/saas_outreach.db`). If more are needed:
```bash
python3 pipeline.py discover-capterra --category <category> --limit 50
python3 pipeline.py dedup
```
Categories used: CRM, project management, marketing automation, video conferencing, help desk, HR, accounting, ecommerce, LMS, customer success.

### Step 2: Find YouTube Channels
**Always scrape homepages first** (zero API cost), then use YouTube API only for pulling videos.

#### 2a. Scrape homepages for YouTube channel links
```bash
python3 find_youtube_links.py
```
Looks for social buttons and links to youtube.com/@, /channel/, /c/, /user/ on the company homepage. Found 525 channels from 1,544 companies this way.

#### 2b. Pull recent videos from found channels
```bash
python3 pull_channel_videos.py              # All channels
python3 pull_channel_videos.py --limit 100  # First 100
```
Uses YouTube API (check quota first!). Resolves handles to channel IDs, gets uploads playlist, pulls up to 5 recent videos per channel.

**YouTube API quota**: 10,000 units/day. Resets at midnight Pacific.
- Search endpoint (channel ID resolution): 100 units each
- channels().list: 1 unit per batch of 50
- playlistItems().list: 1 unit each

Test quota:
```python
from googleapiclient.discovery import build as yt_build
from utils import load_config
config = load_config()
youtube = yt_build('youtube', 'v3', developerKey=config['youtube_api_key'])
youtube.search().list(q='test', type='channel', part='snippet', maxResults=1).execute()
```

### Step 3: Review Companies (Web App)
```bash
python3 review_websites.py --port 8889
```
- **Review tab**: Shows companies with their YouTube videos embedded. Approve or reject. Select which video to dub. Set trim start/end (default 0:00–0:30).
- **Dashboard tab**: All approved companies with dubbed videos, contacts, outreach checkboxes.
- Edit domain with ✎ button if website URL is wrong.
- Decisions saved in `data/review_decisions.json`.
- DB companies filtered: DR 20–85, traffic < 500K, must have YouTube channel (`has_youtube_channel = 1`).
- Already reviewed companies (in review_decisions.json) never appear again.

### Step 4: Customer Dedup (CRITICAL — always do before dubbing)
Cross-reference ALL approved companies against `data/Customers.csv` (24,971 records, 8,477 unique email domains in the `Email Domain` column).

Check by:
1. **Exact domain match** against Email Domain column
2. **Root domain match** (e.g., company.ca vs company.com — strip TLD and compare)
3. **Company name match** against Clean Parent Name column (be careful of false positives on short/generic names like "Count", "Bridge", "Bold")

Block confirmed customers:
```python
decisions[domain]['status'] = 'rejected'
decisions[domain]['block_reason'] = 'existing_customer'
```

### Step 5: Dub Videos with Synthesia
```bash
python3 batch_dub.py              # Dub all approved without Synthesia links
python3 batch_dub.py --dry-run    # Preview
python3 batch_dub.py --limit 5    # Only first 5
```
Process: download video → trim to specified range → upload to Synthesia → dub to Spanish with lip sync → poll for completion → set visibility public → save share link + GIF URL.

**GIF URL pattern**: `https://synthesia-ttv-data.s3.amazonaws.com/video_data/{asset_id}/transfers/rendered_video.gif`

After dubbing, always backfill any missing GIF URLs:
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

### Step 6: Enrich Contacts via AirOps MCP
**Use AirOps MCP tools directly — do NOT upload CSVs manually.**

1. Gather approved companies with Synthesia links but no contacts yet
2. Write to AirOps grid using `mcp__airops__write_grid`:
   - **Grid ID: 60558**, **Table ID: 78167**
   - Mode: `create`
   - Columns: Company Name, Domain, Website, Category, Domain Rating, Organic Traffic, Organic Keywords, Selected Video URL, Video Source, Dubbed To, Synthesia Share Link, Synthesia GIF URL, Trim Start, Trim End, Outreached
3. The "Simple Email Extraction - George" power agent runs automatically
4. Outputs up to 3 contacts: First Name, Last Name, Email, Position
5. User downloads the enriched CSV from AirOps UI

**Before writing rows, check which domains already exist in the grid to avoid duplicates.**

### Step 7: Prepare Reply.io CSV
The final CSV for Reply.io upload needs:
- Company Name, Domain, Website
- Contact First Name, Contact Last Name, Contact Email, Contact Job Title
- Selected Video URL, Synthesia Share Link, Synthesia GIF URL
- Domain Rating, Organic Traffic

### Step 8: Mark as Outreached
After the user sends via Reply.io, mark companies:
```python
decisions[domain]['outreached'] = True
```

---

## Key Rules

1. **NEVER outreach to existing Synthesia customers** — always check Customers.csv before dubbing
2. **Approved/rejected companies must not reappear** — review_decisions.json is the source of truth
3. **Homepage scraping before YouTube API** — saves quota
4. **Always save both Synthesia share link AND GIF URL** — both needed for Reply.io emails
5. **Filter review app**: DR 20–85, traffic < 500K, YouTube channel confirmed. No giant companies.
6. **Check for duplicate domains** before writing to AirOps grid
7. **Clean up downloaded videos** — batch_dub.py handles this automatically

---

## Key Files

| File | Purpose |
|------|---------|
| `OUTREACH_STATUS.md` | Progress tracker — read this first |
| `data/saas_outreach.db` | SQLite DB: companies, videos, contacts |
| `data/review_decisions.json` | Approve/reject, Synthesia links, outreach status |
| `data/Customers.csv` | Customer list for dedup (24,971 records) |
| `data/airops_email_enrichment.csv` | AirOps enrichment results |
| `data/saas_300_outreach_ready.csv` | Original 300-company curated list |
| `find_youtube_links.py` | Homepage scraper for YouTube channel links |
| `pull_channel_videos.py` | Pull videos from YouTube channels |
| `review_websites.py` | Web review app (port 8889) |
| `batch_dub.py` | Synthesia batch dubbing |
| `pipeline.py` | CLI orchestrator |

---

## Troubleshooting

- **YouTube quota exceeded**: Wait until midnight Pacific. Use `find_youtube_links.py` (zero cost) instead.
- **Video download failed**: Video may be unavailable/private. Select a different video in the review app.
- **Moderation failed** on Synthesia: Video content was flagged. Skip and select different video.
- **Website iframe not loading**: Most sites block iframes via X-Frame-Options. Use "Visit Website" button instead.
- **Wrong domain on a company**: Use the ✎ button in the review app to fix it.
