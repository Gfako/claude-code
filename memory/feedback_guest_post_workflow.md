---
name: feedback-guest-post-workflow
description: "Guest post workflow is autonomous and generalized. /guest-post handles ALL article types (listicle, how-to, opinion, case study, etc.), follows the host's Notion guidance for structure, and runs verifier gates conditionally."
metadata:
  node_type: memory
  type: feedback
  originSessionId: 2ceb16a3-4bab-47a3-93ec-424f848cd865
---

When the user assigns a guest post (typically by pointing me at an entry in the Synthesia Guest Posts Notion DB, collection `373c16d2-2bf1-81ee-a093-000bd006743e`), **invoke the `/guest-post` skill**. That skill is autonomous — it runs every step from brief through Notion update without prompting the user for intermediate decisions.

**Generalized scope (clarified 2026-06-05):** The skill handles ALL guest post types, not just listicles. Structure follows the Notion entry's guidance + brief, not a hardcoded template. Listicle rules apply only when the brief calls for one. Other types covered: how-to, opinion/thought-leadership, case study, comparison (X vs Y), foundational guide, or any other structure the brief specifies.

**Conditional gates (not all entries have all data):**
- Clearscope keyword check — only runs if the Notion entry provided Clearscope targets. **No Clearscope ≠ failure; just skip the gate.**
- Pricing verification — only runs if the article mentions pricing or known tools (`tools_registry.json`).
- Section balance (`--tools-only`) — only runs for listicles. Other article types follow whatever structure the brief calls for.
- Required link insertion always runs but does nothing if `required-links.json` is empty.

**Why:** The user explicitly built this skill to stop having to direct each step (brief → draft → humanize → score → pricing verify → keyword check → section balance → links → Doc → Notion). They want one invocation, end-to-end. They also re-said: "it should know exactly how to craft the next article."

**How to apply:**

1. Invoke `/guest-post <notion-url-or-id>`. Skill location: `/Users/george.fakorellis/Desktop/SEO Custom Projects/.claude/skills/guest-post/SKILL.md` (project skills folder, same place as the other SEO skills). Runbook: `/Users/george.fakorellis/Desktop/SEO Custom Projects/guest-posts/WORKFLOW.md`.
2. Don't break the pipeline into separate skill calls. The verifier modules (pricing, keyword, section balance, AI score) are scripts under `guest-posts/scripts/` invoked **inside** `/guest-post`, not separately by the user.
3. Resume behavior: if `guest-posts/<slug>/` already exists, the skill resumes from the first step whose output is missing.
4. Stop only on real blockers (auth missing, StealthGPT plateau after 3 retries, scraping fails, target unattainable). Don't ask for direction on intermediate decisions.
5. The pricing verifier needs a Firecrawl scrape pass via AirOps grid 61652 — that's the one operator-in-loop step (the operator triggers the workflow, then the skill proceeds).

**Lessons baked into the workflow this session:**
- Score AI on markdown-stripped prose (`scripts/score_ai.py`), not raw `.md` — `**` inflates ZeroGPT ~30 pts.
- Comparison table prices and body prose prices MUST agree — fix both when updating either.
- Section balance: 100–180 words per tool H3, never under 80. Verify with `scripts/section_balance.py`.
- First-person voice in 8–10 sections is part of the draft, not a separate punch-up pass.
- When a tool is removed mid-pipeline, sweep title count + table renumber + body H3 renumber + mention grep + keyword re-check.
- Always `doc_roundtrip.py pull` + snapshot before any post-publish edit — never overwrite user edits in the Doc.
- Markdown upload only to Drive (HTML breaks fonts).

Related: [[reference_link_outreach]], [[reference_link_discover]].
