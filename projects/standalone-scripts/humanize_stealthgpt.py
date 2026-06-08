#!/usr/bin/env python3
"""Humanize the first N words of a markdown file via StealthGPT /api/stealthify."""
import json
import re
import sys
import requests
from pathlib import Path

API_KEY = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/stealthgpt-api-key.txt").read_text().strip()
SOURCE = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/content-briefs/test-marketing-software-article.md")
OUTPUT_RAW = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/content-briefs/test-marketing-software-first500.md")
OUTPUT_HUMANIZED = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/content-briefs/test-marketing-software-first500-humanized.md")

TARGET_WORDS = 500
URL = "https://stealthgpt.ai/api/stealthify"

def first_n_words(text, n):
    """Return the first n words of text, preserving whitespace around them."""
    tokens = re.findall(r"\S+\s*", text)
    out, count = [], 0
    for t in tokens:
        if count >= n:
            break
        out.append(t)
        count += 1
    return "".join(out).rstrip()

def call_stealthify(prompt, tone="Standard", mode="Medium", output_format="markdown"):
    body = {
        "prompt": prompt,
        "rephrase": True,            # humanize existing text, don't generate new
        "tone": tone,                # Standard | College | HighSchool | PhD
        "mode": mode,                # Low | Medium | High
        "qualityMode": "quality",    # quality | fast
        "model": "heavy",            # heavy | lite (heavy = bypass-focused)
        "isMultilingual": False,
        "outputFormat": output_format,
    }
    r = requests.post(URL, json=body, headers={"api-token": API_KEY}, timeout=180)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {"raw": r.text[:500]}

# --- run ---
full = SOURCE.read_text()
sample = first_n_words(full, TARGET_WORDS)
actual_words = len(sample.split())
OUTPUT_RAW.write_text(sample)
print(f"INPUT  : {actual_words} words extracted -> {OUTPUT_RAW.name}")
print(f"        Calling StealthGPT...")

code, resp = call_stealthify(sample)
print(f"HTTP {code}")
print(f"Response keys: {list(resp.keys())}")

if "result" in resp:
    OUTPUT_HUMANIZED.write_text(resp["result"])
    print()
    print(f"OUTPUT : {len(resp['result'].split())} words written -> {OUTPUT_HUMANIZED.name}")
    print(f"  howLikelyToBeDetected (higher = more human): {resp.get('howLikelyToBeDetected', 'n/a')}")
    print(f"  wordsSpent: {resp.get('wordsSpent', resp.get('tokensSpent', 'n/a'))}")
    print(f"  remainingCredits: {resp.get('remainingCredits', 'n/a')}")
    print(f"  billingMode: {resp.get('billingMode', 'n/a')}")
else:
    print("FAILED. Response payload:")
    print(json.dumps(resp, indent=2)[:1500])
