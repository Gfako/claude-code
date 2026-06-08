# YouTube Data API - Internal Tool Design Document

## Application Name
SaaS Video Outreach - YouTube Channel Detector

## Purpose
Internal command-line research tool that identifies official YouTube channels of software (SaaS) companies for market research purposes.

## API Services Used
- **YouTube Data API v3** (read-only)

## Endpoints Used

### 1. search.list
- **Purpose:** Find YouTube channels matching a company name
- **Parameters:** `q={company_name}`, `type=channel`, `part=snippet`, `maxResults=5`
- **Usage:** One call per company lookup
- **Quota cost:** 100 units per call

### 2. channels.list
- **Purpose:** Retrieve public channel metadata (subscriber count, video count)
- **Parameters:** `id={channel_id}`, `part=snippet,statistics`
- **Usage:** One call per company lookup (batched when possible)
- **Quota cost:** 1 unit per call

## Data Flow

```
Company Name (from internal database)
        |
        v
search.list (find matching channels)
        |
        v
channels.list (get subscriber count, video count)
        |
        v
Store in local SQLite database:
  - channel_id
  - channel_name
  - channel_url
  - subscriber_count
  - video_count
```

## Data Storage
- All data stored locally in a SQLite database
- No data is shared externally or displayed publicly
- Only publicly available channel metadata is stored

## Usage Pattern
- **Initial batch:** ~3,200 company lookups (one-time)
- **Ongoing:** 10-20 new companies per week
- **Rate limiting:** 0.5 second delay between API calls
- **Peak QPS:** 2 queries per second (maximum)
- **Daily usage after initial batch:** ~500-1,000 units

## Quota Calculation
- Per company: 1 search.list (100 units) + 1 channels.list (1 unit) = 101 units
- Initial batch: 3,200 × 101 = ~323,200 units total
- Requested daily quota: 50,000 units/day
- Estimated days to complete: ~7 days

## What We Do NOT Do
- We do NOT upload any content to YouTube
- We do NOT modify or delete any YouTube data
- We do NOT access private/authenticated user data
- We do NOT display YouTube data publicly
- We do NOT use YouTube Analytics, Reporting, Content ID, or Live Streaming APIs
- We do NOT aggregate or resell YouTube data

## Compliance
- Read-only access to publicly available data
- Compliant with YouTube API Terms of Service
- Internal use only - no public-facing application

## Screenshots
This is a command-line tool with no graphical interface. Sample output:

```
$ python3 detect_youtube.py --limit 5

13:00:01 [INFO] Searching YouTube for 5 companies...
13:00:02 [INFO]   [1] Salesforce → Salesforce (295,000 subs, 4,521 videos)
13:00:03 [INFO]   [2] HubSpot → HubSpot (392,000 subs, 2,891 videos)
13:00:04 [INFO]   [3] Asana → Asana (18,400 subs, 287 videos)
13:00:05 [INFO]   [4] Slack → Slack (65,200 subs, 412 videos)
13:00:06 [INFO]   [5] Notion → Notion (512,000 subs, 198 videos)

YouTube detection complete!
  Checked:  5
  Found:    5
```

## Contact
Internal tool - single user, no external access.
