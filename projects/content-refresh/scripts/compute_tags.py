#!/usr/bin/env python3
"""
Map a list of verified findings to a deduped list of Notion `Tags` values
for the page row.

Tag schema (matches the Notion DB column):
  dead-link, link-redirect, link-auth-wall,
  pricing-tier-removed, pricing-stale,
  feature-count-stale, feature-deprecated,
  stat-old, ai-model-stale

Only `confirmed` and `likely` findings produce tags. Unconfirmed findings
are not tagged so they don't pollute the filter.

Usage:
  echo '{"findings": [...]}' | python3 compute_tags.py
"""

import json
import sys


def _link_tag(f: dict) -> str | None:
    title = (f.get("title") or "").lower()
    note = (f.get("source_note") or "").lower()
    if "dead link" in title or "unreachable" in title:
        return "dead-link"
    if "auth" in title or "401" in title:
        return "link-auth-wall"
    # Generic "Link error (xxx)" → categorize by status if we can find one
    if "404" in note or "(000)" in title:
        return "dead-link"
    return None  # bot-blocked / unconfirmed / redirects don't tag


def _pricing_tag(f: dict) -> str | None:
    title = (f.get("title") or "").lower()
    fix = (f.get("suggested_fix") or "").lower()
    if "doesn't match any tier" in title or "tier doesn't exist" in title or "no longer has" in fix or "no team" in fix.lower() or "tier doesn't exist" in fix:
        return "pricing-tier-removed"
    return "pricing-stale"


def _feature_tag(f: dict) -> str | None:
    meta = f.get("meta") or {}
    subtype = meta.get("subtype", "")
    title = (f.get("title") or "").lower()
    # Numeric feature counts (avatars, languages, voices, templates, etc.)
    if subtype in {"avatars", "languages", "voices", "templates", "integrations", "accents",
                   "duration_limit", "volume_per_period", "videos_per_period"}:
        return "feature-count-stale"
    if "count" in title and ("stale" in title or "outdated" in title):
        return "feature-count-stale"
    return "feature-deprecated"


def tag_for(f: dict) -> str | None:
    if f.get("severity") not in ("confirmed", "likely"):
        return None
    t = f.get("type")
    if t == "link":
        return _link_tag(f)
    if t == "pricing":
        return _pricing_tag(f)
    if t == "feature":
        return _feature_tag(f)
    if t == "stat":
        return "stat-old"
    if t == "ai-news":
        return "ai-model-stale"
    if t == "title":
        return "title"
    if t == "meta":
        return "meta"
    return None


def compute_tags(findings: list[dict]) -> list[str]:
    seen: list[str] = []
    for f in findings or []:
        tag = tag_for(f)
        if tag and tag not in seen:
            seen.append(tag)
    return seen


def main():
    payload = json.loads(sys.stdin.read())
    tags = compute_tags(payload.get("findings", []))
    print(json.dumps(tags, ensure_ascii=False))


if __name__ == "__main__":
    main()
