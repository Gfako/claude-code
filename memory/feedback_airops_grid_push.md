---
name: AirOps grid push — use scripts not MCP
description: Never push large datasets to AirOps grids via MCP tool calls — use Python scripts instead to avoid data truncation
type: feedback
---

Never push large datasets (50+ rows) to AirOps grids through MCP tool calls. The MCP parameter size limit forces truncation of fields to fit, which causes missing data in the grid.

**Why:** During the first link outreach campaign, pushing 253 rows via MCP required splitting into many small batches. To fit within parameter limits, fields like URL, Article Topic, and Section Quote were stripped from later batches, leaving ~180 rows with incomplete data. Took hours to fix.

**How to apply:** For any AirOps grid write with more than ~20 rows:
1. Write a Python script that calls the AirOps `write_grid` MCP endpoint or uses the grid API directly
2. Run the script in the background — it handles chunking internally without data loss
3. Never manually truncate fields to fit MCP parameter limits
4. Always verify all rows have complete data after pushing by reading a sample from the middle/end of the grid

Also: when pushing to AirOps, use proper company names (e.g. "Vimeo" not "vimeo.com") and include ALL analysis data (URL, Fit Strength, Outreach Track, Article Topic, Section Quote, Suggested Anchor Text, DR, Synthesia Target URL) in a single push — don't split the data across multiple update passes.
