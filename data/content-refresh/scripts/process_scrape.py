#!/usr/bin/env python3
"""
Take a Firecrawl scrape response file (the auto-saved tool result), extract the
markdown + html, save them under drafts/, and run the extractor.

Usage:
    python3 process_scrape.py <scrape_json_path> <slug> [section]

  section is optional. If "blog" (default — auto-detected), the extractor is
  told to restrict to article body (strips top banner / pre-footer / about-
  synthesia / related posts templates). For "alternatives", the whole page is
  considered article-relevant.

Outputs:
    drafts/<slug>.original.md
    drafts/<slug>.original.html
    drafts/<slug>.findings.json
And prints a compact JSON: {slug, title, md_chars, findings_count, by_type}
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DRAFTS = ROOT / "drafts"
DRAFTS.mkdir(exist_ok=True)

SCRIPT_EXTRACT = ROOT / "scripts" / "extract_claims.py"


def main():
    if len(sys.argv) not in (3, 4):
        print("usage: process_scrape.py <scrape_json> <slug> [section]", file=sys.stderr)
        sys.exit(1)
    scrape_path = Path(sys.argv[1])
    slug = sys.argv[2]
    # Section: "blog" or "alternatives". Default = blog (article-body-only),
    # since most of our crawl targets are blog posts.
    section = sys.argv[3] if len(sys.argv) == 4 else "blog"

    raw = scrape_path.read_text()
    data = json.loads(raw)
    md = data.get("markdown", "")
    html = data.get("html", "")
    metadata = data.get("metadata", {}) or {}
    title = metadata.get("title") or metadata.get("ogTitle") or ""
    if not title:
        m = re.search(r"^#\s+(.+)$", md, re.MULTILINE)
        title = m.group(1).strip() if m else slug

    (DRAFTS / f"{slug}.original.md").write_text(md)
    (DRAFTS / f"{slug}.original.html").write_text(html)
    (DRAFTS / f"{slug}.metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2))

    article_body_only = (section == "blog")
    payload = json.dumps({"text": md, "html": html, "article_body_only": article_body_only, "metadata": metadata})
    proc = subprocess.run(
        ["python3", str(SCRIPT_EXTRACT)],
        input=payload,
        capture_output=True, text=True, check=True,
    )
    findings = json.loads(proc.stdout)
    (DRAFTS / f"{slug}.findings.json").write_text(json.dumps(findings, indent=2, ensure_ascii=False))

    summary = {
        "slug": slug,
        "section": section,
        "title": title,
        "md_chars": len(md),
        "html_chars": len(html),
        "article_body_only": article_body_only,
        "findings_count": findings["total"],
        "by_type": findings["counts"],
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
