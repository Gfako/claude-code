---
name: guest-post
description: End-to-end autonomous guest-post production for any article (listicle, how-to, opinion, case study, comparison, etc.). Takes a Notion entry URL and produces a humanized Google Doc with the required links inserted, plus a Notion update. The article's structure follows the host's guidance on the Notion page — not a hardcoded template. Self-iterates the humanize/score loop and conditionally runs pricing, keyword, and section-balance gates depending on whether the entry calls for them.
---

# Guest Post — autonomous production

Single command. Runbook lives at `/Users/george.fakorellis/Desktop/SEO Custom Projects/guest-posts/WORKFLOW.md` — read it first if anything below is ambiguous, then proceed without asking.

The skill handles **any guest post**, not just listicles. Structure, length, voice, and constraints all come from the Notion entry's guidance (host brief, required links, Clearscope targets if present, examples, tone requirements). Listicle rules apply only when the brief calls for a listicle.

## Input

`{notion-entry-url-or-id}` — a row in the Synthesia Guest Posts DB (collection `373c16d2-2bf1-81ee-a093-000bd006743e`). Extract the trailing 32-char ID from URLs.

## How to run

Run the steps in order. Each step's gate is either **always-on** (humanize + AI score, Doc creation, Notion update) or **conditional** (pricing, keyword, section balance — only when the entry calls for them). Verifier scripts return exit 0 on pass / 1 on fail — re-edit and re-run until they pass, max 3 cycles per gate. Hit the cap → **stop and tell the user exactly what's blocking** — do not ship.

All paths assume working directory `/Users/george.fakorellis/Desktop/SEO Custom Projects/`.

### Step 0 — Init
1. Fetch the Notion entry via `notion-fetch`.
2. Derive `slug` from the topic (lowercase, hyphen-separated).
3. `mkdir -p guest-posts/<slug>`.
4. Save raw entry JSON to `guest-posts/<slug>/00-notion-entry.json`.
5. Extract from the entry — write each only if the data is present:
   - **Always:** required link list → `required-links.json` as `[{"url", "anchor", "section_hint"}, ...]`. Even if the entry has just one link, save the file.
   - **Always:** any text/structural guidance from the host → `guidance.md`. If the host provided example articles, brief docs, or constraints (word count, tone, sections), capture all of them.
   - **Optional:** Clearscope keyword table → `keyword-targets.json` as `[{"keyword", "target"}, ...]`. **Only write the file if Clearscope targets are present in the entry.** If absent, do not run the keyword-frequency gate later.
   - **Optional:** detected article type → `meta.json` with `{"article_type": "listicle|howto|opinion|case-study|comparison|foundational|other", "has_pricing": bool, "has_tool_mentions": bool}`. Derive from the guidance and the topic. If unclear, default to `"other"`.

### Step 1 — Brief
- Invoke `/content-brief-simplified` for the target keyword/topic from the entry.
- Feed it the Notion guidance, Clearscope keywords (if any), required-link list, and host examples so it does not re-ask.
- Save to `guest-posts/<slug>/00-brief.md`.
- Post the brief content under the article's Notion page.

The brief, plus `guidance.md`, is the source of truth for Step 2's structure.

### Step 2 — Draft

Write `guest-posts/<slug>/01-draft.md`. **Structure is dictated by `00-brief.md` + `guidance.md`, not by a hardcoded template.**

Always-on draft rules:
- Length target: hit whatever the host or brief specifies. If unspecified, default to 2,400–2,600 words pre-humanize (≈ 3,000–3,200 post-humanize at PhD/High's ~28% expansion).
- First-person practitioner voice — sprinkle "I", "In my experience", "Honestly, I…" through the article. Avoid pure analyst voice. Aim for ~8 first-person moments per 2,500 words.
- **No hyperlinks in the draft.** Links go in only at Step 6 — humanizers mangle markdown links.

Type-specific rules — apply only when the brief calls for that type:

- **Listicle (`article_type == "listicle"`):**
  - Comparison table near the top with columns `# | Tool | Category | Starting price | Best for`.
  - Category H2s grouping numbered tool H3s.
  - "What is <topic>?" body H2.
  - 100–180 words per tool H3.
- **How-to:**
  - Numbered steps as H2s (or H3s under a single H2).
  - Each step ends with a concrete outcome ("you should now see X").
  - Optional "Common mistakes" section at the end.
- **Opinion / thought-leadership:**
  - Strong thesis in the first paragraph.
  - Body builds the argument through 3–5 H2 sections.
  - Closing call-to-action or implication.
- **Case study:**
  - Situation → action → result structure.
  - Real numbers/quotes from the source where available.
- **Comparison (X vs Y):**
  - Comparison table at top.
  - Side-by-side analysis under H2s like "Pricing", "Onboarding", "Best for", "Edge cases".
- **Foundational ("What is X" / "Complete guide to X"):**
  - Definition → use cases → workflow → pitfalls → tools/resources structure.

If none of the above fits, follow whatever heading structure the brief proposes — don't force a template.

After writing the draft:
- **Always:** save it. Then proceed to humanize.
- **If `keyword-targets.json` exists:** run `python3 guest-posts/scripts/keyword_check.py guest-posts/<slug>/01-draft.md guest-posts/<slug>/keyword-targets.json`. If MISS, lightly edit and re-run. Cap: 3 cycles.
- **If `meta.json` says `article_type == "listicle"`:** run `python3 guest-posts/scripts/section_balance.py guest-posts/<slug>/01-draft.md --tools-only`. If imbalanced, expand inline. Cap: 3 cycles. For non-listicle articles, balance is whatever the structure calls for — don't run this gate.

### Step 3+4 — Humanize + AI score loop (always)
- Run `python3 humanize_pipeline.py guest-posts/<slug>/01-draft.md`. The pipeline retries up to 3x against ZeroGPT ≤ 30%, but it scores raw markdown.
- After it finishes, **also run** `python3 guest-posts/scripts/score_ai.py guest-posts/<slug>/02-humanized-final.md --threshold 30` — strips markdown bold and re-scores. If FAIL, re-humanize from the **original draft** (not the previous humanized output — fresh RNG draws).

### Step 5 — Pricing verification (conditional)

Run only if `meta.json` says `has_pricing == true` OR the draft mentions any tool from `scripts/tools_registry.json`.

1. `python3 guest-posts/scripts/verify_pricing.py guest-posts/<slug>/02-humanized-final.md` — prints the pricing URLs to scrape.
2. Push them to AirOps grid 61652 (Table 79641) via `write_grid`. Tell the operator: *"I've added N pricing URLs to AirOps grid 'Content Brief Automation w Claude / Firecrawl Scrape'. Trigger Firecrawl on the new rows, then say 'ready'."* — wait for them.
3. `read_grid` to pull scraped markdown back; write each row's markdown to `guest-posts/<slug>/cached/<tool-slug>.md`.
4. `python3 guest-posts/scripts/verify_pricing.py guest-posts/<slug>/02-humanized-final.md --offline --scraped-dir guest-posts/<slug>/cached`.
5. For each stale tool, auto-fix the body **and** any comparison table together. Save as `02b-pricing-fixed.md`. Re-run keyword check + (if listicle) section balance against this file.

If the article doesn't mention pricing, skip this step entirely — go straight from Step 4 to Step 6.

### Step 6 — Link insertion (always — but only the links from `required-links.json`)

Open `required-links.json`. For each entry, find the natural anchor in the article (use `anchor` + `section_hint` to locate) and convert that text to a markdown link `[anchor](url)`. Save as `guest-posts/<slug>/03-with-links.md`.

If `required-links.json` is empty, save the post-humanize file as `03-with-links.md` unchanged.

Re-run `score_ai.py` on this file — links shouldn't change the score, but verify.

### Step 7 — Google Doc
`python3 guest-posts/scripts/doc_roundtrip.py create "<Topic> — Guest Post Final" guest-posts/<slug>/03-with-links.md`. Capture `doc_id` and `webViewLink`.

### Step 8 — Notion update
Append `Google Doc: <webViewLink>` as a block on the Notion entry. Update Status property to "Draft ready" (or the next status in the DB workflow).

### Step 9 — Final report
Print one summary back:

```
Article:      <topic>
Type:         <article_type>
Words:        <count>
AI score:     <%> (rendered, post strip)
Keywords:     <X/Y on target>     # if keyword targets present
Pricing:      <N tools verified>  # if pricing run
Doc:          <webViewLink>
Notion:       <notion-url> (status set to Draft ready)
```

## Hard rules

- Do not skip Step 1 (brief) — the brief consolidates Notion guidance with fresh SERP/keyword data.
- Do not score AI on raw markdown — always strip first via `score_ai.py`.
- Re-feed the original draft on each humanize retry, never the previous humanized output.
- If the article has a comparison table, table prices and body prices MUST agree — fix both when updating either.
- Never overwrite the user's edits in the Google Doc — `doc_roundtrip.py pull` + auto-snapshot before any post-publish edit.
- Markdown upload only to Drive (HTML breaks fonts).
- Stop on real blockers (auth missing, StealthGPT plateau, scraping fails). Don't fake success.
- **Don't force a listicle structure on a non-listicle article.** Structure follows the brief + Notion guidance.
- **Don't run the keyword gate if there are no Clearscope targets.**

## When a tool is removed mid-pipeline (listicles only)

See WORKFLOW.md "When the user removes a tool mid-process" — covers title count, table row removal, renumbering, mention sweep, and keyword re-check.

## Continuation behavior

If `<slug>/` already exists, **resume** from the first missing output:
- `00-brief.md` → Step 1 done
- `01-draft.md` → Step 2 done
- `02-humanized-final.md` → Steps 3–4 done
- `02b-pricing-fixed.md` → Step 5 done (only if pricing was applicable)
- `03-with-links.md` → Step 6 done
- A Google Doc ID present in `00-notion-entry.json` → Step 7 done
