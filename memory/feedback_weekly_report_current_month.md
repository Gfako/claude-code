---
name: Weekly SEO report — always include current month cohort
description: When generating the weekly SEO report, the cohort LTV summary and chart must include the current calendar month, not stop at the previous complete month.
type: feedback
originSessionId: fcec3d38-6dc9-45fb-a95a-de62dcf76b57
---
When running `/weekly-seo-report`, the cohort LTV summary (text + chart) MUST include the current calendar month even when it's still in formation (e.g. running the report on May 11 → include May 2026 cohort).

**Why:** Surfacing the freshest cohort week-over-week is the whole point of the report — stopping at the previous complete month hides the active cohort's progress. User flagged this on 2026-05-11 when May 2026 cohort (£45k cumulative) was missing from the report.

**How to apply:**
- 1A prompt: "last 6 months including the current (partial) month" (not "last 5 months")
- 1B prompt: "last 8 months including the current (partial) month" (not "last 7 months")
- Cohort text format: the current month uses "(new)" on first appearance and "+£Xk" thereafter
- Chart: include the current-month bar even if it's a small partial column at the right edge
- Skill at `~/.claude/projects/-Users-george-fakorellis-Desktop-SEO-Custom-Projects/skills/weekly-seo-report/SKILL.md` already updated with these notes
