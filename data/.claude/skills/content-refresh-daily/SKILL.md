---
name: content-refresh-daily
description: Autonomous daily crawl — pulls 15 URLs from the Synthesia sitemap (blog + alternatives, oldest-not-yet-checked first), extracts volatile claims, verifies them, scores each page, writes one row per page to the "Light Content Updates Suggestions" Notion DB with a detailed findings body, and posts a run summary to #light-content-refreshes. Triggered by cron — no user interaction.
---

# /content-refresh-daily — autonomous daily crawl

This is the cron entry point. Runs without user interaction. Writes findings to Notion + Slack. Does NOT edit any blog content — only flags.

## Project location
`/Users/george.fakorellis/Desktop/SEO Custom Projects/content-refresh/`

## Config
All IDs and settings live in `content-refresh/config.json`:
- `notion.database_id`, `notion.data_source_id`, `notion.database_url`
- `slack.findings_channel_id` (`C0AUZFBGR29` — #light-content-refreshes)
- `slack.changelog_channel_id` (`C029EFJ65NF` — #product-changelog)
- `slack.changelog_lookback_days` (90)
- `urls_per_day` (15)
- `airops.scrape_grid_id` (61652)
- scoring weights, severity thresholds, competitor pricing URLs, AI model terms

---

## Run sequence

### 1. Mark run start

```bash
python3 content-refresh/scripts/crawl_state.py mark-run-start
```

Log the run date (`YYYY-MM-DD`) as the run ID for log files.

### 2. Fetch + filter sitemap

```bash
python3 content-refresh/scripts/sitemap_fetch.py > /tmp/sitemap.json
```

This gives 260+ blog URLs and 10+ alternatives URLs. Note: the sitemap's `lastmod` is site-wide (always the same date) — don't rely on it for change detection. Use content hashing instead.

### 3. Pick today's 15 URLs

```bash
cat /tmp/sitemap.json | python3 -c "import json,sys;d=json.load(sys.stdin);print(json.dumps(d['urls']))" | python3 content-refresh/scripts/crawl_state.py pick-urls --count 15 > /tmp/picks.json
```

Priority: never-checked first, then oldest-last-checked.

### 4. Sync the Synthesia product KB

Two parts to this:

**4a. Pull changelog since last sync.** Read `#product-changelog` (`C029EFJ65NF`) since `kb_last_synced_ts` from `state/crawl_state.json`. If no last-sync timestamp, fall back to last 90 days. Save raw to `/tmp/changelog_new.md`.

```bash
LAST_TS=$(python3 content-refresh/scripts/sync_changelog.py get-last-synced-ts)
# (call mcp__slack__slack_read_channel with oldest=$LAST_TS, channel C029EFJ65NF)
```

**4b. Extract product facts (LLM).** Read `/tmp/changelog_new.md`. For each post:
- SKIP pure A/B variant chatter without a rollout decision, hiring/eng-infra posts, internal logistics
- KEEP concrete user-visible product changes (launches, removals, tier changes, behaviour changes, even minor "you can now rename your video")
- Resolve contradictions: newer post wins. If a Mar 2026 post says "removing PowerPoint-to-video" and a Dec 2025 post said "we shipped PowerPoint-to-video", the entry should be `status: "removed"`.

Output JSON file `/tmp/new_entries.json` with the schema (matches `state/synthesia_kb.json`):
```json
{"entries": [
  {"id": "kebab-case-id", "name": "Human Name", "status": "live|removed|limited|beta",
   "description": "...", "tiers": ["Starter","Creator","Enterprise"]|null,
   "limitations": "..."|null, "source": {"date": "2026-03-15", "author": "..."}, "supersedes": []}
]}
```

**4c. Merge into the KB:**
```bash
cat /tmp/new_entries.json | python3 content-refresh/scripts/sync_changelog.py merge-entries
```
The script handles supersedence (newer source date wins on id-collision). Then mark synced:
```bash
python3 content-refresh/scripts/sync_changelog.py mark-synced <newest_ts_from_this_run>
```

The KB at `state/synthesia_kb.json` is the single source of truth for what Synthesia ships. The verifier (`verify_findings.py`) loads it on import and exposes a `kb_lookup(query)` helper for use in feature-verification.

### 5. Process each of the 15 URLs

For each URL (loop):

**a. Scrape** — via `mcp__firecrawl__firecrawl_scrape` with `formats: ["markdown","html"]`. The AirOps-grid rule is scoped to competitor scraping in content briefs; Firecrawl direct is correct here (Synthesia's own pages). If the scrape fails, skip this URL, log the failure, continue.

**b. Hash the content** — `python3 scripts/crawl_state.py hash < scraped_text.txt`. Compare to prior hash in state. If unchanged AND the URL has been checked before AND its last check was within 30 days, skip all work for this URL (write only `last_checked` update) and continue. This is how we avoid redoing work.

**c. Extract claims — two passes** —

Pass A (regex, deterministic):
```bash
python3 scripts/extract_claims.py < '{"text":"...","html":"..."}'
```
Returns findings with types `pricing`, `feature` (numeric brand specs), `stat`, `link`, `ai-news`. Each finding carries a `location` field (section heading + line number).

Pass B (LLM reasoning): read the scraped markdown and flag **additional potentially-outdated claims regex can't catch**:
- Qualitative brand claims ("X doesn't support Y", "only available on Enterprise")
- Comparative statements ("the only tool that…", "the first to ship…")
- Plan/tier names that may have been renamed
- Technology/model references beyond what the AI-model regex sees
- Company facts (headcount, funding, HQ, CEO/CTO)
- Integration lists
- UI/UX specifics ("click the X button")
- Launch/date claims ("launched in 2022", "coming soon", "new feature")

Add LLM-identified findings with the same schema as regex ones (include `location`, `meta.subtype: "llm_reasoning"`, and `meta.rationale` explaining why flagged). Bias toward flagging — false positives are cheap here.

**d. Reason about Synthesia feature claims using the KB** (`state/synthesia_kb.json`).

The KB is your reference for "what Synthesia currently ships" — built from `#product-changelog` posts and updated daily. **Use it as input for reasoning, not as a lookup oracle.**

How to use it:

1. As you read the article, identify capability claims about Synthesia (positive: "Synthesia can do X", "X is built in"; negative: "Synthesia doesn't support Y", "Y is missing"; conditional: "Z is only on Enterprise").

2. Open the KB and **read the entries** — there are ~80 of them. Skim the names + descriptions to find anything topically related to the claim. The optional helper `kb_lookup(query)` can surface candidate matches by substring, but it's just a filter — entries with different naming may still be relevant. Read whole entries when in doubt.

3. Reason about each claim:
   - Does the KB describe a feature that **directly supports or contradicts** the article's claim? (Beware paraphrasing — "PowerPoint to video" vs "PPT-to-Video Onboarding" describe the same capability.)
   - If contradicted: check the KB entry's `source.date` — is it recent enough that the article author plausibly wouldn't have known? Is there a `supersedes` chain that resolves earlier KB statements?
   - If the KB doesn't mention the capability at all, **don't assume it's wrong** — the changelog only goes back 6 months and doesn't cover everything Synthesia ships. Fall back to checking `synthesia.io/features/*` via WebFetch.

4. Severity:
   - **Confirmed** only when KB unambiguously contradicts the article AND the KB entry is current (no later entry walks it back). Cite the KB entry's id + source date in the suggested fix.
   - **Likely** when there's tension but it's interpretive (e.g., article says "fully launched" but KB says `status: "beta"`).
   - **Unconfirmed** when you can't cleanly map the article claim to a KB entry — let the user check.

5. The verifier exposes `kb_lookup` as a utility, but the actual feature-claim verdict is your reasoning step. Don't write rules like "if status==removed → confirmed". Treat the KB as a knowledgeable but partial colleague you're consulting.

**e. Verify each finding** —
- **pricing**: `WebFetch` each competitor's pricing URL (from `config.competitors`); compare exactly.
- **feature (numeric)**: `WebFetch` the brand's pricing/product page; compare the number. Lower than current → `confirmed`. Same → drop. Can't verify → `unconfirmed`.
- **feature (qualitative / llm-reasoning)**: `WebFetch` brand's features or product page for evidence. If the article says "X doesn't support Y" and the brand now clearly ships Y → `confirmed`. If ambiguous → `likely` with rationale. If no evidence either way → `unconfirmed`.
- **link**: HEAD-check via `curl -sI -o /dev/null -w "%{http_code}" <url> --max-time 10`. Batch in one bash loop. Then classify each (url, code) pair with `python3 scripts/classify_link.py`. Severity rules baked in there: 200=drop · 3xx=likely · 401=likely(auth-wall) · **403/405/999=unconfirmed (bot-blocked, NOT a real error)** · 404=confirmed dead · other 4xx/5xx/000=likely. Do NOT mark 403s as errors — they're nearly always bot-blocking.
- **stat**: ALWAYS `unconfirmed` from the verifier. Stats can stay accurate for years — a survey result doesn't expire just because it's from 2023. Use the LLM-reasoning Pass B to surface the cases that matter (e.g. "best tools in 2023" used as a quality signal in body copy). Don't auto-flag year_refs.
- **title**: dated H1 references >5 months old (e.g. `In 2024`, `[April 2026]` when today is December 2026). Auto-classified by the extractor: >12 months → `confirmed` (must update — kills CTR in SERPs); 5–12 months → `likely`. The verifier preserves the extractor's severity unchanged.
- **ai-news**: `WebSearch` to check if model is superseded; `confirmed` if deprecated, `likely` if a clear newer tier exists.

Assign `severity: confirmed | likely | unconfirmed` + `suggested_fix` + `source` + `source_note` to each finding. Preserve `location` from the extractor in the final payload so the Notion page shows where on the page each finding lives.

**Severity rules — be strict:**
- `confirmed` only when the claim is **clearly, provably false** against a live source. "Probably / likely / appears to be" wrong ≠ confirmed.
- `likely` for strong evidence of staleness that can't be fully proved (monthly rate changed, annual rate not exposed; brand no longer advertises a number prominently).
- `unconfirmed` for unverifiable items (blocked pages, historical facts, dynamic content).

**Title requirement — every finding needs a 3–8 word `title`** describing WHAT is wrong (not what to change). Examples: "Team tier doesn't exist", "Languages count outdated", "Creator duration cap wrong". Not "Pricing" / "Update needed".

Do this verification step efficiently: batch link checks, cache competitor pricing pages within the run (fetch each one only once even if referenced by multiple URLs).

**f. Score**:

```bash
python3 scripts/score.py < '{"findings":[...]}'
```

Returns `score`, `severity`, `types`, `counted_findings`.

**f.5. Compute tags**:

```bash
python3 scripts/compute_tags.py < '{"findings":[...]}'
```

Returns a JSON array of fine-grained tags (`dead-link`, `pricing-tier-removed`, `feature-count-stale`, etc.) for the page row's `Tags` Notion property. Pass this in the result object as `result.tags` so `format_notion_page.py` includes it in the properties dict.

**g. Format the Notion payload**:

```bash
python3 scripts/format_notion_page.py < '<full_result_json>'
```

Returns `properties` dict (now including `Tags`) + `body_markdown`.

**h. Upsert into Notion** —
- Query the DB for an existing row with this URL via `mcp__notion__notion-query-data-sources` (data source ID from config) filtered by `userDefined:URL = <url>`.
- If exists: update via `mcp__notion__notion-update-page` (properties) and replace the page body with new markdown. Don't touch the `Findings page` URL or `Status` column — they're preserved.
- If not: create via `mcp__notion__notion-create-pages` with `parent: {data_source_id: <cfg.notion.data_source_id>}`, the properties, and the body markdown as `content`. Then **immediately** call `mcp__notion__notion-update-page` on the returned `page_id` with `properties: {"Findings page": "<returned page URL>"}`. This populates the clickable-link column so triagers can open the findings page directly from any table view.

Capture the page URL for the Slack summary.

**i. Record state**:

```bash
python3 scripts/crawl_state.py record-result < '<result>'
```

where result includes `url`, `section`, `content_hash`, `findings_count`, `score`, `severity`, `notion_page_id`, `changed`.

### 6. Post Slack run summary

Build the summary object:

```json
{
  "run_date": "2026-04-24",
  "urls_checked": 15,
  "pages_with_findings": <count of pages with severity != Clean>,
  "total_findings": <sum>,
  "notion_database_url": "<cfg.notion.database_url>",
  "results": [...]
}
```

Format:

```bash
python3 scripts/format_slack_summary.py < summary.json
```

Post via `mcp__slack__slack_send_message` to channel `C0AUZFBGR29` (#light-content-refreshes).

### 7. Write the run log

Dump the full run result (all URLs, all findings, all decisions) to `content-refresh/logs/run-YYYY-MM-DD.json`. Also:

```bash
python3 scripts/crawl_state.py mark-run-end
```

### 8. Done

Print a one-line summary to stdout: `"Run {date} complete: {n} URLs, {m} flagged, {k} critical. Notion: {db_url}"`.

---

## Failure handling

- **Individual URL fails to scrape** → skip, log, continue. Don't abort the whole run.
- **Notion write fails** → retry once, then log and continue. The finding is in the log; you can retry manually.
- **Slack post fails** → log and continue. The findings are in Notion regardless.
- **Sitemap fetch fails** → abort with error. Without the sitemap we can't pick URLs.
- **#product-changelog read fails** → continue without feature findings; log the degraded run in Slack summary.

## Safety rails

- NEVER edit any blog content. This skill only **reads** pages and **writes** to Notion/Slack.
- NEVER auto-update the Notion `Status` column — user controls status manually.
- NEVER delete state or logs — only append/overwrite by date.

## Cost/time notes

A full run is ~15 URL scrapes + ~30 WebFetch/WebSearch verification calls + 15 Notion writes + 1 Slack write. Expect 5–15 minutes of runtime.
