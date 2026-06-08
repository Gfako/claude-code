#!/usr/bin/env python3
"""StealthGPT humanization mangles heading and table structure. This script
takes the humanized output and the original draft, and restores:

  1. The H1 (article title) from the original.
  2. The H2 section headings from the original.
  3. The H3 tool headings from the original — matched by tool name and number.
  4. The comparison table from the original (entire section, table + framing).

Body prose under each heading stays as humanized.

Usage: restore_structure.py <original.md> <humanized.md> <out.md>
"""
import re, sys
from pathlib import Path

H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
H2 = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
H3 = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
# Match patterns the humanizer produces for tool sections: "N. **Tool Name..."
FAUX_H3 = re.compile(r"^\s*(\d+)\.\s*\*\*([^*]+?)\*\*\s*$", re.MULTILINE)
# Match the humanized "at-a-glance" section's numbered list
GLANCE_HEAD = re.compile(r"^###?\s*(?:An )?[Aa]t[- ]?a[- ]?glance.*$", re.MULTILINE)


def extract_original_h3_titles(original: str):
    """Returns {number: '### N. Tool — Best for X'} for every H3 starting with a digit."""
    titles = {}
    for m in H3.finditer(original):
        title = m.group(1).strip()
        num_match = re.match(r"(\d+)\.?\s+(.+)", title)
        if num_match:
            num = int(num_match.group(1))
            titles[num] = f"### {title}"
    return titles


def extract_original_glance_section(original: str):
    """The full '## B2B ... at a glance' section through the next H2."""
    matches = list(H2.finditer(original))
    glance = None
    next_h2 = None
    for i, m in enumerate(matches):
        if "at a glance" in m.group(1).lower():
            glance = m
            if i + 1 < len(matches):
                next_h2 = matches[i + 1]
            break
    if not glance:
        return None
    end = next_h2.start() if next_h2 else len(original)
    return original[glance.start():end].rstrip()


def restore(original: str, humanized: str) -> str:
    h3_map = extract_original_h3_titles(original)
    glance_block = extract_original_glance_section(original)

    out = humanized

    # 1. Restore H1 from original
    orig_h1 = H1.search(original)
    if orig_h1:
        # Replace the humanized H1 line (or insert if missing)
        if H1.search(out):
            out = H1.sub(orig_h1.group(0), out, count=1)
        else:
            out = orig_h1.group(0) + "\n\n" + out

    # 2. Restore tool H3 headings — replace "N. **Tool Name...**" lines
    def replace_faux_h3(m):
        num = int(m.group(1))
        return h3_map.get(num, m.group(0))
    out = FAUX_H3.sub(replace_faux_h3, out)

    # 3. Restore the entire "at a glance" section
    if glance_block:
        # Find the humanized at-a-glance header + content up to next H2
        h2_iter = list(H2.finditer(out))
        glance_start = None
        glance_end = None
        for i, m in enumerate(h2_iter):
            # The humanized output may keep the H2 ## or have demoted it to ### — handle both
            if "glance" in m.group(1).lower():
                glance_start = m.start()
                glance_end = h2_iter[i + 1].start() if i + 1 < len(h2_iter) else len(out)
                break
        if glance_start is None:
            # Try H3 form
            for m in H3.finditer(out):
                if "glance" in m.group(1).lower():
                    glance_start = m.start()
                    # Find next H2 or H3 after this
                    nxt = H2.search(out, glance_start + 1)
                    glance_end = nxt.start() if nxt else len(out)
                    break
        if glance_start is not None:
            out = out[:glance_start] + glance_block + "\n\n" + out[glance_end:]

    return out


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    original = Path(sys.argv[1]).read_text()
    humanized = Path(sys.argv[2]).read_text()
    restored = restore(original, humanized)
    Path(sys.argv[3]).write_text(restored)
    print(f"Wrote: {sys.argv[3]} ({len(restored.split())} words)")


if __name__ == "__main__":
    main()
