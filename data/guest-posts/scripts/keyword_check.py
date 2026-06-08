#!/usr/bin/env python3
"""Clearscope keyword frequency check.

Usage:  python3 keyword_check.py <article.md> <targets.json>

targets.json format:
[
  {"keyword": "marketing software", "target": 17},
  {"keyword": "marketing tools",    "target": 7},
  ...
]

Exit 0 if all targets met, 1 otherwise.
"""
import argparse, json, re, sys
from pathlib import Path


def normalize(text: str) -> str:
    text = re.sub(r"[*_`]+", "", text)  # strip md emphasis
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # strip md links (keep anchor)
    text = re.sub(r"<[^>]+>", "", text)  # strip HTML
    return text.lower()


def count(text: str, kw: str) -> int:
    return len(re.findall(re.escape(kw.lower()), text))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article", type=Path)
    ap.add_argument("targets", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    text = normalize(args.article.read_text())
    targets = json.loads(args.targets.read_text())

    rows = []
    misses = 0
    for t in targets:
        actual = count(text, t["keyword"])
        target = t["target"]
        status = "OK" if actual >= target else "MISS"
        if status == "MISS":
            misses += 1
        rows.append({"keyword": t["keyword"], "target": target, "actual": actual, "status": status})

    if args.json:
        print(json.dumps({"misses": misses, "rows": rows}, indent=2))
    else:
        print(f"{'STATUS':<6} {'COUNT':>6}  {'TARGET':>6}  KEYWORD")
        print("-" * 70)
        for r in rows:
            print(f"{r['status']:<6} {r['actual']:>6}  {r['target']:>6}  {r['keyword']}")
        print(f"\n{misses}/{len(rows)} keywords below target.")

    sys.exit(1 if misses else 0)


if __name__ == "__main__":
    main()
