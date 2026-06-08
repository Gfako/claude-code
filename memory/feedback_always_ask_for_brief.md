---
name: Always ask for content brief
description: When running /edit-review, always ask the user for the content brief before proceeding — never skip this step even if no brief is found locally
type: feedback
---

Always ask the user for the content brief before running the edit review, even if no matching brief is found in `content-briefs/`. The skill instructions explicitly require this.

**Why:** The user expects to be asked — skipping the brief question means the review runs without a key input, and the user has to correct the workflow after the fact.

**How to apply:** During Step 1 of /edit-review, after checking `content-briefs/` for a match, always use AskUserQuestion to ask the user for the brief (Notion URL, local file, or confirmation that none exists) before proceeding to the review.
