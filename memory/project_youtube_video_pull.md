---
name: YouTube video pull - pending work
description: 519 YouTube channels found via homepage scraping; 208 have channel IDs resolved but need video pull, 311 still need ID resolution. Resume when API quota resets.
type: project
---

As of 2026-03-25, we scraped 1,544 company homepages and found 525 YouTube channel links.

**Status:**
- 65 channels: videos already pulled and in DB (ready for review)
- 208 channels: channel ID resolved, need video pull via `playlistItems().list` (cheap API calls)
- 311 channels: still need channel ID resolution (handle/custom URL → channel ID via search API, costs 100 units each)

**Why:** YouTube API quota (10,000 units/day) ran out during channel ID resolution. The search endpoint costs 100 units per call. `playlistItems().list` only costs 1 unit.

**How to apply:**
1. Run `python3 pull_channel_videos.py` in `/Users/george.fakorellis/Desktop/SEO Custom Projects/saas-video-outreach/` — it will skip already-resolved IDs and pull videos for the 208 ready channels first, then resolve remaining 311.
2. After running, restart the review server so new companies appear.
3. The script `find_youtube_links.py` in the same dir does the homepage scraping (already done for all 1,544).
