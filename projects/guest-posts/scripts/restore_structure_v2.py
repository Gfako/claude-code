#!/usr/bin/env python3
"""Splice humanized prose into the original draft's structure.

Strategy: original draft is the skeleton (H1/H2/H3 + table). For each H3 tool
section in the original, find the matching humanized prose by tool name match,
and use the humanized body under the original H3 heading.

For top-level H2 sections (intro, methodology, FAQs, etc.), match by section
title similarity and replace the original body with humanized prose.

Usage: restore_structure_v2.py <original.md> <humanized.md> <out.md>
"""
import re, sys
from pathlib import Path

HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)


def parse_sections(text: str):
    """Returns list of {level, title, start, body}. Sections are bounded by next
    heading of same or higher level."""
    headings = []
    for m in HEADING_RE.finditer(text):
        level = len(m.group(1))
        title = m.group(2).strip()
        headings.append((level, title, m.start(), m.end()))
    sections = []
    for i, (lvl, title, hstart, hend) in enumerate(headings):
        # next heading of level <= current
        body_end = len(text)
        for j in range(i + 1, len(headings)):
            if headings[j][0] <= lvl:
                body_end = headings[j][2]
                break
        body = text[hend:body_end].strip("\n")
        sections.append({"level": lvl, "title": title, "body": body, "start": hstart})
    return sections


def tool_name_from_h3(title: str):
    """'1. HubSpot Marketing Hub — Best all-in-one' → 'hubspot marketing hub'.
    Returns lowercase tool name, no number, no — Best for clause."""
    m = re.match(r"\d+\\?\.\s*([^—\-]+?)\s*[—\-]", title)
    if m:
        return m.group(1).strip().lower()
    # fallback: no dash, just strip number
    m2 = re.match(r"\d+\\?\.\s*(.+)", title)
    if m2:
        return m2.group(1).strip().lower()
    return title.strip().lower()


def find_humanized_tool_body(humanized: str, tool_name: str):
    """Locate the section in humanized text that's about this tool. Match by
    name appearing in a heading-like line (H3, faux-H3 'N. **Name...**', or
    bold paragraph opener)."""
    name_pattern = re.escape(tool_name)
    candidates = []

    # Real H3
    for m in re.finditer(r"^###\s+.*?" + name_pattern + r".*$", humanized,
                          re.IGNORECASE | re.MULTILINE):
        candidates.append(m.end())
    # Faux H3 - "N. **Name...**"
    for m in re.finditer(r"^\s*\d+\.\s*\*\*[^*]*" + name_pattern + r"[^*]*\*\*\s*$",
                          humanized, re.IGNORECASE | re.MULTILINE):
        candidates.append(m.end())
    # Bold paragraph opener at line start
    for m in re.finditer(r"^\*\*" + name_pattern + r"\*\*", humanized,
                          re.IGNORECASE | re.MULTILINE):
        candidates.append(m.start())

    if not candidates:
        return None

    start = min(candidates)
    # body ends at next H1/H2/H3 OR at next faux-H3 line OR end of doc
    end_match = re.search(
        r"\n(?:#{1,3}\s|\s*\d+\.\s*\*\*[^*]+\*\*\s*$|##\s)",
        humanized[start + 1:], re.MULTILINE
    )
    end = start + 1 + end_match.start() if end_match else len(humanized)
    body = humanized[start:end].strip()
    # Trim leading heading-like line if we matched a real heading
    lines = body.split("\n", 1)
    if len(lines) > 1 and (lines[0].startswith("###") or
                            re.match(r"^\s*\d+\.\s*\*\*", lines[0])):
        body = lines[1].strip()
    return body


def find_humanized_h2_body(humanized: str, h2_title: str):
    """Find H2 section in humanized by fuzzy title match (first 2 significant
    words)."""
    title_words = [w for w in re.findall(r"\w+", h2_title.lower()) if len(w) > 3][:3]
    if not title_words:
        return None
    pattern = ".*".join(re.escape(w) for w in title_words)
    m = re.search(r"^##\s+.*" + pattern + r".*$", humanized,
                   re.IGNORECASE | re.MULTILINE)
    if not m:
        return None
    body_start = m.end()
    next_h2 = re.search(r"^##\s", humanized[body_start + 1:], re.MULTILINE)
    body_end = body_start + 1 + next_h2.start() if next_h2 else len(humanized)
    return humanized[body_start:body_end].strip()


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    original = Path(sys.argv[1]).read_text()
    humanized = Path(sys.argv[2]).read_text()

    out = original

    # Replace each H3 tool section body with humanized prose
    h3_pattern = re.compile(r"(^###\s+\d+\\?\.\s+[^\n]+\n)((?:(?!^#{1,3}\s).*\n?)*)",
                             re.MULTILINE)

    def replace_h3(m):
        heading = m.group(1)
        title_text = heading.replace("###", "").strip()
        tool = tool_name_from_h3(title_text)
        humanized_body = find_humanized_tool_body(humanized, tool)
        if humanized_body:
            return heading + "\n" + humanized_body + "\n\n"
        return m.group(0)

    out = h3_pattern.sub(replace_h3, out)

    # Replace each H2 section body (NOT the at-a-glance with the table, NOT the
    # H2s that contain H3 subsections — those keep their humanized H3 bodies)
    h2_titles_to_replace = [
        "What is B2B marketing software",  # body H2 with bullets
        "How I picked the tools",           # intro methodology
        "How to pick the right",            # closer
        "Common mistakes B2B teams",
        "FAQs",
        "Time to upgrade your B2B",
    ]
    h2_pattern = re.compile(
        r"(^##\s+([^\n]+)\n)((?:(?!^##\s).*\n?)*)",
        re.MULTILINE
    )

    def replace_h2(m):
        heading = m.group(1)
        h2_title = m.group(2).strip()
        if not any(t.lower() in h2_title.lower() for t in h2_titles_to_replace):
            return m.group(0)
        # Don't replace if section contains H3s (handled per-H3 above)
        body = m.group(3)
        if re.search(r"^###\s", body, re.MULTILINE):
            return m.group(0)
        humanized_body = find_humanized_h2_body(humanized, h2_title)
        if humanized_body:
            return heading + humanized_body + "\n\n"
        return m.group(0)

    out = h2_pattern.sub(replace_h2, out)

    # Replace H1 intro (the text between H1 and first H2 — preserve H1)
    h1_match = re.search(r"^#\s+[^\n]+\n", out, re.MULTILINE)
    first_h2 = re.search(r"^##\s", out[h1_match.end():], re.MULTILINE)
    if h1_match and first_h2:
        # find humanized H1's intro paras (between H1 and first H2 in humanized)
        h_h1 = re.search(r"^#\s+[^\n]+\n", humanized, re.MULTILINE)
        h_h2 = re.search(r"^##\s", humanized[h_h1.end():], re.MULTILINE) if h_h1 else None
        if h_h1 and h_h2:
            humanized_intro = humanized[h_h1.end():h_h1.end() + h_h2.start()].strip()
            intro_start = h1_match.end()
            intro_end = h1_match.end() + first_h2.start()
            out = out[:intro_start] + "\n" + humanized_intro + "\n\n" + out[intro_end:]

    Path(sys.argv[3]).write_text(out)
    print(f"Wrote: {sys.argv[3]} ({len(out.split())} words)")


if __name__ == "__main__":
    main()
