---
name: content-brief
description: Generate a full content brief — keyword research, SERP analysis, competitor scraping, off-page, AEO, and recommendations.
---

# Content Brief Generator

You are generating a comprehensive SEO content brief. Follow each phase below in order. The output is a single markdown file saved to `content-briefs/content-brief-<keyword-slug>.md` in the current working directory.

**Defaults:** Brand domain = `synthesia.io` | Country = `us` | Date = today's date

---

## Phase 1: Input Gathering

Ask the user the following (use AskUserQuestion for structured input):

1. **Target keyword(s)** — the primary keyword(s) this brief is for
2. **Existing page URL** — is this a content update? If yes, get the URL
3. **Brand domain** — confirm default `synthesia.io` or let them override
4. **Country** — confirm default `us` or override

Then auto-detect the AirOps Brand Kit:
- Call `list_brand_kits` and find the one matching the brand domain
- Store the `brand_kit_id` for AEO queries
- If AEO is not enabled on the brand kit, note this and skip AEO sections later

---

## Phase 2: GSC History (if existing page URL provided)

Pull Google Search Console data automatically using the service account.

**Service account JSON:** `/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gsc-service-account.json`
**GSC property:** `sc-domain:synthesia.io`

Write and run a Python script that pulls TWO things:

### A. Page-level trend (last 12 months)
Monthly clicks and impressions for the whole page. Do NOT compute average CTR or average position — those are meaningless across thousands of keywords.

### B. Query breadth comparison (last 30 days vs 3 months ago)
Pull ALL queries for the page (rowLimit 25000) for both periods. Count unique queries, total clicks, total impressions for each. This shows whether the page is gaining/losing keyword footprint and whether visibility translates to clicks.

### C. Per-keyword current vs 3 months ago (runs AFTER keyword universe is built)
After Agent A identifies the anchor keywords and gap keywords, query GSC for each one individually. For each keyword, compare the **totals** for the **last 30 days** vs **3 months ago (same 30-day window)**: clicks, impressions, CTR, avg position.

```python
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime, json
from collections import defaultdict

SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
KEY_PATH = '/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gsc-service-account.json'
PROPERTY = 'sc-domain:synthesia.io'
PAGE_URL = '<existing_url>'

creds = service_account.Credentials.from_service_account_file(KEY_PATH, scopes=SCOPES)
service = build('searchconsole', 'v1', credentials=creds)

end_date = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

# --- A. Page-level monthly clicks & impressions (last 12 months) ---
start_date = (datetime.date.today() - datetime.timedelta(days=365)).isoformat()
response = service.searchanalytics().query(
    siteUrl=PROPERTY,
    body={
        'startDate': start_date,
        'endDate': end_date,
        'dimensions': ['date'],
        'dimensionFilterGroups': [{'filters': [{'dimension': 'page', 'expression': PAGE_URL}]}],
        'rowLimit': 25000,
        'type': 'web'
    }
).execute()
# Aggregate daily → monthly, output clicks & impressions per month only

# --- B. Query breadth: current 30d vs 3mo ago 30d ---
current_start = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
compare_start = (datetime.date.today() - datetime.timedelta(days=120)).isoformat()
compare_end = (datetime.date.today() - datetime.timedelta(days=90)).isoformat()

for period_name, s, e in [('current', current_start, end_date), ('3mo_ago', compare_start, compare_end)]:
    resp = service.searchanalytics().query(
        siteUrl=PROPERTY,
        body={
            'startDate': s,
            'endDate': e,
            'dimensions': ['query'],
            'dimensionFilterGroups': [{'filters': [{'dimension': 'page', 'expression': PAGE_URL}]}],
            'rowLimit': 25000,
            'type': 'web'
        }
    ).execute()
    rows = resp.get('rows', [])
    # Count: len(rows) unique queries, sum clicks, sum impressions

# --- C. Per-keyword: current 30d totals vs 3mo ago 30d totals ---
# Run AFTER Agent A identifies the keyword universe.
KEYWORDS = ['<keyword1>', '<keyword2>', '...']  # Fill from Agent A results

for kw in KEYWORDS:
    for period_name, s, e in [('current', current_start, end_date), ('3mo_ago', compare_start, compare_end)]:
        resp = service.searchanalytics().query(
            siteUrl=PROPERTY,
            body={
                'startDate': s,
                'endDate': e,
                'dimensions': ['query'],
                'dimensionFilterGroups': [{'filters': [
                    {'dimension': 'page', 'expression': PAGE_URL},
                    {'dimension': 'query', 'expression': kw}
                ]}],
                'rowLimit': 1,
                'type': 'web'
            }
        ).execute()
        # Output: total clicks, impressions, CTR, avg position for the 30-day period
```

**Important:** Part A runs immediately. Parts B and C run AFTER the keyword universe is built in Phase 3. GSC data is ONLY used in the History section — do not repeat it elsewhere in the brief.

---

## Phase 3: Parallel Data Collection

Launch **3 agents in parallel** to collect data. Pass each agent the target keyword(s), brand domain, country, and date.

### Agent A — Keyword Universe Profiling

This is the most important agent. It builds the realistic keyword universe for the page by analysing what top-ranking competitors actually rank for. A keyword only belongs in the brief if the page ranks top 7 for it OR if SERP competitors rank top 7 for it with the same page type/intent.

Use `mcp__ahrefs__doc` before first use of any unfamiliar tool to check the real schema.

**Step 1: Get the page's anchor keywords (top 7 positions only)**
```
site-explorer-organic-keywords:
  target: <existing_url or brand_domain>
  mode: exact (for existing URL) or subdomains (for domain)
  country: <country>
  date: <today>
  select: keyword,volume,best_position,sum_traffic
  where: {"field":"best_position","is":["lte",7]}
  order_by: sum_traffic:desc
  limit: 40
```

Also pull the GSC top keywords (from Phase 2) filtered to positions ≤7. Cross-reference both sources to identify the page's **anchor keywords** — the 3-5 highest-volume keywords where the page actually ranks well.

**Step 2: SERP the anchor keywords**
For each of the top 3-5 anchor keywords (by volume), get the SERP:
```
serp-overview:
  keyword: <anchor keyword>
  country: <country>
  select: position,url,title,type,traffic,domain_rating,backlinks,refdomains,keywords
  top_positions: 10
```

**Step 3: Identify SERP regulars**
From the SERP results, find the 4-5 non-Reddit organic pages that appear in positions 1-5 across multiple SERPs. These are the pages Google considers authoritative for this topic — the "SERP regulars".

**Step 4: Pull competitor keyword profiles (top 7 only)**
For each SERP regular, get their keyword profile filtered to top 7 positions:
```
site-explorer-organic-keywords:
  target: <competitor_page_url>
  mode: exact
  country: <country>
  date: <today>
  select: keyword,volume,best_position,sum_traffic
  where: {"field":"best_position","is":["lte",7]}
  order_by: sum_traffic:desc
  limit: 40
```

**Step 5: Build the keyword universe**
From all the competitor keyword profiles (top 7 only):
1. **Group keywords into clusters** — e.g., "best ai video generator" variants, "free" variants, "how to" variants, "text to video" variants, branded comparisons
2. **Mark each cluster**: Does Synthesia rank top 7? Do 2+ competitors rank top 7? Is it the same page type (editorial vs product)?
3. **Classify clusters as:**
   - **OUR KEYWORDS** — we rank top 7, or the cluster matches our page intent and 2+ competitors rank for it with similar page types
   - **PRODUCT PAGE TERRITORY** — the cluster is dominated by product/tool pages, not editorial listicles. These should NOT be in the brief for a blog post
   - **GAPS** — competitors rank, we don't, but the intent matches our page type
   - **IRRELEVANT** — branded competitor terms, wrong intent, or outside our page's scope

**Step 6: Also get related keyword opportunities (questions)**
```
keywords-explorer-matching-terms:
  keywords: <target keyword(s)>
  country: <country>
  terms: questions
  select: keyword,volume,difficulty,traffic_potential,intents
  order_by: volume:desc
  limit: 20
```

**Step 7: Cannibalisation check**
Check what other pages on the brand domain rank for keywords in our keyword universe:
```
site-explorer-organic-keywords:
  target: <brand_domain>
  mode: subdomains
  country: <country>
  date: <today>
  select: keyword,volume,best_position,best_position_url,sum_traffic
  where: {"field":"keyword","is":["isubstring","<core term>"]}
  order_by: sum_traffic:desc
  limit: 30
```

**Return:** The full keyword universe with clusters, gap analysis, cannibalisation findings, SERP data, and competitor profiles.

---

### Agent B — AEO & Prompts

Skip this agent entirely if AEO is not enabled on the brand kit.

**Step 1: Find relevant prompts**
```
list_aeo_prompts:
  brand_kit_id: <brand_kit_id>
  filters: { keyword: <target keyword or core term> }
  fields: id,text,keyword,brand_mentioned,mention_rate,citation_rate,topic_id
  sort: prompt_volume:desc
  per_page: 20
```

Try multiple keyword variations if results are sparse (e.g., "video translat", "video translator", "translate video").

**Step 2: Get AI answers for top 5 prompts**
For each of the top 5 prompts by volume:
```
get_prompt_answers:
  prompt_id: <prompt_id>
  providers: chat_gpt,gemini,perplexity,google_ai_overview
  fields: id,text,provider,brand_mentioned,brand_cited
  per_page: 10
```

**Step 3: Citations landscape**
```
list_aeo_citations:
  brand_kit_id: <brand_kit_id>
  filters: { domain_category: Competitors }
  fields: url,citation_count,citation_rate,citation_share,influence_score,domain_name,brand_sentiment
  sort: citation_count:desc
  per_page: 20
```

```
list_aeo_domains:
  brand_kit_id: <brand_kit_id>
  fields: domain_name,domain_category,citation_count,citation_rate,citation_share,url_count
  sort: citation_count:desc
  per_page: 20
```

**Step 4: Trends**
```
query_analytics:
  brand_kit_id: <brand_kit_id>
  metrics: mention_rate,citation_rate,share_of_voice
  dimensions: date
  grain: monthly
  brand_mentioned: category
  start_date: <6 months ago>
  end_date: <yesterday>
```

**Return:** All prompts, AI answers, citation data, and trends.

---

### Agent D — Off-Page / Backlink Analysis

Analyse the brand URL and the top 3-5 SERP competitors. If Agent A hasn't returned yet, get the SERP independently.

For **each** competitor URL + the brand's existing page (if any):

**Step 1: Backlink stats**
```
site-explorer-backlinks-stats:
  target: <url>
  mode: exact
  date: <today>
```

**Step 2: Top referring domains ("best" = high-DR dofollow links)**
```
site-explorer-referring-domains:
  target: <url>
  mode: exact
  select: domain,domain_rating,links_to_target,dofollow_links,traffic_domain,first_seen
  order_by: domain_rating:desc
  where: {"and":[{"field":"domain_rating","is":["gte",50]},{"field":"dofollow_links","is":["gte",1]}]}
  limit: 10
```

**Step 3: Anchor text distribution**
```
site-explorer-anchors:
  target: <url>
  mode: exact
  select: anchor,backlinks,refdomains,dofollow,first_seen
  order_by: refdomains:desc
  limit: 15
```

**Return:** Comparative backlink data for all analysed URLs.

---

## Phase 4: Competitor Content Scraping (via AirOps Grid)

After SERP data is available (from Agent A), scrape the **top 7 organic results** across the main keywords + the existing Synthesia page (even if not ranking top 7). Prioritise pages that appear across multiple keyword SERPs.

**Use the AirOps grid for scraping, NOT the Firecrawl MCP directly.**

Grid: "Content Brief Automation w Claude / Firecrawl Scrape"
- Grid ID: 61652
- Table ID: 79641
- URL column: id 949782
- Markdown output column: id 949802

**Workflow:**
1. **Clear previous data** — read existing rows, update them to blank URLs to clear. If more rows needed than exist, create new rows.
2. **Add URLs** — write the competitor URLs + Synthesia's URL to the URL column using `write_grid` with mode "create"
3. **Ask the user to trigger the workflow** — tell them exactly:
   > "I've added X URLs to the AirOps grid. Please go to AirOps, open the grid 'Content Brief Automation w Claude / Firecrawl Scrape', select the new rows, and click Run on the Firecrawl Page Scrape column. Tell me 'ready' when the Markdown column is populated (~30 seconds)."
4. **Wait for the user to say "ready"** — do NOT poll the grid or proceed until the user confirms. Do NOT fall back to using Firecrawl MCP directly.
5. **Read the Markdown output** — read the full Markdown content for each page from the grid using `read_grid`
6. **Analyse in Claude Code** — extract heading structures, word counts, tools mentioned, CTAs, media types from the markdown content directly
7. **Clear the grid** — after reading all outputs, update all rows back to blank URLs so the grid is clean for next use

**Return:** Content analysis for each competitor page.

---

## Phase 5: Internal Linking

**NEVER assume a page exists. Only recommend pages confirmed via Ahrefs top-pages.**

Two data sources to discover real pages:

**Source 1: Ahrefs top pages** — the MCP caps at 25 rows per query, so run multiple prefix queries to build the full inventory:
```
# Domain-level top pages
site-explorer-top-pages:
  target: <brand_domain>
  mode: subdomains
  date: <today>
  select: url,sum_traffic,top_keyword,top_keyword_volume
  order_by: sum_traffic:desc
  limit: 100

# Then query each content path separately for more coverage
site-explorer-top-pages:
  target: www.<brand_domain>/post/
  mode: prefix
  ...

site-explorer-top-pages:
  target: www.<brand_domain>/features/
  mode: prefix
  ...

site-explorer-top-pages:
  target: www.<brand_domain>/tools/
  mode: prefix
  ...
```
This gives ~100 pages total. Use this as the inventory of EXISTING pages.

**Source 2: Ahrefs organic keywords** — search for related keywords across the domain and see which pages rank:
```
site-explorer-organic-keywords:
  target: <brand_domain>
  mode: subdomains
  country: <country>
  date: <today>
  select: keyword,volume,best_position,best_position_url,sum_traffic
  where: {"or":[{"field":"keyword","is":["isubstring","<term1>"]},{"field":"keyword","is":["isubstring","<term2>"]}]}
  order_by: sum_traffic:desc
  limit: 50
```

Use multiple related terms from the keyword research (5-10 isubstring filters in the OR clause) to cast a wide net.

**For each recommended internal link, include:**
- The confirmed page URL (linked)
- What keyword it ranks for (linked to Ahrefs)
- Its traffic
- WHERE in the new post to link it and WHY

---

## Phase 6: Synthesis & Output

Now compile everything into the final brief. Create the output directory and file:

```bash
mkdir -p content-briefs
```

Write the brief to `content-briefs/content-brief-<keyword-slug>.md`.

**CRITICAL: The brief must follow the EXACT format below.** This is the house style. Do NOT use tables (except in the comparison table within Recommendation). Use bullet lists with inline numbers. Be opinionated and conversational in analysis paragraphs.

---

### Output Template

```markdown
## History

<If no existing page: "New post, no history." and skip to Keywords.>

**Page trend (last 12 months)**

<Monthly clicks and impressions for the whole page. No average CTR or position.>

**Query breadth (last 30 days vs 3 months ago)**

- Now: X unique queries | X total clicks | X total impressions
- 3 months ago: X unique queries | X total clicks | X total impressions

<1 paragraph analysis.>

**Keyword performance (last 30 days vs 3 months ago)**

<For each anchor keyword and key gap keyword, show ONLY the delta/takeaway — not the raw numbers. Link each keyword to Ahrefs.>

- [keyword A](ahrefs-url) — -183 clicks despite stable position
- [keyword B](ahrefs-url) — dropped from pos 3 to pos 7

## Keywords, topics and prompts

### Keywords

<Only include keywords that REALISTICALLY belong to this page. A keyword belongs if:
(a) The page ranks top 7 for it, OR
(b) 2+ SERP competitor pages (same page type/intent) rank top 7 for it

Do NOT include keywords at position 20+. Strikethrough for deprioritised keywords.>

- Keyword A (Xk/month, ranking #X)
- ~~Keyword B (X/month, cannibalised by [other page](url))~~
- Keyword C (X/month, not ranking) — gap: competitors A, B rank top 5

<1-2 paragraphs: keyword clusters, which this page should own, total addressable volume, cannibalisation.>

### Prompts

- Prompt question 1?
- Prompt question 2?

## SERP analysis

<Analyse 3-5 keywords depending on importance. For each, list the top 5 results as linked titles. Keep commentary to 1-2 sentences per keyword.>

[**Keyword phrase**](ahrefs-url) (volume/mo)

1. [Page title](url)
2. [Page title](url)
3. [Page title](url)
4. [Page title](url)
5. [Page title](url)

<1-2 sentences of commentary.>

## Content structure and intent

<Scrape and show heading outlines for the TOP 7 organic results across the main keywords + Synthesia's page (even if not ranking top 7). Prioritise pages that appear across multiple keyword SERPs. Format:>

<url>

- H2: **Heading text**
- H2: **Heading text**
    - H3: Sub-heading text
    - H3: Sub-heading text

<Repeat for each competitor page. Under each, note:
- What they do well
- Where they feel generic or surface-level
- Word count, media types>

### Core intent

<Interpret the core intent of the search queries based on what's ranking. What problem is the user trying to solve? What judgment are they trying to make?>

**Content classification:**
- **Foundational** — exists to shape judgment, define standards, and build trust with enterprise leaders over time (thought leadership). Example: https://www.synthesia.io/post/learning-in-the-flow-of-work
- **Utility** — exists to capture demand, solve immediate tasks, and support discoverability and self-serve exploration (SEO content). Example: https://www.synthesia.io/post/training-videos

<State which classification applies to this post and why.>

**Likely reader problem:** <What the reader is actually trying to figure out — not just "what is X" but "should I use this?", "how do I implement this?", "which tool should I pick?" etc.>

### Onwards intents

<What will the user want to do AFTER they've satisfied the core intent? These shape the CTAs and internal links.>

- Onwards intent 1 (e.g., "try the tool", "compare pricing", "see case studies")
- Onwards intent 2
- Onwards intent 3

### Why top pages rank

<For the top 3-4 ranking pages, explain WHY they perform well. Consider:
- Content approach / intent satisfaction
- Backlink profile strength
- Domain authority + topical authority
- Freshness, structure, media richness>

### Intent gap

<What's missing from the current Synthesia page vs what the SERP rewards? If new content, what's the gap between what competitors cover and what we plan to cover?>

## Audience

Users searching '<target keyword>' are likely:

- Persona 1
- Persona 2
- Persona 3

<Relevant brand insights or reports that should inform the angle.>

## Off-page

- Synthesia: X RDs, Y 'best'
- Competitor A: X RDs, Y 'best'
- Competitor B: X RDs, Y 'best'

<Assessment: link-dependent SERP? Link gap? What should we do?>

## Recommendation

### Subtopics to cover

<List the key subtopics the post must address, based on competitor analysis and gap analysis. For each subtopic, include a "likely reader problem" — the underlying question they're trying to answer.>

- Subtopic 1 — likely reader problem: "..."
- Subtopic 2 — likely reader problem: "..."

### Title recommendation

**Suggested Title Here**

<1-2 sentences explaining the title choice.>

### Assets to include

- Templates
- Screenshots
- Case studies / customer stories
- Videos (embed specific URLs if known)

### 'From experience' insights

<Identify 1-2 places where a practical, real-world insight would strengthen the post. For each:>

1. **Section:** <which section/topic>
   **Type of insight:** <workflow, tradeoff, implementation challenge, bottleneck, constraint>
   **Prompt for writer:** <specific question to guide the writer, e.g., "Describe a real scenario where team X hit constraint Y and how they resolved it">

2. **Section:** ...
   **Type of insight:** ...
   **Prompt for writer:** ...

<"From experience" = practical, real-world insight based on how teams actually work. Avoid generic advice or invented examples.>

## AEO optimisations checklist

<This section must be SPECIFIC to this page. Every bullet should reference actual data from the AEO research — specific prompts, specific providers, specific citation gaps, specific entities. No generic advice.

BAD (too generic): "Include specific entities"
GOOD (page-specific): "Include Synthesia, Google Veo, Sora, Runway in the first 30% — these are the tools most named in AI answers for 'best AI video generator' prompts"

BAD: "Answer relevant prompts"
GOOD: "The prompt 'best AI video generator for business' has 94% mention rate but only 60% citation rate — add a dedicated section with a direct, quotable answer to close the citation gap"

Each bullet = one specific, actionable recommendation tied to data from this brief.>

## Internal linking

<NEVER assume a page exists. Only include URLs confirmed via Ahrefs top-pages or organic-keywords. For each link, explain where in the post to place it and why.>

**Link to these pages from the updated post:**

- [page-url](full-url) — ranks for [keyword](ahrefs-url), X traffic/mo. Link from <specific section> when discussing <specific topic>
- ...

**Link from these pages to the updated post:**

- [page-url](full-url) (X traffic) — add "<suggested anchor text>"
- ...
```

---

## Important Rules

1. **Use `mcp__ahrefs__doc` before first use** of any Ahrefs tool you haven't used before in this conversation, to verify the real parameter schema.
2. **Always verify keyword volumes with `keywords-explorer-overview`** before putting them in the brief. The `site-explorer-organic-keywords` endpoint often returns different (inflated) volume numbers. The brief must use volumes from `keywords-explorer-overview` as the source of truth.
3. **SERP positions: use organic positions only.** The `serp-overview` endpoint returns AI Overview sitelinks, snippets, questions, news, etc. alongside organic results. When reporting "Zapier ranks #X", only count the organic/snippet position, not AI Overview sitelink positions. Each organic position is held by ONE page — never report multiple pages at the same position.
4. **Distinguish organic vs AI Overview in the Keywords section.** When pulling `site-explorer-organic-keywords`, always include the `best_position_kind` field. If a keyword's best_position_kind is `ai_overview` or `ai_overview_sitelink`, report it as "**AI Overview sitelink**" — do NOT call it "ranking #1". Only `organic` or `snippet` positions count as true rankings. This is critical for accuracy.
5. **Add links throughout the brief.** Link every keyword to its Ahrefs keyword explorer page (format: `https://app.ahrefs.com/keywords-explorer/google/us/overview?keyword=<url-encoded-keyword>`). Link every competitor page mention to the actual URL. This makes the brief immediately actionable — the reader can click through to verify any data point.
2. **Monetary values from Ahrefs are in USD cents** — divide by 100 to display in dollars.
3. **Always use `mode: subdomains`** when analysing a domain name in site-explorer tools (not `mode: domain`).
4. **Date format** for Ahrefs: `YYYY-MM-DD`.
5. **Ahrefs `where` uses JSON syntax** — e.g., `{"field":"keyword","is":["isubstring","video translat"]}`. Do NOT use the shorthand `keyword~term` syntax.
6. **Parallelise agents** — launch Agent A, B, and D simultaneously. Agent C (scraping) runs after SERP results are available.
7. **Be opinionated in analysis** — don't just list data. Provide commentary on what the data means, which keywords to target vs ignore, what content gaps exist, and how to differentiate. Write like an experienced SEO strategist giving a recommendation, not a tool dumping data.
8. **Cannibalisation is critical** — always check what the brand already ranks for and flag conflicts.
9. **Strike through keywords** that should NOT be targeted (already covered, wrong intent, too competitive).
10. **The recommendation must be actionable** — a specific title, a full outline, and clear rationale.
11. **NO TABLES in the brief output** — except optionally in the Recommendation section for a comparison table. Use bullet lists with inline data everywhere else. This is the house style.
12. **Keep it concise** — the brief should be scannable. Short paragraphs, bullets, no padding. Every sentence should add information or an opinion.
13. **GSC data is automatic** — always pull it via the service account when an existing URL is provided. Do not ask the user to paste performance data.
14. **GSC data stays in History only** — do NOT reference GSC clicks, impressions, CTR, or positions anywhere else in the brief. The Keywords section uses Ahrefs data (volume, position, difficulty). The SERP section uses Ahrefs SERP data. GSC is for the History section's trend analysis and keyword-level performance comparison only.
15. **Use emojis in section headings.** Every ## heading gets an emoji: 📈 History, 🔍 Keywords, 💬 Prompts, 🌐 SERP analysis, 📑 Content structure, 🎯 Core intent, ➡ Onwards intents, 🏆 Why top pages, ⚠ Intent gap, 👥 Audience, 🔗 Off-page, 💡 Recommendation, 📋 Subtopics, 📦 Assets, 🧠 From experience, 🤖 AEO, 📎 Internal linking.
16. **Push to Notion automatically.** After writing the markdown + docx, create a Notion page under "Synthesia Blog Content Briefs" (page ID: `317c16d2-2bf1-801d-b16a-e1a0a7721c40`) and add a mention under the "Claude Briefs" heading. Use Notion-flavored markdown (fetch spec from `notion://docs/enhanced-markdown-spec`). Keep emojis in headings. Page icon: 📋. Use real newlines in the content string, NOT escaped `\n`.
