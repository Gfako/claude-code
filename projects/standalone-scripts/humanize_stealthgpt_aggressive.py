#!/usr/bin/env python3
"""Aggressive single-pass humanization via StealthGPT (PhD + High + heavy + quality)."""
import json
import re
import requests
from pathlib import Path

API_KEY = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/stealthgpt-api-key.txt").read_text().strip()
INPUT = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/content-briefs/test-marketing-software-first500.md")
OUTPUT = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/content-briefs/test-marketing-software-first500-humanized-aggressive.md")
URL = "https://stealthgpt.ai/api/stealthify"

sample = INPUT.read_text()
body = {
    "prompt": sample,
    "rephrase": True,
    "tone": "PhD",                  # most stylistic transformation
    "mode": "High",                 # most elaboration / rewording
    "qualityMode": "quality",       # keep quality check on
    "model": "heavy",               # bypass-focused engine
    "isMultilingual": False,
    "outputFormat": "markdown",
}

print(f"INPUT  : {len(sample.split())} words")
print(f"        Calling StealthGPT with tone=PhD, mode=High...")

r = requests.post(URL, json=body, headers={"api-token": API_KEY}, timeout=240)
print(f"HTTP {r.status_code}")

try:
    resp = r.json()
except ValueError:
    print(f"NON-JSON response: {r.text[:500]}")
    raise SystemExit(1)

if "result" in resp:
    OUTPUT.write_text(resp["result"])
    print()
    print(f"OUTPUT : {len(resp['result'].split())} words written -> {OUTPUT.name}")
    print(f"  howLikelyToBeDetected (higher = more human): {resp.get('howLikelyToBeDetected', 'n/a')}")
    print(f"  wordsSpent: {resp.get('wordsSpent', 'n/a')}")
    print(f"  remainingCredits: {resp.get('remainingCredits', 'n/a')}")
    print(f"  billingMode: {resp.get('billingMode', 'n/a')}")
else:
    print("FAILED. Response payload:")
    print(json.dumps(resp, indent=2)[:1500])
