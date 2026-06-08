# SaaS Video Outreach — Status & Progress

Last updated: 2026-03-25

## Pipeline Summary

We discover SaaS companies, find videos on their websites/YouTube channels, dub them to Spanish using Synthesia, enrich with contact emails via AirOps/Hunter, and send outreach via Reply.io.

## Current Numbers

| Stage | Count |
|-------|-------|
| Total companies in DB | 3,139 |
| Discovered (not yet video-checked) | 1,528 |
| Video-checked | 1,611 |
| Have YouTube channel | 584 |
| Total videos in DB | 5,710 |
| Reviewed: Approved | 136 |
| Reviewed: Rejected | 182 |
| Dubbed to Spanish (Synthesia) | 111 (+21 in progress) |
| Enriched with contact email | 23 |
| Marked as outreached | 123 |

## What We've Done

### Discovery
- Scraped **10 Capterra categories** via Apify: CRM, project management, marketing automation, video conferencing, help desk, HR, accounting, ecommerce, LMS, customer success
- Deduplicated across sources → 3,139 unique companies

### Video Detection
- **YouTube API detection**: Ran on ~1,200 companies, found 55 channels (hit quota limits)
- **Homepage scraping** (2026-03-25): Scraped 1,544 homepages for YouTube channel links → found **525 channels**
- **YouTube video pull**: Pulled recent videos for 65 channels. 208 more have channel IDs resolved (waiting for quota). 311 still need ID resolution.
- **Google Video Search** (Serper.dev): Used as fallback for companies without YouTube channels

### Review (review_websites.py on port 8889)
- Two-tab web app: **Review tab** (approve/reject companies + select videos) and **Dashboard tab** (track outreach status)
- 136 approved, 182 rejected so far
- Review decisions stored in `data/review_decisions.json`

### Dubbing (Synthesia)
- Batch dubbing via `batch_dub.py` — downloads video, trims to 30s clip, uploads to Synthesia, dubs to Spanish with lip sync
- 111 companies dubbed, 21 more in progress
- Share links and GIF URLs saved to review_decisions.json

### Contact Enrichment (AirOps + Hunter)
- AirOps grid (ID: 60558, table: 78167) with "Simple Email Extraction" power agent
- Extracts up to 3 contacts per company (first name, last name, email, position)
- Enrichment CSV: `data/airops_email_enrichment.csv`

### Customer Dedup
- Customer file: `data/Customers.csv` (24,971 records, 8,477 unique email domains)
- Cross-referenced all approved companies against full customer list
- Blocked confirmed customers: Earnix, Commusoft, Glytec
- FranConnect flagged as active opportunity

### Outreach (Reply.io)
- 33 contacts outreached so far via Reply.io sequences
- Sequence includes dubbed video share link + GIF
- One reply received (Atomicwork — marked "do not contact")

## Key Files

| File | Purpose |
|------|---------|
| `data/saas_outreach.db` | SQLite database — companies, videos, contacts |
| `data/review_decisions.json` | Approve/reject decisions, Synthesia links, outreach status |
| `data/Customers.csv` | Synthesia customer list for dedup (24,971 records) |
| `data/airops_email_enrichment.csv` | AirOps enrichment export |
| `data/outreach_final.csv` | First batch outreach export (63 companies) |
| `data/saas_300_outreach_ready.csv` | Original 300-company curated list |

## Contacts Outreached (Reply.io)

### Batch 1 (sent 2026-03-16 to 2026-03-24)
33 contacts across companies including: BigTime, Codat, Condens, Featurespace, Gladia, GreyOrange, Bridge, AgriWebb, Atomicwork, CalAmp, At-Bay, Dragonboat, Flywheel, HawkSoft, Impel, Introhive, Ethena, Artera, BillingPlatform, Fairmarkit, Function Point, Gradient AI, InterGuard, CallProof, Jolt, Jonas Fitness, Anomalo, Drag, Influ2, Hummingbird, ClockShark, Clientpoint, Jungo

### Batch 2 (pending — newly dubbed)
22 companies uploaded to AirOps for Hunter enrichment. 9 found contacts so far.

## Next Steps
1. Wait for Synthesia dubbing to complete (21 videos in progress)
2. Resume YouTube video pull when API quota resets (208 channels ready + 311 need resolution)
3. Run more companies through review app
4. Upload enriched contacts to Reply.io for outreach
5. Continue approving/rejecting companies from the 1,500+ in the pipeline
