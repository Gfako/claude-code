#!/usr/bin/env python3
"""Full humanize-and-verify pipeline.

For a given markdown file:
1. Humanize via StealthGPT (PhD / High / heavy / quality)
2. Score via ZeroGPT
3. If AI > 30%, retry — up to MAX_ATTEMPTS times, each time humanizing the ORIGINAL again
4. Return the best (lowest AI score) result regardless

Usage: humanize_pipeline.py <markdown-file>
"""
import json
import sys
import time
import requests
from pathlib import Path

STEALTH_KEY = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/stealthgpt-api-key.txt").read_text().strip()
ZEROGPT_KEY = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/zerogpt-api-key.txt").read_text().strip()
STEALTH_URL = "https://stealthgpt.ai/api/stealthify"
ZEROGPT_URL = "https://api.zerogpt.com/api/detect/detectText"

MAX_ATTEMPTS = 3
AI_THRESHOLD = 30.0   # if ZeroGPT AI % is at or below this, accept


def humanize(text: str) -> tuple[str, dict]:
    body = {
        "prompt": text,
        "rephrase": True,
        "tone": "PhD",
        "mode": "High",
        "qualityMode": "quality",
        "model": "heavy",
        "isMultilingual": False,
        "outputFormat": "markdown",
    }
    r = requests.post(STEALTH_URL, json=body, headers={"api-token": STEALTH_KEY}, timeout=300)
    r.raise_for_status()
    resp = r.json()
    if "result" not in resp:
        raise RuntimeError(f"StealthGPT failed: {json.dumps(resp)[:400]}")
    return resp["result"], {
        "stealth_self_score": resp.get("howLikelyToBeDetected"),
        "words_billed": resp.get("wordsSpent"),
        "remaining_credits": resp.get("remainingCredits"),
        "billing_mode": resp.get("billingMode"),
    }


def detect(text: str) -> dict:
    r = requests.post(
        ZEROGPT_URL,
        json={"input_text": text},
        headers={"ApiKey": ZEROGPT_KEY, "Content-Type": "application/json"},
        timeout=60,
    )
    r.raise_for_status()
    resp = r.json()
    if not resp.get("success"):
        raise RuntimeError(f"ZeroGPT failed: code={resp.get('code')} message={resp.get('message')}")
    d = resp["data"]
    return {
        "ai_percentage": float(d.get("fakePercentage") or 0),
        "ai_words": d.get("aiWords"),
        "text_words": d.get("textWords"),
        "verdict": d.get("feedback") or d.get("feedback_message"),
        "flagged_count": len(d.get("h") or d.get("gpt_generated_sentences") or []),
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: humanize_pipeline.py <markdown-file>")
        sys.exit(1)

    src = Path(sys.argv[1])
    original = src.read_text()
    stem = src.stem
    out_dir = src.parent
    print(f"Input: {src.name} ({len(original.split())} words)")
    print(f"Threshold: ZeroGPT AI ≤ {AI_THRESHOLD}% | Max attempts: {MAX_ATTEMPTS}")
    print("=" * 70)

    # Score original (baseline)
    base = detect(original)
    print(f"Baseline (raw)     : AI {base['ai_percentage']:5.1f}% | {base['flagged_count']} flagged | {base['verdict']}")
    print()

    best = {"score": 999.0, "text": None, "attempt": None, "stats": None}

    for attempt in range(1, MAX_ATTEMPTS + 1):
        t0 = time.time()
        try:
            humanized, stats = humanize(original)
        except Exception as e:
            print(f"Attempt {attempt}: humanize FAILED — {e}")
            continue
        try:
            score = detect(humanized)
        except Exception as e:
            print(f"Attempt {attempt}: detect FAILED — {e}")
            continue
        elapsed = time.time() - t0

        # Write attempt to disk
        out_path = out_dir / f"{stem}-humanized-attempt{attempt}.md"
        out_path.write_text(humanized)

        ai_pct = score["ai_percentage"]
        print(
            f"Attempt {attempt} ({elapsed:.0f}s): AI {ai_pct:5.1f}% | "
            f"{score['flagged_count']} flagged | "
            f"StealthGPT self {stats['stealth_self_score']}/100 | "
            f"billed {stats['words_billed']}w | "
            f"-> {out_path.name}"
        )
        print(f"            Verdict: {score['verdict']}")

        if ai_pct < best["score"]:
            best = {"score": ai_pct, "text": humanized, "attempt": attempt, "stats": stats, "score_detail": score}

        if ai_pct <= AI_THRESHOLD:
            print(f"\n✓ PASSED on attempt {attempt} (AI {ai_pct:.1f}% ≤ {AI_THRESHOLD}%). Stopping early.")
            break
    else:
        print(f"\n✗ EXHAUSTED {MAX_ATTEMPTS} attempts without crossing threshold.")

    # Write best (or abort cleanly if every attempt failed)
    print()
    print("=" * 70)
    if best["text"] is None:
        print("All attempts failed before producing any humanized output. Nothing to write.")
        sys.exit(2)
    final_path = out_dir / f"{stem}-humanized-final.md"
    final_path.write_text(best["text"])
    print(f"BEST result   : attempt {best['attempt']}, AI {best['score']:.1f}% -> {final_path.name}")
    print(f"Words billed  : {best['stats']['words_billed']} (this attempt only — every attempt is billed)")
    print(f"Credits left  : {best['stats']['remaining_credits']}")


if __name__ == "__main__":
    main()
