#!/usr/bin/env python3
"""
Programmatic first-pass verifier.

Reads drafts/<slug>.findings.json + state/competitor_prices.json, assigns
severity / title / suggested_fix to each finding using deterministic rules,
and writes drafts/<slug>.verified.json.

Severity rules:
- pricing: try to match brand+amount against cached tier prices (both monthly
  and annual). If brand is "unverified" (D-ID, Hour One, Invideo, VEED) →
  unconfirmed. If amount matches a known tier → drop (still current). If
  amount doesn't match any tier → confirmed outdated.
- feature (numeric): compare against cached counts when available.
- stat: year_ref older than 18 months → likely; others → unconfirmed.
- ai-news: unconfirmed by default (LLM should review).
- link: marked as needs_check (caller batches HEAD checks separately).

Generates a short `title` (3-8 words) for every finding.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
PRICES = json.load(open(ROOT / "state" / "competitor_prices.json"))

_KB_PATH = ROOT / "state" / "synthesia_kb.json"
SYNTHESIA_KB: dict = json.loads(_KB_PATH.read_text()) if _KB_PATH.exists() else {"entries": []}


def kb_lookup(query: str) -> list[dict]:
    """
    Loose substring match against KB names + descriptions. Returns matching
    entries (could be 0 or many). The verifier (or LLM) decides what to do
    with the matches — typically: if KB says status="removed" and the blog
    claim asserts the feature is current, that's a confirmed contradiction.
    """
    if not query:
        return []
    q = query.lower()
    hits = []
    for e in SYNTHESIA_KB.get("entries", []):
        haystack = " ".join([
            e.get("name", ""),
            e.get("id", ""),
            e.get("description", ""),
        ]).lower()
        if q in haystack:
            hits.append(e)
    return hits


def page_brand_from_slug(slug: str) -> str | None:
    """Determine which competitor a comparison page is about."""
    if slug.startswith("synthesia-vs-"):
        return slug.replace("synthesia-vs-", "")
    return None


def normalize_amount(s: str) -> float | None:
    s = s.replace(",", "").replace(" ", "")
    try:
        return float(s)
    except ValueError:
        return None


def find_matching_tier(amount: float, prices: dict) -> dict | None:
    """Look for any tier whose monthly OR annual price matches `amount`."""
    for tier in prices.get("tiers", []):
        for key in ("monthly", "annual_per_mo", "monthly_per_seat"):
            v = tier.get(key)
            if isinstance(v, (int, float)) and abs(v - amount) < 0.5:
                return {"tier": tier["name"], "matched_field": key, "matched_value": v}
    return None


def verify_pricing(f: dict, page_brand: str | None) -> dict:
    meta = f.get("meta", {})
    brand = (meta.get("brand") or "").lower()
    amount_str = meta.get("amount", "")
    amount = normalize_amount(amount_str)
    text = f.get("text", "")

    # Decide which competitor's pricing to compare against
    target_brand = brand
    # If brand is "synthesia" but the page is a vs-X comparison, this is OK as-is
    prices = PRICES.get(target_brand)

    out = dict(f)

    if amount is None:
        out["severity"] = "unconfirmed"
        out["title"] = f"Pricing format unclear ({brand or 'unknown'})"
        out["suggested_fix"] = f"Couldn't parse amount from `{text}`. Verify manually."
        out["source"] = ""
        out["source_note"] = ""
        return out

    if prices is None:
        out["severity"] = "unconfirmed"
        out["title"] = f"{brand or 'Brand'} not in price cache"
        out["suggested_fix"] = f"No cached pricing data for {brand}. Verify `{text}` manually."
        out["source"] = ""
        out["source_note"] = ""
        return out

    if prices.get("unverified"):
        out["severity"] = "unconfirmed"
        out["title"] = f"{brand.title()} pricing not fetchable"
        out["suggested_fix"] = (
            f"{prices.get('note', '')} Verify `{text}` manually."
        )
        out["source"] = ""
        out["source_note"] = "Competitor pricing page unavailable to scraper"
        return out

    match = find_matching_tier(amount, prices)
    if match:
        out["severity"] = "unconfirmed"  # still current — informational
        out["title"] = f"{brand.title()} {match['tier']} ${int(amount)} still current"
        out["suggested_fix"] = (
            f"Current — ${int(amount)} matches {brand.title()} {match['tier']} tier "
            f"({match['matched_field'].replace('_', ' ')}). No action."
        )
        out["source"] = "(cached pricing 2026-04-24)"
        out["source_note"] = ""
        return out

    # No match — likely outdated
    available = [
        f"{t['name']} ${t.get('monthly') or t.get('monthly_per_seat') or '?'}/mo"
        + (f" or ${t['annual_per_mo']}/mo annual" if isinstance(t.get('annual_per_mo'), (int, float)) else "")
        for t in prices.get("tiers", [])
    ]
    out["severity"] = "confirmed"
    out["title"] = f"{brand.title()} ${int(amount)} doesn't match any tier"
    out["suggested_fix"] = (
        f"`{text}` doesn't match any current {brand.title()} tier. "
        f"Current tiers: {' · '.join(available)}. Update or remove."
    )
    out["source"] = "(cached pricing 2026-04-24)"
    out["source_note"] = ""
    return out


def verify_feature(f: dict) -> dict:
    meta = f.get("meta", {})
    subtype = meta.get("subtype", "")
    brand = (meta.get("brand") or "").lower()
    value = meta.get("value", "")
    text = f.get("text", "")

    out = dict(f)
    prices = PRICES.get(brand) or {}

    # Map subtype to a homepage_claims key when it's Synthesia
    if brand == "synthesia":
        homepage = prices.get("homepage_claims") or {}
        key = {"avatars": "avatars", "languages": "languages", "voices": "voices"}.get(subtype)
        if key and key in homepage:
            current = homepage[key]
            current_num = re.search(r"\d+", str(current))
            blog_num = re.search(r"\d+", value)
            if current_num and blog_num and int(current_num.group(0)) != int(blog_num.group(0)):
                # Numeric staleness — the page still works, the claim is just
                # mildly out of date. Mark `likely` (yellow), not confirmed (red).
                # Reserve `confirmed` for things that meaningfully break user
                # experience (dead links, missing tiers, wrong prices).
                out["severity"] = "likely"
                out["title"] = f"Synthesia {subtype} count slightly stale ({value} vs {current})"
                out["suggested_fix"] = (
                    f"Synthesia now advertises **{current} {subtype}** on the homepage. "
                    f"Worth refreshing '{value} {subtype}' → '{current} {subtype}' next time you "
                    "touch this page, but not urgent."
                )
                out["source"] = "https://www.synthesia.io"
                out["source_note"] = "homepage copy"
                return out
            else:
                out["severity"] = "unconfirmed"
                out["title"] = f"Synthesia {subtype} {value} still current"
                out["suggested_fix"] = "Matches current homepage. No action."
                out["source"] = "https://www.synthesia.io"
                out["source_note"] = ""
                return out

    if prices.get("unverified"):
        out["severity"] = "unconfirmed"
        out["title"] = f"{brand.title()} {subtype} count unverifiable"
        out["suggested_fix"] = f"Couldn't fetch {brand}'s pricing/features page. Verify `{text}` manually."
        out["source"] = ""
        out["source_note"] = ""
        return out

    # Generic competitor feature claim
    out["severity"] = "unconfirmed"
    out["title"] = f"{brand.title() if brand else 'Brand'} {subtype}: '{text}' — review"
    out["suggested_fix"] = f"Verify '{text}' against {brand}'s current marketing/pricing page."
    out["source"] = ""
    out["source_note"] = ""
    return out


def verify_stat(f: dict) -> dict:
    """
    Stats are noisy — a stat from 2023 can still be perfectly accurate (a
    survey result doesn't expire). The earlier rule promoted any 18-month-old
    year_ref to `likely` which produced too many false positives.

    Now: ALL body-level stat findings stay `unconfirmed`. The LLM-reasoning
    pass in the skill is responsible for surfacing the cases that matter
    (e.g. "best tools in 2023" used as a quality signal, or claims phrased
    in a way that admits being old). For dated *titles* see `verify_title`.
    """
    out = dict(f)
    text = f.get("text", "")
    out["severity"] = "unconfirmed"
    out["title"] = f"Stat needs review: '{text[:40]}'"
    out["suggested_fix"] = (
        f"Stat reference: `{text}`. Stats can stay relevant for years — only "
        "update if the underlying claim is clearly out of date or used as a "
        "freshness signal in the article."
    )
    out["source"] = ""
    out["source_note"] = ""
    return out


def verify_title(f: dict) -> dict:
    """
    Dated titles (H1 contains "in 2024" / "[April 2026]" / etc.) are
    high-impact — visible in search results, hurt CTR/AEO if outdated.

    Severity logic:
      - month-year reference >12 months old → confirmed (e.g. "[April 2024]")
      - month-year reference 5–12 months   → likely
      - bare-year reference older than last year → confirmed (e.g. "in 2024" today)
      - bare-year reference == last year        → likely (e.g. "in 2025" today, could still be valid context)

    For bare-year refs we don't display "X months old" — that's misleading
    since a "2025" mention doesn't pin to a specific date. We just say the
    year is outdated.
    """
    today = datetime.now(timezone.utc)
    current_year = today.year

    out = dict(f)
    meta = f.get("meta", {})
    subtype = meta.get("subtype", "")
    ref_year = meta.get("ref_year")
    matched = f.get("text", "")

    if subtype == "dated_title_month":
        months_old = int(meta.get("months_old") or 0)
        ref_month = meta.get("ref_month")
        sev = "confirmed" if months_old > 12 else "likely"
        out["title"] = (
            f"Title dated {ref_year}-{ref_month:02d} (~{months_old}mo old)"
            if ref_month else f"Title dated {ref_year}"
        )
        out["suggested_fix"] = (
            f"Title contains a dated reference '{matched}' (~{months_old} months old). "
            "Update to the current month/year, or remove the date stamp — dated titles "
            "in search results lose CTR fast."
        )
    else:
        # Bare year — don't say "X months old", just flag the year as outdated
        year_diff = current_year - (ref_year or current_year)
        sev = "confirmed" if year_diff > 1 else "likely"
        out["title"] = f"Title references outdated year ({ref_year})"
        out["suggested_fix"] = (
            f"Title contains the year '{ref_year}' which is no longer current "
            f"(today is {today.year}). Update to the current year or drop the "
            "year stamp so the article doesn't need annual renames."
        )

    out["severity"] = sev
    out["source"] = ""
    out["source_note"] = "Detected from H1."
    return out


def verify_link(f: dict) -> dict:
    out = dict(f)
    out["severity"] = "needs_check"
    out["title"] = f"Link to {f.get('meta', {}).get('domain', 'external site')}"
    out["suggested_fix"] = ""  # filled in after HEAD check
    out["source"] = ""
    out["source_note"] = ""
    return out


def verify_ai_news(f: dict) -> dict:
    out = dict(f)
    model = f.get("meta", {}).get("model", "")
    out["severity"] = "unconfirmed"
    out["title"] = f"AI model mention: {model}"
    out["suggested_fix"] = (
        f"Verify whether '{model}' is still the current/relevant model for this comparison; "
        "newer model tiers ship frequently."
    )
    out["source"] = ""
    out["source_note"] = ""
    return out


def verify_meta(f: dict) -> dict:
    """
    Stale meta title / meta description references. Same logic as
    verify_title — month-year refs use months_old; bare-year refs just
    flag the year. Meta is even higher CTR impact than H1 — it's what
    shows in Google search snippets.
    """
    today = datetime.now(timezone.utc)
    current_year = today.year

    out = dict(f)
    meta = f.get("meta", {})
    subtype = meta.get("subtype", "meta_title")
    date_subtype = meta.get("date_subtype")
    months_old = int(meta.get("months_old") or 0)
    ref_year = meta.get("ref_year")
    matched = f.get("text", "")
    field = "Meta title" if subtype == "meta_title" else "Meta description"

    if date_subtype == "month" and meta.get("ref_month"):
        sev = "confirmed" if months_old > 12 else "likely"
        out["title"] = f"{field} dated {ref_year}-{meta['ref_month']:02d} (~{months_old}mo)"
        out["suggested_fix"] = (
            f"{field} contains '{matched}' (~{months_old} months old). "
            "This is what shows in Google search snippets — update to the current "
            "month/year in the CMS to keep CTR."
        )
    else:
        year_diff = current_year - (ref_year or current_year)
        sev = "confirmed" if year_diff > 1 else "likely"
        out["title"] = f"{field} references outdated year ({ref_year})"
        out["suggested_fix"] = (
            f"{field} contains the year '{ref_year}' (today is {today.year}). "
            "This is what shows in Google search snippets — update the year "
            "or drop the year stamp."
        )

    out["severity"] = sev
    out["source"] = ""
    out["source_note"] = f"Detected from {field.lower()}."
    return out


def verify_one(f: dict, page_brand: str | None) -> dict:
    t = f.get("type")
    if t == "pricing":
        return verify_pricing(f, page_brand)
    if t == "feature":
        return verify_feature(f)
    if t == "stat":
        return verify_stat(f)
    if t == "link":
        return verify_link(f)
    if t == "ai-news":
        return verify_ai_news(f)
    if t == "title":
        return verify_title(f)
    if t == "meta":
        return verify_meta(f)
    f["severity"] = "unconfirmed"
    f["title"] = f"{t}: review"
    return f


def main():
    if len(sys.argv) != 2:
        print("usage: verify_findings.py <slug>", file=sys.stderr)
        sys.exit(1)
    slug = sys.argv[1]
    findings_path = ROOT / "drafts" / f"{slug}.findings.json"
    out_path = ROOT / "drafts" / f"{slug}.verified.json"

    data = json.load(open(findings_path))
    raw = data.get("findings", [])
    page_brand = page_brand_from_slug(slug)

    verified = [verify_one(f, page_brand) for f in raw]

    counts_by_severity = {}
    for f in verified:
        counts_by_severity[f.get("severity", "unconfirmed")] = counts_by_severity.get(f.get("severity", "unconfirmed"), 0) + 1

    out = {
        "slug": slug,
        "page_brand": page_brand,
        "total_findings": len(verified),
        "by_severity": counts_by_severity,
        "findings": verified,
    }
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps({
        "slug": slug,
        "by_severity": counts_by_severity,
        "total": len(verified),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
