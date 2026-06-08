---
name: Always use AirOps grid for scraping
description: NEVER use Firecrawl MCP directly for competitor scraping — always use the AirOps grid workflow (Grid 61652). No exceptions.
type: feedback
originSessionId: 55f1f46c-2318-4cf9-adb0-f2e40405b014
---
NEVER use Firecrawl MCP directly for competitor page scraping in content briefs. Always use the AirOps grid workflow. No exceptions, no fallback.

**Why:** User has confirmed this multiple times (2026-04-06, 2026-04-09, 2026-04-14). The AirOps grid calls Firecrawl through AirOps — that's the correct pipeline. Using Firecrawl MCP directly bypasses the intended workflow.

**How to apply:** Follow the skill steps exactly — clear grid rows, add competitor URLs with `write_grid`, ask the user to trigger the workflow, wait for "ready", then read results with `read_grid`. Clean up after. There is no circumstance where Firecrawl MCP should be used directly for scraping competitor pages.
