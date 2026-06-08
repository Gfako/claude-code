---
name: SaaS outreach process preferences
description: User preferences for how the SaaS video outreach pipeline should be run — scraping approach, customer checks, AirOps usage, dubbing workflow
type: feedback
---

Use homepage scraping before YouTube API to save quota. Scrape for YouTube channel links on the homepage (social buttons, footer links) via `find_youtube_links.py`, then only use YouTube API for pulling videos from found channels.

**Why:** YouTube API has a 10,000 unit/day quota. Homepage scraping found 525 channels from 1,544 companies with zero API cost.

**How to apply:** Always run `find_youtube_links.py` first, then `pull_channel_videos.py` for the discovered channels.

---

Use AirOps MCP tools for Hunter email enrichment — do NOT export/upload CSVs manually. Write directly to grid ID 60558.

**Why:** User prefers the integrated MCP workflow over manual CSV uploads.

**How to apply:** Use `mcp__airops__write_grid` to add companies, let the power agent run, then user downloads the result from AirOps.

---

Always do a comprehensive customer check against ALL 8,477 domains in Customers.csv before dubbing. Check exact domain, root domain, and company name matches.

**Why:** User is very careful about not outreaching to existing Synthesia customers. This is critical.

**How to apply:** Run the dedup check on every batch before dubbing. Block confirmed customers in review_decisions.json.

---

After dubbing, always save both the Synthesia share link AND the GIF URL. The GIF URL follows the pattern: `https://synthesia-ttv-data.s3.amazonaws.com/video_data/{asset_id}/transfers/rendered_video.gif`

**Why:** Both are needed for the Reply.io outreach emails.

---

Filter the review app to only show companies with confirmed YouTube channels, DR 20-85, traffic < 500K. No giant companies (Microsoft, Adobe, etc.).

**Why:** Giant companies are not realistic outreach targets for Synthesia's dubbing service.

---

Mark all approved/rejected companies so they never appear again in the review queue. Track outreach status in review_decisions.json with `outreached: true`.
