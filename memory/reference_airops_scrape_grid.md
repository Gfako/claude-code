---
name: AirOps Firecrawl scrape grid
description: Grid for scraping competitor pages via AirOps Firecrawl workflow. Used by the content-brief skill instead of Firecrawl MCP directly.
type: reference
---

Grid: "Content Brief Automation w Claude / Firecrawl Scrape"
- Grid ID: 61652
- Table ID: 79641
- Columns:
  - URL (id: 949782, text) — input column
  - Firecrawl Page Scrape (id: 949783, app_execution) — triggers the workflow
  - Markdown (id: 949802, app_execution_output) — scraped page content
  - Metadata (id: 949803, app_execution_output) — page metadata

Workflow: Add URLs → workflow auto-scrapes → read Markdown output → clear grid for next use.
Note: AirOps MCP has no delete rows function. Clear by updating rows to blank URLs.
