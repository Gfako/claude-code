#!/usr/bin/env python3
"""Humanize a long article by splitting on H2 boundaries, humanizing each chunk,
and concatenating. Scores the rendered version with ZeroGPT after each pass.

For each chunk:
  - Cap at ~1,800 words. If a single H2 section is bigger, split further on H3.
  - Up to 3 retries against ZeroGPT ≤ 30% on the chunk.

Then concatenate humanized chunks → score the rendered concatenation → done.

Usage: humanize_chunked.py <markdown-file>
"""
import json, re, sys, time
from pathlib import Path
import requests

STEALTH_KEY = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/stealthgpt-api-key.txt").read_text().strip()
ZEROGPT_KEY = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/zerogpt-api-key.txt").read_text().strip()
STEALTH_URL = "https://stealthgpt.ai/api/stealthify"
ZEROGPT_URL = "https://api.zerogpt.com/api/detect/detectText"

MAX_CHUNK_WORDS = 1500
MAX_ATTEMPTS = 3
AI_THRESHOLD = 35.0   # per-chunk threshold (final whole-doc score is what matters)


def humanize(text: str):
    body = {
        "prompt": text, "rephrase": True,
        "tone": "PhD", "mode": "High",
        "qualityMode": "quality", "model": "heavy",
        "isMultilingual": False, "outputFormat": "markdown",
    }
    r = requests.post(STEALTH_URL, json=body, headers={"api-token": STEALTH_KEY}, timeout=300)
    r.raise_for_status()
    resp = r.json()
    if "result" not in resp:
        raise RuntimeError(f"StealthGPT failed: {json.dumps(resp)[:400]}")
    return resp["result"]


def detect(text: str):
    r = requests.post(ZEROGPT_URL, json={"input_text": text},
                       headers={"ApiKey": ZEROGPT_KEY, "Content-Type": "application/json"}, timeout=60)
    r.raise_for_status()
    return r.json()["data"]


def split_by_h2(text: str):
    """Split markdown into chunks bounded by H2 (or H1 if no H2). Chunks include
    their leading heading. Each chunk capped at MAX_CHUNK_WORDS — bigger sections
    get further split on H3.
    """
    h2_starts = [m.start() for m in re.finditer(r"^##\s+", text, flags=re.MULTILINE)]
    h1_match = re.search(r"^#\s+", text, flags=re.MULTILINE)
    h1_start = h1_match.start() if h1_match else 0
    if not h2_starts:
        return [text]
    boundaries = [h1_start] + h2_starts + [len(text)]
    chunks = []
    for i in range(len(boundaries) - 1):
        chunk = text[boundaries[i]:boundaries[i + 1]].strip()
        if not chunk:
            continue
        if len(chunk.split()) <= MAX_CHUNK_WORDS:
            chunks.append(chunk)
        else:
            # split on H3 inside this chunk
            h3 = [m.start() for m in re.finditer(r"^###\s+", chunk, flags=re.MULTILINE)]
            if not h3:
                chunks.append(chunk)
                continue
            sub = []
            current = chunk[:h3[0]].strip()
            for j, h3start in enumerate(h3):
                end = h3[j + 1] if j + 1 < len(h3) else len(chunk)
                sub_part = chunk[h3start:end].strip()
                if len((current + "\n\n" + sub_part).split()) <= MAX_CHUNK_WORDS:
                    current = (current + "\n\n" + sub_part).strip()
                else:
                    if current:
                        sub.append(current)
                    current = sub_part
            if current:
                sub.append(current)
            chunks.extend(sub)
    return chunks


def humanize_chunk(chunk: str, idx: int, total: int):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            t0 = time.time()
            humanized = humanize(chunk)
            elapsed = time.time() - t0
        except Exception as e:
            print(f"  Chunk {idx}/{total} attempt {attempt}: humanize FAILED — {e}")
            continue
        d = detect(humanized)
        ai = float(d.get("fakePercentage") or 0)
        print(f"  Chunk {idx}/{total} attempt {attempt} ({elapsed:.0f}s): AI {ai:5.1f}%   "
              f"{len(humanized.split())}w out")
        if ai <= AI_THRESHOLD:
            return humanized, ai
    # fallback — return the last attempted humanized version
    return humanized, ai


def main():
    src = Path(sys.argv[1])
    text = src.read_text()
    chunks = split_by_h2(text)
    print(f"Input: {src.name} ({len(text.split())} words) → {len(chunks)} chunks")
    print(f"Per-chunk threshold: AI ≤ {AI_THRESHOLD}% | Max attempts per chunk: {MAX_ATTEMPTS}")
    print("=" * 70)
    out_parts = []
    for i, c in enumerate(chunks, 1):
        print(f"\nChunk {i}/{len(chunks)}: {len(c.split())}w  — '{c.splitlines()[0][:60]}'")
        humanized, ai = humanize_chunk(c, i, len(chunks))
        out_parts.append(humanized)
    final = "\n\n".join(out_parts)
    out = src.parent / (src.stem + "-humanized-final.md")
    out.write_text(final)
    print("\n" + "=" * 70)
    print(f"Combined output: {out}  ({len(final.split())} words)")


if __name__ == "__main__":
    main()
