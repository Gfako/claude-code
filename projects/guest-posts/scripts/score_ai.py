#!/usr/bin/env python3
"""Strip markdown to rendered prose, then score via ZeroGPT.

Crucial: markdown bold (`**`) inflates ZeroGPT's score by ~30 points because the
detector counts the literal asterisks as template structure. A Google Doc renders
the same prose without those characters, so we score on the stripped version.

Usage:  python3 score_ai.py <article.md>

Exits 0 if AI score < threshold (default 30), 1 otherwise.
"""
import argparse, re, sys
from pathlib import Path
import requests

KEY_PATH = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/zerogpt-api-key.txt")
URL = "https://api.zerogpt.com/api/detect/detectText"


def to_rendered_prose(md: str) -> str:
    text = md
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)  # fenced code
    text = re.sub(r"`[^`]+`", "", text)  # inline code
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # md links → anchor
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)  # images
    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text, flags=re.MULTILINE)  # heading markers
    text = re.sub(r"[*_]{1,3}", "", text)  # bold/italic markers
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)  # ul markers
    text = re.sub(r"^\s*\d+[.)]\s+", "", text, flags=re.MULTILINE)  # ol markers
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)  # blockquote
    text = re.sub(r"^\|.*\|\s*$", "", text, flags=re.MULTILINE)  # table rows
    text = re.sub(r"\\([)(\\\[\]{}.!])", r"\1", text)  # md escapes
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def score(text: str) -> dict:
    key = KEY_PATH.read_text().strip()
    r = requests.post(
        URL,
        json={"input_text": text},
        headers={"ApiKey": key, "Content-Type": "application/json"},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=Path)
    ap.add_argument("--threshold", type=float, default=30.0)
    ap.add_argument("--show-prose", action="store_true")
    args = ap.parse_args()

    md = args.file.read_text()
    prose = to_rendered_prose(md)
    if args.show_prose:
        print("--- STRIPPED PROSE ---")
        print(prose[:2000])
        print("--- END ---\n")

    resp = score(prose)
    data = resp.get("data", resp)
    ai_pct = data.get("fakePercentage") or data.get("ai_percentage") or 0
    words = data.get("textWords") or len(prose.split())
    print(f"File:      {args.file.name}")
    print(f"Words:     {words}")
    print(f"AI score:  {ai_pct}%")
    print(f"Threshold: {args.threshold}%")
    status = "PASS" if ai_pct < args.threshold else "FAIL"
    print(f"Status:    {status}")
    sys.exit(0 if status == "PASS" else 1)


if __name__ == "__main__":
    main()
