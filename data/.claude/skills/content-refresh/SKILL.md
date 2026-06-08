---
name: content-refresh
description: Single-URL light-refresh. Extracts volatile claims (pricing, stats, dead links, stale AI-model mentions, outdated feature claims vs #product-changelog), verifies each against live sources, scores the page, and posts one row to the "Light Content Updates Suggestions" Notion DB + a summary to #light-content-refreshes. The skill only suggests — the user decides which suggestions to apply.
---

# /content-refresh — single URL, on-demand

Same pipeline as `/content-refresh-daily` but scoped to one URL the user passes in. Use this to re-check a specific page without waiting for the daily crawl to reach it.

The skill **only produces suggestions** — it does NOT apply edits or push to the CMS. The user reviews the Notion row and picks what to change manually.

## Project location
`/Users/george.fakorellis/Desktop/SEO Custom Projects/content-refresh/`

## Config
Read `config.json` for: sitemap URL, competitors, pricing URLs, AI model terms, scoring weights, Notion DB ID, Slack channel IDs, AirOps grid ID.

## Inputs
User passes one URL (must be `/post/*` or `/alternatives/*` under synthesia.io — reject otherwise). If no URL, ask.

---

## Step 1 — Scrape the page

Use **Firecrawl MCP directly** (`mcp__firecrawl__firecrawl_scrape`) with `formats: ["markdown", "html"]`. This skill scrapes Synthesia's own pages — the AirOps-grid-only rule (see `feedback_airops_scrape_grid.md`) is scoped to **competitor scraping in content briefs** and does not apply here.

Capture:
- Rendered markdown (for claim extraction)
- Raw HTML (for link extraction including `href` attributes)
- Page `<title>` (from metadata)

Save both to `content-refresh/drafts/<slug>.original.html` and `.original.md` so we have an audit trail.

**For verifying competitor pricing pages in Step 3,** prefer `WebFetch` (LLM-summarised). Only fall back to `firecrawl_scrape` if WebFetch is blocked/insufficient.

## Step 2 — Extract claims (two passes: regex + LLM reasoning)

**Pass A — regex (deterministic):** pipe the text + HTML through `scripts/extract_claims.py`:

```bash
python3 scripts/extract_claims.py < payload.json
# payload.json: {"text": "...", "html": "..."}
```

Returns findings with types: `pricing`, `feature` (numeric brand specs — avatars, languages, voices, templates, durations, volume limits), `stat`, `link`, `ai-news`. Each finding includes a `location` field with the section heading and line number.

**Pass B — LLM reasoning (judgement):** read the scraped markdown (`drafts/<slug>.original.md`) and identify ADDITIONAL potentially-outdated claims that regex can't catch. Look for:
- **Qualitative brand claims** — "HeyGen doesn't support X", "Synthesia only offers Y on Enterprise", "Veed is limited to Z". These are often outdated after feature launches.
- **Comparative statements** — "X is the only tool that does Y", "the most advanced", "the first to ship Z" — verify against current product landscape.
- **Product/tier names** — tier names change (e.g., "Team" → "Business"); flag any plan names that might have been renamed.
- **Technology references** — specific model names, API versions, SDK versions, framework names beyond what the AI-model regex catches.
- **Company facts** — headcount, funding round size, headquarters, leadership names (CEO/CTO).
- **Integration lists** — "integrates with X, Y, Z" (may now integrate with more or fewer).
- **UI/UX specifics** — "click the X button", "available in the Y menu" — UI changes regularly.
- **Launch/date claims** — "launched in 2022", "coming soon" — both go stale.

For each LLM-identified potentially-outdated claim, add it to the findings list with:
- `type`: pick the best-fitting category (most will be `feature`)
- `text`: the exact quote
- `context`: ~200 chars surrounding
- `location`: {heading: <nearest section>, line: <line number>}
- `meta`: {subtype: "llm_reasoning", rationale: <one sentence on WHY it might be outdated>}
- No `severity` yet — that comes from verification in Step 3.

Bias toward flagging. False positives here are cheap (the user sees them and dismisses); false negatives are expensive (outdated content ships). Aim for 2-5 LLM-identified findings per article on top of the regex ones.

If both passes return zero findings, tell the user the page looks clean and stop.

## Step 3 — Verify each finding

**You (the LLM) verify.** The Python scripts do detection only. Assign each finding a `severity`: `confirmed` (definitely wrong), `likely` (suggestive), or `unconfirmed` (no evidence either way — drop from scoring but still show user).

### Pricing
For each pricing finding, fetch the brand's live pricing page from `config.json → competitors` (or `synthesia_pricing_url` for Synthesia). Use `WebFetch` unless a specific MCP is better. Compare:
- Same tier mentioned in the article? → check number matches.
- No tier named? → check the number exists anywhere on the pricing page.
- Mismatch → severity `confirmed`, suggested fix with exact current number + tier.
- Can't verify (page blocked, paywall) → severity `unconfirmed` with note.

### Links
For each link finding, HEAD-check via `curl -sI -o /dev/null -w "%{http_code}" <url> --max-time 10`. Batch these in one Bash call. Then map each (url, code) to severity via `python3 scripts/classify_link.py` (input: `{"url": "...", "code": "..."}`).

The classifier rules:
- **200** → drop (link works, no finding)
- **3xx** → likely (verify destination)
- **401** → likely (auth-wall)
- **403, 405, 999** → unconfirmed — these are nearly always bot-blocking, NOT broken links. Do not mark as errors.
- **404** → confirmed (real dead link)
- other 4xx, 5xx, 000 → likely (could be transient)
- "&amp;" in URL with 400 → unconfirmed (HTML-entity scrape artifact)

### Stats
Stats stay relevant for years; auto-flagging based on year_ref produces too many false positives. The verifier marks ALL body-level stat findings `unconfirmed`. Use the LLM-reasoning Pass B (Step 2) to surface the cases that genuinely matter:
- "best tools in 2023" used as a quality marker
- "as of 2022, X..." where the article admits being old
- Survey/report findings that have a clearly-newer version

For verifiable claims (`percent`, `multiplier`, `large_count`): WebSearch the original source. Mark `confirmed` only if directly contradicted by a current source.

### Title (dated H1)
Extractor flags H1s containing year or month-year references >5 months old. The verifier promotes based on age:
- >12 months old → `confirmed` (red — dated titles in SERPs lose CTR fast)
- 5–12 months old → `likely`
Extractor short-circuits when a month-year is present, so "November 2025" (5mo) won't double-flag as a bare "2025" reference.

### AI-news
For each model mention, use `WebSearch` to confirm the model is still current. Apply judgement:
- Model is deprecated / replaced by a named successor → `confirmed`, suggest updated model.
- Model is still current but a newer tier exists → `likely`, suggest mentioning the newer one.
- Capability claim tied to an outdated model → `confirmed`.

### Feature (numeric + qualitative)
There are two flavours:

**(a) Numeric feature claims** (from the regex extractor — subtypes `avatars`, `languages`, `voices`, `templates`, `integrations`, `duration_limit`, `volume_per_period`, `videos_per_period`):
- For **Synthesia** numbers: check live pages at `synthesia.io/pricing`, `synthesia.io` homepage, or product pages. Compare exactly.
- For **competitor** numbers: WebFetch their pricing page and/or homepage; compare.
- If the numeric claim is lower than the current offering → `confirmed` outdated (e.g. "125+ avatars" when brand now advertises "180+"). Suggest fix with exact current number.
- If equal → drop.
- If can't verify (page dynamic / blocked) → `unconfirmed` with note.

**(b) Qualitative feature claims** (from LLM reasoning, KB cross-check, or competitor pages):

For Synthesia claims, **reason against the product KB** (`state/synthesia_kb.json`, ~80 entries built from #product-changelog):
- Read the KB entries that look topically related to the claim. The `kb_lookup(query)` helper surfaces substring matches but it's a filter, not an oracle — read entries even if naming is different.
- If the KB unambiguously contradicts the article AND the KB entry is current (not superseded), call it `confirmed` and cite the KB entry's id + source date in the suggested fix.
- If the KB has tension with the article but the situation is interpretive (e.g. article says "fully launched", KB says `beta`), call it `likely`.
- If the KB doesn't address the claim, don't assume the article is wrong — fall back to WebFetch on `synthesia.io/features/*`.

For competitor qualitative claims: WebFetch the competitor's features/product page; reason about whether the capability is now supported. Confirmed only when there's clear evidence on the live page.

For plan-tier claims ("X is Enterprise-only", "Y is on Pro+"): check current pricing/plans pages. If the tier boundary has clearly shifted → `confirmed`.

For launch/date claims ("launched in 2022", "new feature", "coming soon"): older than 18 months and still calling it "new" → `likely`.

The verifier doesn't auto-decide feature severities — those are your reasoning step.

These findings should include a `meta.rationale` field explaining WHY they were flagged (especially for LLM-reasoning ones) so the user can quickly judge relevance.

## Step 4 — Score the page

Pipe the verified findings through `scripts/score.py`:

```bash
python3 scripts/score.py < {"findings": [...]}
```

Returns score (0-100), severity tier, types list, counted_findings.

## Step 5 — Format for Notion

Build the full result object:

```json
{
  "url": "...",
  "title": "...",           // from <title>
  "section": "blog" | "alternatives",
  "score": <int>,
  "severity": "...",
  "findings_count": <int>,  // actionable findings (confirmed+likely)
  "types": ["pricing", ...],
  "last_checked": "YYYY-MM-DD",
  "last_change_detected": "YYYY-MM-DD",  // today on first check
  "findings": [
    {
      "type": "pricing",
      "severity": "confirmed",
      "title": "Team tier doesn't exist",    // REQUIRED — 3-8 word summary of WHAT is false
      "quote": "…",
      "suggested_fix": "…",
      "source": "…",
      "source_note": "…",
      "location": {"heading": "...", "line": 123}
    },
    ...
  ]
}
```

Include ALL findings in the body (confirmed, likely, and unconfirmed) so the user sees what was checked. Unconfirmed findings don't affect the score.

**Severity rules — be strict:**
- `confirmed` only when the claim is **clearly, provably false** against a live source. If you're inferring ("probably", "likely", "appears to"), it's not confirmed.
- `likely` when there's strong evidence of staleness but you can't fully prove it (e.g. monthly rate changed but current annual rate isn't exposed).
- `unconfirmed` when you couldn't verify either way (blocked page, dynamic content, historical facts).

**Title rule — every finding must have one:**
- 3–8 words, describes WHAT is wrong, not what to change
- Good: "Team tier doesn't exist", "Languages count outdated", "Creator video-duration cap wrong"
- Bad: "Pricing", "HeyGen", "Line 435 issue", "Update needed"

Run `scripts/compute_tags.py` first to derive the page-level Tags multi-select (filterable in Notion: dead-link, pricing-tier-removed, feature-count-stale, etc.). Add the result as `result.tags`. Then pipe through `scripts/format_notion_page.py` to get `properties` (with Tags populated) + `body_markdown`.

## Step 6 — Upsert to Notion

Query the `Light Content Updates Suggestions` DB (data source `2ad51d70-d7de-4085-b031-d6089beaa5b4`) for an existing row with `userDefined:URL = <url>` via `mcp__notion__notion-query-data-sources`.

- **If exists:** `mcp__notion__notion-update-page` with the new properties, and replace the page body.
- **If new:** `mcp__notion__notion-create-pages` with `parent: {data_source_id: "2ad51d70-d7de-4085-b031-d6089beaa5b4"}`, the properties, and the markdown body as `content`.

Property names to pass (match the DB schema exactly):
- `Title`, `userDefined:URL`, `Outdatedness score`, `Severity`, `Findings count`,
- `Types` (JSON array as string, e.g. `"[\"pricing\",\"link\"]"`),
- `Status` (always `"New"` on first insert; preserve existing value on update),
- `date:Last checked:start`, `date:Last change detected:start` (ISO dates),
- `Section`.

Capture the returned page URL — you'll need it for the next step.

**Second call: set `Findings page`** — immediately after create, call `mcp__notion__notion-update-page` with the returned `page_id` and `properties: {"Findings page": "<returned page URL>"}`. This gives the row a clickable URL column that opens the findings view directly from any table view. On **update** of an existing row, the `Findings page` is already set; don't touch it.

## Step 7 — Post one-line Slack summary

Build a single-result summary object and format via `scripts/format_slack_summary.py`. Post to channel `C0AUZFBGR29` (#light-content-refreshes) via `mcp__slack__slack_send_message`. Include a note that it's a manual `/content-refresh` run (distinguishes from daily batches).

## Step 8 — Done

Print one line: `"Checked {url}: score {n}/100 ({severity}), {count} findings. Notion: {page_url}"`.

The skill **does not** edit any blog content or push to the CMS. The user reviews the Notion row and decides what to change manually.

---

## Edge cases

- **Page is behind a paywall or requires auth.** Stop after scrape failure, tell the user.
- **URL is not blog or alternatives.** Reject with explanation — this skill targets those two sections.
- **Same finding appears multiple times on a page** (same price mentioned twice). Treat each as its own finding — user may want to accept one and reject another.
- **Article mentions historical pricing intentionally** ("In 2022, Synthesia cost $X"). Heuristic: if the quote context contains a past-tense year, drop to `unconfirmed` and surface the reasoning to the user.
- **Competitor pricing page is JS-rendered.** Firecrawl `firecrawl_scrape` with `formats: ["markdown"]` usually works; if not, note as unconfirmed.

## File layout touched by this skill

- Reads: `config.json`, `state/crawl_state.json` (for prior-check history on the URL, informational)
- Writes: `drafts/<slug>.original.{md,html}`, `drafts/<slug>.updated.{md,html}`, `drafts/<slug>.findings.json`
- Does NOT write to Notion or Slack.
