# Guest Post Workflow (autonomous)

Strict, ordered pipeline for **every guest post** — listicle, how-to, opinion, case study, comparison, foundational, or anything else. Articles are tracked in the Notion database "Synthesia Guest Posts" (collection `373c16d2-2bf1-81ee-a093-000bd006743e`). Each row carries the topic, host, contact, and whatever the host actually provided (guidance, examples, required links, Clearscope keywords, tone notes — vary widely per host).

**Invocation:** `/guest-post <notion-page-url-or-id>` runs the entire pipeline. The skill is autonomous — it doesn't ask the user to confirm intermediate decisions.

**Rule for me (Claude):** Never skip an always-on step. Never invoke this as a chain of separate skills — `/guest-post` runs every step internally. Don't force a template on the article — **structure comes from the Notion entry's guidance + brief**, not from the runbook.

---

## Step 0 — Init

- Resolve the `slug` from the Notion entry topic.
- Create `guest-posts/<slug>/`.
- Save the raw entry JSON to `<slug>/00-notion-entry.json`.
- Extract what's present in the entry — only write the file if the data exists:
  - **Always:** required link list → `required-links.json` (even if 1 link, save the file; if zero, save `[]`).
  - **Always:** host guidance/notes/examples → `guidance.md`. Capture word-count hints, tone rules, example articles, structural requirements, everything the host gave you.
  - **Optional:** Clearscope keywords → `keyword-targets.json`. Only write if Clearscope targets are present. **No Clearscope ≠ failure — just skip the keyword gate later.**
  - **Always:** `meta.json` with `{"article_type", "has_pricing", "has_tool_mentions"}`. Derive `article_type` from the topic + guidance — one of `listicle | howto | opinion | case-study | comparison | foundational | other`. Set `has_pricing` if pricing claims will appear. Default to `"other"` if the type is unclear.

## Step 1 — Brief

Always run, regardless of how much the Notion entry already contains. The brief consolidates host guidance + Clearscope keywords (if any) + required links with **fresh SERP and keyword data**, which the entry doesn't have.

- Invoke `/content-brief-simplified` with the topic from the Notion entry.
- Pass the Notion guidance, keyword list (if any), required-link list, and host examples as input — don't re-ask the user.
- Save to `<slug>/00-brief.md`.
- Post the brief content under the article's Notion page (not the default "Synthesia Blog Content Briefs" folder).

## Step 2 — Draft

**Structure comes from `00-brief.md` + `guidance.md`, not from this runbook.**

Always-on draft rules:
- Length target: honor whatever the host or brief specifies. Default to 2,400–2,600 words pre-humanize (≈ 3,000–3,200 post-humanize) when unspecified.
- First-person practitioner voice — about 8 first-person moments per 2,500 words. Sprinkle "I", "In my experience", "Honestly, I…" through the article. Avoid pure analyst voice.
- **No hyperlinks in the draft.** Links go in only at Step 6 — humanizers mangle markdown links.

Type-specific guidance — apply only when the brief actually calls for that type. **If the brief proposes a different structure, follow the brief.**

| Type | Structural pattern |
|---|---|
| listicle | Comparison table near top (`# / Tool / Category / Starting price / Best for`) → category H2s grouping numbered tool H3s → "What is X?" body H2 → tool sections (100–180 words each) → "How to pick" → "Common mistakes" → FAQs |
| howto | Numbered steps as H2 or H3 → each step ends with a concrete outcome → optional "Common mistakes" → FAQs |
| opinion | Strong thesis para 1 → 3–5 argument H2s → closing implication or CTA |
| case-study | Situation → action → result → optional lessons learned |
| comparison | Comparison table at top → side-by-side H2s (Pricing, Onboarding, Best for, Edge cases) → verdict |
| foundational | Definition → use cases → workflow → pitfalls → tools/resources |
| other | Whatever heading structure the brief proposes |

Save the draft to `<slug>/01-draft.md`. Then apply the conditional gates:

- **If `keyword-targets.json` exists:** `python3 scripts/keyword_check.py 01-draft.md keyword-targets.json`. If MISS, lightly edit. Cap: 3 cycles. **If the file doesn't exist, skip this gate entirely.**
- **If `meta.json` says `article_type == "listicle"`:** `python3 scripts/section_balance.py 01-draft.md --tools-only`. If imbalanced, expand inline. Cap: 3 cycles. **For other article types, balance follows the structure — don't run this gate.**

## Step 3+4 — Humanize + AI score (always)

- Run `humanize_pipeline.py` on the draft. Settings: `tone=PhD`, `mode=High`, `qualityMode=quality`, `model=heavy`, `outputFormat=markdown`. Key at `.credentials/stealthgpt-api-key.txt`.
- The pipeline retries up to 3x against ZeroGPT ≤ 30%, but it scores raw markdown.
- After it finishes, **also run** `python3 scripts/score_ai.py 02-humanized-final.md --threshold 30` — strips markdown bold and re-scores against the rendered prose (what the Doc actually shows).
- If FAIL on the stripped version, re-humanize from the **original draft** (not the previous humanized output — fresh RNG draws).
- After 3 failed attempts, stop and flag.

## Step 5 — Pricing verification (conditional)

Run only if the article mentions pricing (`meta.json.has_pricing == true` or the draft contains any tool from `scripts/tools_registry.json`).

- `python3 scripts/verify_pricing.py 02-humanized-final.md` prints the URLs to scrape.
- Push them to AirOps grid 61652 (Table 79641) via `write_grid`. Tell the operator to trigger Firecrawl, wait for "ready".
- Read scraped markdown back to `<slug>/cached/<tool-slug>.md`.
- `python3 scripts/verify_pricing.py 02-humanized-final.md --offline --scraped-dir <slug>/cached`.
- For each stale price, auto-fix the body AND the comparison table together. Save as `02b-pricing-fixed.md`.
- Re-run keyword check + (if listicle) section balance against the new file.

If pricing isn't applicable, skip the step. Don't create `02b-pricing-fixed.md`.

## Step 6 — Link insertion (always)

- Open `required-links.json`. For each entry, find the natural anchor in the article (use `anchor` + `section_hint`) and convert that text to `[anchor](url)`.
- Save as `<slug>/03-with-links.md`.
- If the file is empty `[]`, copy the latest humanized version to `03-with-links.md` unchanged.
- Re-run `score_ai.py` to confirm links didn't change the score.

## Step 7 — Google Doc

- `python3 scripts/doc_roundtrip.py create "<Topic> — Guest Post Final" <slug>/03-with-links.md`.
- Capture `doc_id` and `webViewLink` into `00-notion-entry.json`.

## Step 8 — Notion update

- Append `Google Doc: <webViewLink>` as a block on the Notion entry.
- Update Status property to "Draft ready" (or the next status in the DB workflow).

## Step 9 — Final report

```
Article:      <topic>
Type:         <article_type>
Words:        <count>
AI score:     <%> (rendered, post strip)
Keywords:     <X/Y on target>     # only printed if targets existed
Pricing:      <N tools verified>  # only printed if pricing run
Doc:          <webViewLink>
Notion:       <notion-url> (status set to Draft ready)
```

---

## File layout per guest post

```
guest-posts/
  <slug>/
    00-notion-entry.json
    00-brief.md
    meta.json
    guidance.md
    required-links.json
    keyword-targets.json        # only if Clearscope was provided
    01-draft.md
    02-humanized-attempt1.md
    02-humanized-attempt2.md
    02-humanized-final.md
    02b-pricing-fixed.md        # only if pricing run
    03-with-links.md
    current-from-doc.md                          # after Step 7 + doc_roundtrip pull
    current-from-doc-baseline-<UTC>.md           # baseline before any post-publish edit
```

---

## Things I must never do

- Jump straight to drafting without running Step 1.
- Add hyperlinks before Step 6.
- Ship without Step 4 passing on the markdown-stripped version.
- Run the keyword gate when there are no Clearscope targets.
- Run the section-balance gate on a non-listicle article.
- Force a listicle structure on a non-listicle article.
- Let table and body pricing diverge — fix both, always.
- Overwrite the user's in-doc edits — pull + snapshot first via `doc_roundtrip.py`.
- HTML upload to Drive — markdown only.
- Score AI on raw markdown — strip `**` first via `score_ai.py`.

## When the user removes a tool mid-process (listicles only)

1. Update the title count.
2. Remove the row from the comparison table.
3. Renumber subsequent table rows and body H3s to be contiguous.
4. Update "the following N tools" / "N choices below" mentions in intro + "What is…" sections.
5. Grep for any remaining mentions of the removed tool and remove them.
6. Re-run keyword check (the removed tool's prose may have carried target keywords).
