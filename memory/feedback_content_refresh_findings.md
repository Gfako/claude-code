---
name: content-refresh findings must be strict and titled
description: Only flag as "confirmed" when clearly false against a live source; give every finding a short 3-8 word title explaining WHAT is wrong.
type: feedback
originSessionId: 17d50050-daa6-4718-af24-2dc1a65b0018
---
Every finding the content-refresh system produces (both `/content-refresh` single-URL and `/content-refresh-daily` autonomous) must follow two rules:

**Rule 1 — Strict "confirmed" threshold.**
Only mark a finding as `confirmed` when the claim is **clearly, provably false** against a live source. Inference, "probably wrong", or "appears to be outdated" does not qualify as confirmed.
- `confirmed` = live source directly contradicts the claim (e.g., pricing page says $29, blog says $24 with no matching annual rate available)
- `likely` = strong suggestion of staleness but can't fully prove it (e.g., monthly rate clearly changed; annual rate not publicly exposed)
- `unconfirmed` = can't verify either way (blocked page, dynamic content, historical fact)

**Why:** User flagged a "Creator $29/seat unlimited minutes" finding where I claimed the tier wasn't per-seat and didn't have unlimited minutes. Those were inferences — HeyGen's annual Creator plan *could* be per-seat and *could* allow unlimited total minutes (with a per-video cap). Inference that makes a claim look wrong doesn't make the claim wrong. Reserve `confirmed` for evidence, not vibes.

**Rule 2 — Every finding needs a short title (3–8 words).**
Describes WHAT is wrong, not what to change. Required on every finding payload.
- Good: "Team tier doesn't exist", "Languages count outdated", "Creator duration cap wrong"
- Bad: "Pricing", "Update needed", "HeyGen info", "Line 435 issue"

**Why:** Without titles the Notion row shows "### 1. 🔴 Confirmed" followed by a long quote — user has to read the full finding to know what the issue is. Short titles let triagers scan a Notion page in seconds.

**How to apply:** Every finding emitted to `format_notion_page.py` must include a `title` field. The `format_notion_page.py` script renders it in the H3 header alongside the severity badge. Skills enforce this requirement in their payload-building step.
