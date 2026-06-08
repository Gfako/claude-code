---
name: blog-guidelines
description: Fetch Synthesia Blog Content Guidelines from Notion and save a condensed, actionable version locally. Use this before /edit-review to ensure reviews are grounded in the latest guidelines.
---

# Fetch Synthesia Blog Content Guidelines

Fetch the full Synthesia Blog Content Guidelines from Notion, extract the actionable text (stripping image URLs), and save a condensed version locally that other skills (like `/edit-review`) can reference.

## Source

Notion page: https://www.notion.so/synthesia/Synthesia-Blog-Content-Guidelines-2e1c16d22bf18036ac4af442274c1553

## Steps

1. **Fetch the guidelines page** from Notion using `notion-fetch` with the URL above.
2. If the result is too large and gets saved to a file, read that file in sequential chunks (8K characters at a time using bash/python) until you have 100% of the text content.
3. **Extract only the actionable text** — strip out all S3 image URLs, Notion metadata, and formatting artifacts. Keep:
   - Section headings and structure
   - All checklist items, rules, and guidelines
   - AEO tips with their stats
   - Internal linking rules
   - Embedded content types and when to use them
   - Voice, tone, and editing rules
   - The 3-pass editing system
   - Content type definitions (how-to, review/listicle, data-led)
   - Guiding principles for L&D content
   - Information gain definition and examples
4. **Save the condensed guidelines** to `blog-guidelines/synthesia-blog-guidelines.md` in the working directory. Include a header with the fetch date so reviewers know how fresh it is.
5. **Confirm** to the user that the guidelines have been saved and are ready for use by `/edit-review`.

## Output

The file should be a clean, readable markdown document organized by the same sections as the Notion page. No images, no S3 URLs, no Notion markup — just the rules, checklists, and guidelines in plain markdown.
