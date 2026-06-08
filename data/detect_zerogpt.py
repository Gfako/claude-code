#!/usr/bin/env python3
"""Score a markdown file with ZeroGPT detection API."""
import json
import sys
import requests
from pathlib import Path

API_KEY = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/zerogpt-api-key.txt").read_text().strip()
URL = "https://api.zerogpt.com/api/detect/detectText"

if len(sys.argv) < 2:
    print("Usage: detect_zerogpt.py <markdown-file>")
    sys.exit(1)
TARGET = Path(sys.argv[1])
text = TARGET.read_text()
print(f"Scoring: {TARGET.name} ({len(text.split())} words)")

r = requests.post(URL, json={"input_text": text}, headers={"ApiKey": API_KEY, "Content-Type": "application/json"}, timeout=60)
print(f"HTTP {r.status_code}")
try:
    resp = r.json()
except ValueError:
    print(f"NON-JSON: {r.text[:400]}")
    sys.exit(1)

if resp.get("success"):
    d = resp["data"]
    print()
    print(f"  Fake / AI percentage: {d.get('fakePercentage', '?')}")
    print(f"  Words counted (textWords): {d.get('textWords', '?')}")
    print(f"  AI-flagged words (aiWords): {d.get('aiWords', '?')}")
    print(f"  Verdict: {d.get('feedback', d.get('feedback_message', '?'))}")
    flagged = d.get('h', d.get('gpt_generated_sentences', []))
    print(f"  AI-flagged sentences (h): {len(flagged) if isinstance(flagged, list) else flagged}")
    if isinstance(flagged, list) and flagged:
        print("  First 3 flagged sentences:")
        for s in flagged[:3]:
            print(f"    - {s[:140]}")
else:
    print(f"FAILED. code={resp.get('code')} message={resp.get('message')}")
    print(json.dumps(resp, indent=2)[:800])
