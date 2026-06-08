#!/usr/bin/env python3
"""
Score a set of verified findings for one URL.

Input (stdin JSON):
  {
    "findings": [
      {"type": "pricing", "severity": "confirmed" | "likely" | "unconfirmed", ...},
      ...
    ]
  }

Severity multipliers:
  confirmed = 1.0     (verified against a fresh source, definitely wrong)
  likely    = 0.6     (strongly suggestive but not fully verified)
  unconfirmed = 0.0   (don't score these — they become extractor noise)

Score = sum(weight[type] * multiplier[severity]) capped at score_cap.
Severity tier derived from config thresholds.
"""

import json
import sys
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config.json"

SEVERITY_MULTIPLIER = {
    "confirmed": 1.0,
    "likely": 0.6,
    "unconfirmed": 0.0,
}


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def score_findings(findings: list[dict], cfg: dict) -> dict:
    weights = cfg["scoring_weights"]
    cap = cfg.get("score_cap", 100)
    total = 0.0
    counted_types = set()
    for f in findings:
        ftype = f.get("type")
        sev = f.get("severity", "unconfirmed")
        w = weights.get(ftype, 0)
        mult = SEVERITY_MULTIPLIER.get(sev, 0.0)
        contribution = w * mult
        total += contribution
        if contribution > 0:
            counted_types.add(ftype)
    score = min(int(round(total)), cap)

    thresholds = cfg["severity_thresholds"]
    # Sort tiers by their threshold ascending, pick the highest whose threshold <= score.
    sorted_tiers = sorted(thresholds.items(), key=lambda kv: kv[1])
    tier = "Clean"
    for name, thresh in sorted_tiers:
        if score >= thresh:
            tier = name
    return {
        "score": score,
        "severity": tier,
        "types": sorted(counted_types),
        "counted_findings": sum(1 for f in findings if SEVERITY_MULTIPLIER.get(f.get("severity"), 0) > 0),
    }


def main():
    cfg = load_config()
    payload = json.loads(sys.stdin.read())
    findings = payload.get("findings", [])
    result = score_findings(findings, cfg)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
