#!/usr/bin/env python3
"""
Format a crawl result into:
  1. Notion database row properties (JSON for the upsert call)
  2. Markdown body for the row's page (findings, quotes, suggestions)

Input (stdin JSON):
{
  "url": "...",
  "title": "Post title",
  "section": "blog",
  "score": 42,
  "severity": "High",
  "findings_count": 5,
  "types": ["pricing", "link"],
  "last_checked": "2026-04-24",
  "last_change_detected": "2026-04-20",
  "findings": [
    {
      "type": "pricing",
      "severity": "confirmed",   // confirmed | likely | unconfirmed
      "quote": "HeyGen starts at $29/mo",
      "suggested_fix": "Update to $24/mo per current HeyGen pricing page",
      "source": "https://heygen.com/pricing",
      "source_note": "Checked 2026-04-24"
    },
    ...
  ]
}

The MCPs are called from the skill itself, not from this script — this script
just produces the exact markdown + property dict the skill passes to the MCP.
"""

import json
import sys

TYPE_EMOJI = {
    "pricing": "💰",
    "link": "🔗",
    "feature": "🆕",
    "stat": "📊",
    "ai-news": "🤖",
}

SEVERITY_BADGE = {
    "confirmed": "🔴 Confirmed",
    "likely": "🟡 Likely",
    "unconfirmed": "⚪ Flagged for review",
}


def build_body(result: dict) -> str:
    lines = []
    lines.append(f"# {result.get('title', result['url'])}")
    lines.append("")
    lines.append(f"- **URL:** {result['url']}")
    lines.append(f"- **Score:** {result['score']}/100 — {result['severity']}")
    lines.append(f"- **Findings:** {result['findings_count']}")
    lines.append(f"- **Last checked:** {result['last_checked']}")
    if result.get("last_change_detected"):
        lines.append(f"- **Last change detected:** {result['last_change_detected']}")
    lines.append("")

    findings_by_type = {}
    for f in result.get("findings", []):
        findings_by_type.setdefault(f["type"], []).append(f)

    if not findings_by_type:
        lines.append("_No findings — page is clean._")
        return "\n".join(lines)

    for ftype, group in sorted(findings_by_type.items(), key=lambda kv: kv[0]):
        emoji = TYPE_EMOJI.get(ftype, "•")
        lines.append(f"## {emoji} {ftype.title()} ({len(group)})")
        lines.append("")
        for i, f in enumerate(group, 1):
            badge = SEVERITY_BADGE.get(f.get("severity"), "⚪ Review")
            title = (f.get("title") or "").strip()
            header = f"### {i}. {badge}"
            if title:
                header += f" — {title}"
            lines.append(header)
            lines.append("")
            loc = f.get("location") or {}
            heading = loc.get("heading")
            line_no = loc.get("line")
            if heading or line_no:
                loc_parts = []
                if heading:
                    loc_parts.append(f"section **{heading}**")
                if line_no:
                    loc_parts.append(f"line {line_no}")
                lines.append(f"**Where on the page:** {' · '.join(loc_parts)}")
                lines.append("")
            ftype = f.get("type", "")
            matched = (f.get("text") or "").replace("\n", " ").strip()
            sentence = (f.get("sentence") or f.get("context") or matched or "").replace("\n", " ").strip()

            if ftype == "link":
                # Link rendering: URL on its own line, anchor text shown if present.
                # When anchor exists it's the cleanest signal of where the link
                # is used — surrounding sentence is usually noisy markdown.
                url = matched
                anchor = ((f.get("meta") or {}).get("anchor") or "").strip()
                lines.append("**URL:**")
                lines.append(f"> {url}")
                lines.append("")
                if anchor:
                    lines.append(f"**Anchor text:** \"{anchor}\"")
                    lines.append("")
                elif sentence and sentence != url:
                    # Fall back to surrounding sentence only when no anchor available
                    lines.append("**Used in this sentence:**")
                    lines.append(f"> {sentence[:300]}{'…' if len(sentence) > 300 else ''}")
                    lines.append("")
            else:
                # Non-link: show the matched token + the full sentence it lives in.
                if matched:
                    lines.append(f"**Found:** `{matched}`")
                    lines.append("")
                if sentence and sentence != matched:
                    lines.append("**Exact copy on the page:**")
                    lines.append(f"> {sentence}")
                    lines.append("")
            fix = f.get("suggested_fix", "").strip()
            if fix:
                lines.append("**Suggested fix:**")
                lines.append(f"> {fix}")
                lines.append("")
            src = f.get("source")
            if src:
                note = f.get("source_note", "")
                src_line = f"**Source:** {src}"
                if note:
                    src_line += f" — {note}"
                lines.append(src_line)
                lines.append("")
        lines.append("")

    return "\n".join(lines)


def build_properties(result: dict) -> dict:
    """
    Matches the Notion DB schema for this project. Use these as the property
    values when calling notion-create-pages / notion-update-page.

    Note on expanded property names (Notion MCP convention):
      - URL -> "userDefined:URL" (the "URL" name collides with a Notion reserved key)
      - Dates -> "date:<Name>:start" (+ optional :end, :is_datetime)
      - Types (multi_select) is serialized as a JSON array string

    `findings_page` is optional on create (we don't know the row's own URL yet);
    populate it with a follow-up update-page call after creation, or on
    subsequent upserts when we already have the page_id.
    """
    props = {
        "Title": result.get("title") or result["url"],
        "userDefined:URL": result["url"],
        "Outdatedness score": result["score"],
        "Severity": result["severity"],
        "Findings count": result["findings_count"],
        "Types": json.dumps(result.get("types", [])),
        "Status": "New",
        "date:Last checked:start": result["last_checked"],
        "Section": result.get("section", "blog"),
    }
    if result.get("last_change_detected"):
        props["date:Last change detected:start"] = result["last_change_detected"]
    if result.get("findings_page_url"):
        props["Findings page"] = result["findings_page_url"]
    if "tags" in result:
        # Multi-select: serialize as a JSON array string per the Notion MCP convention.
        props["Tags"] = json.dumps(result.get("tags", []))
    return props


def main():
    result = json.loads(sys.stdin.read())
    out = {
        "properties": build_properties(result),
        "body_markdown": build_body(result),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
