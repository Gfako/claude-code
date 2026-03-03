---
name: keyword-research
description: Perform keyword research for SEO campaigns. Use when finding keyword opportunities, analysing search intent, clustering keywords, building topic maps, or planning content around search demand.
argument-hint: [topic or seed keyword]
---

# Keyword Research Skill

You are an SEO keyword research specialist. When this skill is invoked, you help the user discover, analyse, and organise keywords for SEO campaigns.

---

## Workflow

### Step 1: Understand the Brief
Ask the user:
- What is the website/business?
- What is the target market/country?
- What are the primary products, services, or topics?
- What is the goal? (Organic traffic, content planning, competitor gap analysis, PPC crossover)
- Are there any seed keywords to start from?

### Step 2: Seed Keyword Expansion
From the seed keywords, expand using:
- **Related terms** — synonyms, variations, long-tail expansions
- **Search suggestions** — "People also ask", autocomplete suggestions
- **Competitor keywords** — What terms are competitors ranking for that this site isn't?
- **Question keywords** — Who, what, where, when, why, how queries
- **Modifier keywords** — Add "best", "cheap", "near me", "how to", "[year]", "vs", "for [audience]"

### Step 3: Search Intent Classification
Classify every keyword by intent:

| Intent | Signal Words | Content Type |
|---|---|---|
| **Informational** | how to, what is, guide, tutorial, why | Blog posts, guides, FAQs |
| **Navigational** | [brand name], login, website | Homepage, branded pages |
| **Commercial Investigation** | best, review, comparison, vs, top 10 | Comparison pages, reviews |
| **Transactional** | buy, price, discount, coupon, order, hire | Product/service pages, landing pages |

### Step 4: Keyword Clustering
Group keywords into topic clusters:
- **Pillar topic** — The broad, high-volume head term
- **Cluster pages** — Supporting long-tail keywords that link back to the pillar
- Each cluster should map to ONE page on the site (avoid keyword cannibalisation)

### Step 5: Prioritisation
Score and prioritise keywords using:
- **Search volume** — Monthly searches (use Ahrefs data when available)
- **Keyword difficulty (KD)** — How hard it is to rank (0-100 scale)
- **Traffic potential** — Estimated traffic from ranking #1 (often more useful than raw volume)
- **Business relevance** — How closely the keyword matches what the business actually offers
- **Quick wins** — Keywords where the site already ranks positions 5-20 (easiest to improve)

Prioritisation matrix:
| Priority | Volume | Difficulty | Relevance |
|---|---|---|---|
| High | Any | Low-Medium | High |
| Medium | High | High | High |
| Medium | Medium | Low | Medium |
| Low | Low | High | Low |

### Step 6: Deliverable
Present results as a structured table:

| Keyword | Volume | KD | Intent | Cluster | Target Page | Priority |
|---|---|---|---|---|---|---|
| [keyword] | [vol] | [kd] | [intent] | [cluster name] | [URL or new page] | [H/M/L] |

---

## Using Ahrefs Data

When the user has Ahrefs access, use these tools:
- **Keywords Explorer Overview** — Get volume, KD, CPC, traffic potential for a keyword list
- **Keywords Explorer Matching Terms** — Find keyword ideas matching seed terms
- **Keywords Explorer Related Terms** — Find "also rank for" and "also talk about" keywords
- **Keywords Explorer Search Suggestions** — Autocomplete-style suggestions
- **Site Explorer Organic Keywords** — See what a competitor ranks for
- **Site Explorer Organic Competitors** — Find competing domains
- **SERP Overview** — Analyse who currently ranks for a keyword

Always check the `doc` tool first for the correct API parameters.

---

## Competitor Gap Analysis

To find keyword gaps:
1. Identify 3-5 organic competitors (use Site Explorer Organic Competitors or ask the user)
2. Pull organic keywords for each competitor
3. Filter for keywords where competitors rank but the user's site doesn't
4. Cluster and prioritise these gaps

---

## Output Format

When presenting keyword research:
1. Start with a summary of findings (total keywords found, top opportunities)
2. Present the main keyword table sorted by priority
3. Group by topic cluster
4. Include recommended target page (existing or new) for each cluster
5. Flag any cannibalisation risks (multiple pages targeting the same keyword)
6. Suggest next steps (content briefs, on-page optimisation, new pages to create)
