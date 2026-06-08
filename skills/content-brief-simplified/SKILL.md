---
name: content-brief-simplified
description: Generate a concise, skimmable content brief optimised for quick writing workflows.
---

# Content Brief Generator (Simplified)

Generate a concise, skimmable content brief. Same data collection as `/content-brief` but the output is shorter, sharper, and optimised for a writer to read in under 1 minute and start writing immediately.

**Defaults:** Brand domain = `synthesia.io` | Country = `us` | Date = today's date

---

## Phase 1: Input Gathering

Ask the user the following (use AskUserQuestion):

1. **Target keyword** — the primary keyword this brief is for
2. **Existing page URL** — is this a content update? If yes, get the URL
3. **Secondary keywords** — ask: "Do you want to provide secondary keywords or should I discover them automatically?" If they provide them, use those. If auto, discover via the keyword universe profiling.
4. **Target audience** — ask: "Who is the target audience for this post? (Skip if you want me to infer from SERP data)" — allow them to define it or skip.
5. **Brand domain** — confirm default `synthesia.io` or let them override
6. **Country** — confirm default `us` or override

---

## Data Collection

Use the EXACT same data collection pipeline as `/content-brief`:
- **Phase 2:** GSC history — page-level trend (last 16 months), query breadth (30d vs 3mo ago), per-keyword deltas for top keywords
- **Phase 3:** Parallel agents (keyword universe profiling, AEO prompts, off-page/backlinks)
- **Phase 4:** Competitor content scraping via AirOps grid (Grid ID 61652, Table ID 79641)
- **Phase 5:** Internal linking (Ahrefs top-pages inventory, only verified URLs)

### GSC data to collect:
- **Page-level trend:** Monthly clicks + impressions for the last 16 months
- **Comparison snapshot:** Last 3 months TOTALS (clicks, impressions, queries) vs previous 3 months TOTALS — page level
- **Per-keyword snapshot:** For the top 5-8 important keywords, show last 3 months vs previous 3 months (clicks, impressions, CTR, avg position) — keep it simple, one line per keyword with the delta

All the same rules apply:
- Verify volumes with `keywords-explorer-overview`
- Distinguish organic vs AI Overview positions (`best_position_kind`)
- Use JSON `where` syntax for Ahrefs filters
- Ahrefs MCP caps at 25 rows — query /post/, /features/, /tools/ separately
- Never assume a page exists for internal linking
- Link keywords to Ahrefs, pages to actual URLs

### Competitor scraping (AirOps grid — IMPORTANT)

Scrape competitor pages via the AirOps grid, NOT Firecrawl MCP directly.

**Grid:** "Content Brief Automation w Claude / Firecrawl Scrape" — Grid ID: 61652, Table ID: 79641, URL column: 949782, Markdown column: 949802

**Steps:**
1. Clear any existing rows (update URLs to blank)
2. Add competitor URLs using `write_grid` with mode "create"
3. **Ask the user to trigger the workflow.** Say exactly:
   > "I've added X URLs to the AirOps grid. Please go to AirOps, open the grid 'Content Brief Automation w Claude / Firecrawl Scrape', select the new rows, and click Run on the Firecrawl Page Scrape column. Tell me 'ready' when done (~30 seconds)."
4. **Wait for the user to say "ready"** — do NOT poll, do NOT fall back to Firecrawl MCP
5. Read the Markdown output using `read_grid`
6. Extract heading structures, word counts, strengths/weaknesses from the content
7. Clear the grid after reading (blank out URLs)

---

## Output Format

Push directly to Notion under "Synthesia Blog Content Briefs" (page ID: `317c16d2-2bf1-801d-b16a-e1a0a7721c40`), add mention under "Claude Briefs" heading. Also save markdown locally to `content-briefs/`.

**The brief must be skimmable in under 1 minute. Use bullets everywhere. No long paragraphs. Every sentence must add information — no filler.**

```markdown
# Content Brief: <Topic>

**Page:** [url](url)
**Date:** <today>
**Audience:** <target audience — either user-provided or inferred from SERP data>

---

## 📋 TL;DR

- **Post type:** New / Refresh
- **Intent:** Foundational / Utility
- **Primary keyword:** [keyword](ahrefs-url) (volume/mo, KD X)
- **Secondary keywords:** [kw1](url) (vol), [kw2](url) (vol), [kw3](url) (vol) — max 5
- **Core intent:** <1 sentence — what problem is the reader trying to solve?>
- **Onward intents:** <1-2 lines — what will they want to do next?>
- **Main issue or opportunity:** <1 sentence>
- **Top actions:**
  1. <action>
  2. <action>
  3. <action>

---

## 🚨 Core Pain Points

<3-5 bullets. These are NOT page assessment issues. These are the REAL pain points the target audience has — extracted from what ranking pages address, what questions PAA/AEO show, and what gaps exist in the SERP.>

<For refresh posts: what pain points are competitors addressing that we're not? What questions are being asked that our page doesn't answer?>
<For new posts: what pain points exist in this space that no one addresses well?>

- Pain point 1 (the reader's problem, not a page flaw)
- Pain point 2
- Pain point 3

---

## ⚡ Why This Matters

<Brief bullets on impact. Focus on:>

- **Performance:** <traffic/CTR/ranking impact>
- **Clarity:** <structural or readability issues>
- **Differentiation:** <generic vs distinctive>
- **Enterprise relevance:** <real-world applicability>
- **Moat opportunity:** <specific suggestions for unique data, research, or commentary that Synthesia could include that competitors wouldn't be able to replicate. E.g., proprietary customer data, internal benchmarks, product-specific workflows, enterprise case studies with named customers.>

---

## 🔧 Recommended Changes

- **Structure:** <bullet(s)>
- **Content:** <bullet(s)>
- **Positioning:** <bullet(s)>

<Each recommendation must map directly to a pain point above.>

### 📐 Suggested Structure

<Suggest a heading structure (H2s and H3s) based on:>
<1. Important entities and keywords from Ahrefs (keywords-explorer-related-terms "also_talk_about" + keyword gaps from competitor profiling)>
<2. What the top 3 competitors cover — ensure every important topic they address is included>
<3. At least 1-2 sections that competitors DON'T cover — this is the differentiation angle>

<For each heading, note WHY it's included:>

- H2: **Heading** — <covers keyword X (vol) + competitors 1,2,3 all have this>
    - H3: Sub-heading — <addresses entity Y from "also talk about">
    - H3: Sub-heading
- H2: **Heading** — <gap: no competitor covers this but audience needs it>
- H2: **Heading** — <covers must-have topic from competitor analysis>
    - H3: Sub-heading
    - H3: Sub-heading

<Mark each heading as one of:>
<🟢 Must-have — all/most competitors cover this>
<🟡 Should-have — some competitors cover, adds depth>
<🔵 New angle — competitors don't cover, our differentiator>

---

## 🏷️ SEO Title & Meta Description

<Critique the current SEO title and meta description (if refresh). Suggest improvements.>

**Current title:** <current title if refresh, or "New post" if new>
**Current meta:** <current meta if available>

**Suggested title:** <proposed title — aware of target keyword placement and ~55-60 char length>
**Suggested meta:** <proposed meta description — includes target keyword, compelling, ~150-155 chars>

<Brief rationale — why this title/meta will perform better.>

---

## 🎯 Core Framing

- **Topic:** <what the post is about>
- **Underlying problem:** <the real problem the reader is trying to solve>
- **Reader intent:** <what they need from this content>

---

## 📝 Content Direction

<Key sections or angles to cover. Light guidance, not a rigid outline.>

- Angle 1
- Angle 2
- Angle 3

<Adjust based on intent:>
- Utility → comparison, decision support, actionable steps
- Foundational → argument, system, implications

---

## 💡 Differentiation Opportunities

- Where the post can go deeper or be more useful than competitors
- Where to add real-world insight (workflows, tradeoffs, constraints)
- Where to strengthen point of view

---

## ❓ FAQ Suggestions

<Suggest 5-8 FAQs based on:>
<1. PAA questions from the SERP>
<2. AEO prompts with high volume>
<3. Questions the target audience would realistically ask based on the topic>

<For each FAQ, note the source (PAA, AEO, or inferred from audience):>

- **Q:** <question> *(source: PAA / AEO / audience inference)*
- **Q:** <question> *(source)*
- **Q:** <question> *(source)*

---

## 🌐 SERP Analysis

<Top 3 organic pages (skip AIO, PAA, Reddit, YouTube). For each:>

### [page-title](url) — Brand (#X for "keyword")

- H2: **Heading**
    - H3: Sub-heading
    - H3: Sub-heading
- H2: **Heading**

**Strengths:** <1 line>
**Weaknesses:** <1 line>

---

## 📎 Related Posts

<All verified via Ahrefs. Link to actual URLs.>

**Directly relevant:**
- [page](url) (Xk traffic) — <why it's relevant>

**Broader context:**
- [page](url) (X traffic) — <why>

---

## 📊 Supporting Detail

### 📈 Performance

**Page trend (last 16 months)**
<Monthly clicks + impressions. Keep compact — one line per month.>

**Last 3 months vs previous 3 months**
- Last 3mo: X clicks | Y impressions | Z queries
- Previous 3mo: X clicks | Y impressions | Z queries
- Delta: +/-X% clicks, +/-X% impressions, +/-X% queries

**Key keyword movements**
<Top 5-8 keywords, one line each with delta only:>
- [keyword](ahrefs-url) — <delta>

### 🔗 Off-page
<1-2 lines: is this a link-dependent SERP?>

### 🤖 AEO
<Key prompt mention/citation rates — only the most actionable insights>
```

---

## Rules

1. **Must be skimmable in under 1 minute.** If a section feels long, cut it.
2. **Bullets everywhere.** No paragraphs longer than 2 sentences.
3. **Prioritise clarity over completeness.** Leave out anything that doesn't help the writer.
4. **No generic statements.** Every bullet must be specific to this page and this SERP.
5. **No invented examples or fake "from experience" claims.** Only use real data.
6. **Plain, practical language.** Write like you're briefing a colleague, not writing a report.
7. **Pain points = reader's problems, not page flaws.** Core Pain Points should reflect what the audience struggles with (extracted from SERP, PAA, AEO), not internal content issues. Page assessment issues go in Recommended Changes.
8. **Every recommendation maps to a pain point.** No orphan suggestions.
9. **Supporting Detail is optional.** Only include if it adds something the other sections don't cover.
10. All the data accuracy rules from `/content-brief` apply: verify volumes, distinguish organic vs AI Overview, link everything, never assume pages exist.
11. **Use emojis in section headings.** 📋 TL;DR, 📈 Performance, 🚨 Core Pain Points, ⚡ Why This Matters, 🔧 Recommended Changes, 🏷️ SEO Title & Meta, 🎯 Core Framing, 📝 Content Direction, 💡 Differentiation, ❓ FAQ Suggestions, 🌐 SERP Analysis, 📎 Related Posts, 📊 Supporting Detail, 🔗 Off-page, 🤖 AEO.
12. **Push to Notion automatically.** Create page under "Synthesia Blog Content Briefs" (page ID: `317c16d2-2bf1-801d-b16a-e1a0a7721c40`), add mention under "Claude Briefs" heading. Use Notion-flavored markdown. Keep emojis. Page icon: 📋. Use real newlines, NOT escaped `\n`.
13. **GSC data goes in Supporting Detail > Performance** — show page trend (16 months), 3mo vs previous 3mo comparison, and per-keyword deltas. Keep it easy to read. This is at the bottom, not the top.
14. **Secondary keywords:** If user provides them, use those. If auto-discovery, use the keyword universe profiling to find them. Either way, max 5.
15. **FAQ section is mandatory.** Combine PAA questions, AEO prompts, and audience-inferred questions. 5-8 FAQs total.
