#!/usr/bin/env python3
"""Word-count per H3 section. Flags imbalances.

Usage:  python3 section_balance.py <article.md> [--min 80] [--max-ratio 2.5]

Exit code 0 if balanced, 1 if any section flagged.
"""
import argparse, re, sys, json
from pathlib import Path

H3 = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
HEADING = re.compile(r"^#{2,6}\s+(?:.+?)\s*$", re.MULTILINE)  # h2/h3/h4/... boundary


def split_h3_sections(text: str):
    h3_matches = list(H3.finditer(text))
    all_headings = list(HEADING.finditer(text))
    sections = []
    for m in h3_matches:
        title = m.group(1).strip()
        start = m.end()
        next_heading = next((h for h in all_headings if h.start() > m.start()), None)
        end = next_heading.start() if next_heading else len(text)
        body = text[start:end].strip()
        sections.append({"title": title, "words": len(body.split())})
    return sections


TOOL_SECTION = re.compile(r"^\d+\\?\.\s")  # listicle tool: "1. Tool — ..." or "1\. Tool — ..."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=Path)
    ap.add_argument("--min", type=int, default=80, help="flag if section below this word count")
    ap.add_argument("--max-ratio", type=float, default=2.5, help="flag if section > N x median")
    ap.add_argument("--tools-only", action="store_true",
                    help="only score H3s whose title starts with N. (the numbered tool sections)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    text = args.file.read_text()
    sections = split_h3_sections(text)
    if args.tools_only:
        sections = [s for s in sections if TOOL_SECTION.match(s["title"])]
    if not sections:
        print("No matching sections found.")
        sys.exit(0)

    counts = sorted(s["words"] for s in sections)
    median = counts[len(counts) // 2]
    flagged = []
    for s in sections:
        s["status"] = "ok"
        if s["words"] < args.min:
            s["status"] = "too_short"
            flagged.append(s)
        elif median and s["words"] > median * args.max_ratio:
            s["status"] = "too_long"
            flagged.append(s)

    report = {
        "file": str(args.file),
        "count": len(sections),
        "median": median,
        "min": min(counts),
        "max": max(counts),
        "flagged": flagged,
        "sections": sections,
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Sections: {len(sections)} | median {median} words | range {min(counts)}–{max(counts)}")
        if flagged:
            print(f"\nFLAGGED ({len(flagged)}):")
            for s in flagged:
                print(f"  [{s['status']:>10}] {s['words']:>4}w  {s['title']}")
        else:
            print("All sections balanced.")
        print("\nAll sections (sorted by word count):")
        for s in sorted(sections, key=lambda x: x["words"]):
            marker = "!" if s["status"] != "ok" else " "
            print(f"  {marker} {s['words']:>4}w  {s['title']}")

    sys.exit(1 if flagged else 0)


if __name__ == "__main__":
    main()
