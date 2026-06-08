#!/usr/bin/env python3
"""
Regex-extract structured volatile claims from article text.

Emits a JSON list of claim dicts, each with:
  - type: "pricing" | "stat" | "link" | "ai-news"
  - text: the literal match
  - context: ~200 chars surrounding the match
  - span: [start, end] char offsets
  - meta: extra per-type info (e.g., detected competitor, model name, link URL)

Does NOT verify. Verification is the skill's job (uses MCPs + web search).

Usage:
  echo "<article text>" | python3 extract_claims.py
  python3 extract_claims.py < article.txt
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config.json"


_MONTH_TO_NUM = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MONTH_YEAR_RE = re.compile(
    r"\b(?P<month>january|february|march|april|may|june|july|august|"
    r"september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"
    r"[ \-,/]+(?P<year>20\d{2})\b",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"\b(?P<year>20\d{2})\b")
_TITLE_DATE_PHRASES = re.compile(
    # "best X of 2024", "in 2023", "for 2025", "[2026]", "(april 2026)" — common dated-title shapes
    r"(?:\b(?:in|for|of|best|top|guide(?:\s+to)?|how\s+to|complete)[\w\s\-]{0,30}\b)?"
    r"(?:\[|\()?\s*"
    r"(?:(?P<m>january|february|march|april|may|june|july|august|september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)[ ,/\-]+)?"
    r"(?P<y>20\d{2})\s*(?:\]|\))?",
    re.IGNORECASE,
)


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


# Headings that mark the END of article body on Synthesia blog posts.
# Everything from the first match onwards is page-template noise.
_ARTICLE_END_MARKERS = (
    re.compile(r"^#{2,4}\s+You\s+might\s+also\s+like\b", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^#{2,4}\s+Ready\s+to\s+try\s+our\s+AI\s+video\s+platform", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^#{2,4}\s+About\s+Synthesia\b", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^#{2,4}\s+Leader\s+in\s+the\s+AI\s+Video\s+Generator\s+category", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^#{2,4}\s+Related\s+(?:reads?|articles?|posts?)\b", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^#{2,4}\s+Get\s+started\s+with\s+Synthesia\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^#{2,4}\s+Frequently\s+asked\s+questions?\s*$", re.IGNORECASE | re.MULTILINE),
)


def restrict_to_article_body(text: str) -> str:
    """
    For blog posts (/post/*), trim the surrounding page template:

      [TEMPLATE: top banner / sticky CTA / nav]
      # Article Title          <-- H1: start of article body
      ...article content...
      ## You might also like   <-- one of the template markers below: end of body
      [TEMPLATE: related posts / pre-footer / about-synthesia / footer]

    Cuts:
      - Everything before the first H1 (`# `) heading.
      - Everything from the first article-end marker onwards.

    If no H1 is found (e.g. scrape didn't include it), return the original
    text — better to over-extract than miss real findings.
    """
    h1_match = re.search(r"(?m)^#\s+\S", text)
    start = h1_match.start() if h1_match else 0

    end = len(text)
    for pat in _ARTICLE_END_MARKERS:
        m = pat.search(text, pos=start)
        if m and m.start() < end:
            end = m.start()

    if start >= end:
        return text  # safety: don't return empty content
    return text[start:end]


_FRAGMENT_HEADING_RE = re.compile(r"^(#{1,6})\s+(.{1,6})\s*$")


def collapse_fragmented_headings(text: str) -> str:
    """
    Some marketing pages render a price like "$29/seat" by wrapping each
    character in its own H2 tag:

        ## $
        ## 29
        ## /
        ## seat

    Firecrawl scrapes that verbatim, which breaks pricing regex that expects
    the full token on one line. This helper collapses runs of consecutive
    very-short-content headings (<= 4 chars of payload) into a single inline
    line joining them with no separator. Blank lines inside a run are
    treated as separators, not breaks.

    Real section headings (longer content) are preserved untouched so
    `_all_headings()` still reports a useful location.
    """
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        m = _FRAGMENT_HEADING_RE.match(stripped)
        if not m or len(m.group(2).strip()) > 4:
            out.append(line)
            i += 1
            continue
        # Start of a possible run. Consume consecutive short headings
        # (allowing single blank lines between them).
        parts: list[str] = []
        j = i
        last_real = i
        while j < n:
            s = lines[j].strip()
            mm = _FRAGMENT_HEADING_RE.match(s)
            if mm and len(mm.group(2).strip()) <= 4:
                parts.append(mm.group(2).strip())
                last_real = j
                j += 1
            elif s == "" and parts:
                j += 1
            else:
                break
        if len(parts) >= 2:
            out.append("".join(parts))
            i = last_real + 1
        else:
            out.append(line)
            i += 1
    return "\n".join(out)


def context_window(text: str, start: int, end: int, pad: int = 100) -> str:
    """
    ~`pad` chars on each side of the match, rounded to word boundaries so
    we don't return half-words like "rPoint presentations" (truncated
    "PowerPoint"). If the rounded boundary lands inside a word, walk
    outward to the nearest whitespace.
    """
    lo = max(0, start - pad)
    hi = min(len(text), end + pad)

    # Walk lo backward to the nearest whitespace (or start of text).
    if lo > 0 and not text[lo - 1].isspace() and not text[lo].isspace():
        ws = text.rfind(" ", 0, lo)
        nl = text.rfind("\n", 0, lo)
        boundary = max(ws, nl)
        if boundary != -1:
            lo = boundary + 1

    # Walk hi forward to the nearest whitespace (or end of text).
    if hi < len(text) and not text[hi - 1].isspace() and not text[hi].isspace():
        ws = text.find(" ", hi)
        nl = text.find("\n", hi)
        candidates = [c for c in (ws, nl) if c != -1]
        if candidates:
            hi = min(candidates)

    snippet = text[lo:hi].replace("\n", " ").strip()
    return re.sub(r"\s+", " ", snippet)


def extract_sentence(text: str, start: int, end: int, max_chars: int = 500) -> str:
    """
    Return the full sentence (or paragraph) containing the match, so the
    Notion finding shows the actual copy a writer needs to edit instead of
    a chopped char-window. Boundaries: `.`/`?`/`!` followed by space/newline,
    OR a blank line, OR `max_chars` away from the match.

    Defensive: if `start`/`end` are out of range (e.g. caller passed body
    text but the span came from HTML), return empty.
    """
    n = len(text)
    if not text or start < 0 or start >= n:
        return ""
    end = min(end, n)

    # Walk back to find sentence start
    sent_start = max(0, start - max_chars)
    for i in range(start - 1, sent_start, -1):
        c = text[i]
        if c in ".!?" and i + 1 < n and text[i + 1] in " \n\t":
            sent_start = i + 2
            break
        if c == "\n" and i > 0 and text[i - 1] == "\n":
            sent_start = i + 1
            break

    # Walk forward to find sentence end
    sent_end = min(n, end + max_chars)
    for i in range(end, sent_end):
        c = text[i]
        if c in ".!?" and (i + 1 == n or text[i + 1] in " \n\t"):
            sent_end = i + 1
            break
        if c == "\n" and i + 1 < n and text[i + 1] == "\n":
            sent_end = i
            break

    snippet = text[sent_start:sent_end].replace("\n", " ").strip()
    snippet = re.sub(r"\s+", " ", snippet)
    # Trim leading/trailing markdown punctuation noise
    snippet = snippet.lstrip("*_-#> ").rstrip("*_-> ")
    return snippet


def _all_headings(text: str) -> list[dict]:
    """All markdown headings in the text, in document order."""
    headings = []
    for m in re.finditer(r"(?m)^(#{1,6})\s+(.+?)\s*$", text):
        line_no = text.count("\n", 0, m.start()) + 1
        headings.append({
            "level": len(m.group(1)),
            "title": m.group(2).strip(),
            "pos": m.start(),
            "line": line_no,
        })
    return headings


def _location_for(text: str, position: int, headings: list[dict]) -> dict:
    """Return the nearest preceding heading (heading + line_number)."""
    nearest = None
    for h in headings:
        if h["pos"] <= position:
            nearest = h
        else:
            break
    line_no = text.count("\n", 0, position) + 1
    if nearest is None:
        return {"heading": "(before first heading)", "heading_level": 0, "line": line_no}
    return {
        "heading": nearest["title"],
        "heading_level": nearest["level"],
        "line": line_no,
    }


def _brand_positions(text: str, brands: list[str]) -> list[tuple[int, int, str]]:
    positions = []
    for brand in brands:
        for m in re.finditer(rf"\b{re.escape(brand)}\b", text, flags=re.IGNORECASE):
            positions.append((m.start(), m.end(), brand))
    return positions


def _find_nearest_brand(
    pos: int, brand_positions: list[tuple[int, int, str]], max_distance: int = 200
) -> str | None:
    best = None
    best_dist = max_distance + 1
    for (bs, be, brand) in brand_positions:
        d = min(abs(pos - bs), abs(pos - be))
        if d < best_dist:
            best_dist = d
            best = brand
    return best


def extract_pricing(text: str, cfg: dict) -> list[dict]:
    """
    Flag money amounts near brand/competitor names.
    Pattern: currency + number + optional /mo|/yr + within ~120 chars of a brand.
    """
    findings = []
    brands = ["Synthesia"] + list(cfg["competitors"].keys())
    brand_positions = _brand_positions(text, brands)

    # Require an explicit price suffix (/mo, per month, etc.) — bare "$N" is too noisy.
    # This intentionally drops corporate-finance amounts like "$100 million ARR".
    price_pattern = re.compile(
        r"(?P<full>(?P<sym>[\$€£])\s?(?P<num>\d{1,4}(?:[,\.]\d{1,3})?)"
        r"\s?(?P<suffix>/mo|/month|/yr|/year|/seat|/user|"
        r"per\s+month|per\s+year|per\s+seat|per\s+user|monthly|annually|/yearly))",
        re.IGNORECASE,
    )

    for m in price_pattern.finditer(text):
        # Reject if immediately followed by a magnitude word (million/billion/thousand/M/B/K)
        tail = text[m.end():m.end() + 20].lstrip()
        if re.match(r"(million|billion|thousand|[MmBbKk]\b)", tail, re.IGNORECASE):
            continue
        near_brand = _find_nearest_brand(m.start(), brand_positions, max_distance=120)
        if near_brand is None:
            continue
        findings.append({
            "type": "pricing",
            "text": m.group("full"),
            "context": context_window(text, m.start(), m.end()),
            "span": [m.start(), m.end()],
            "meta": {
                "brand": near_brand,
                "currency": m.group("sym"),
                "amount": m.group("num"),
            },
        })
    return findings


def extract_brand_features(text: str, cfg: dict) -> list[dict]:
    """
    Structured numeric brand-feature claims that go stale:
      - avatar counts ("125+ AI avatars")
      - language counts ("140+ languages")
      - voice counts ("500+ voices")
      - templates, integrations, custom fonts
      - video duration limits ("max 5 minutes per video", "up to 30 min")
      - video/month limits ("10 minutes/month", "30 videos per month")

    Each must be near a brand name (Synthesia or a competitor) within 200 chars.
    Qualitative feature claims (e.g. "Synthesia doesn't support X") are handled
    by the LLM's prose-reasoning step at verification time, not here.
    """
    findings = []
    brands = ["Synthesia"] + list(cfg["competitors"].keys())
    brand_positions = _brand_positions(text, brands)

    patterns = [
        (re.compile(r"\b(\d{1,4}\+?)\s+(?:AI\s+|stock\s+|digital\s+)?avatars?\b", re.IGNORECASE), "avatars"),
        (re.compile(r"\b(\d{1,3}\+?)\s+languages?\b", re.IGNORECASE), "languages"),
        (re.compile(r"\b(\d{1,4}\+?)\s+(?:AI\s+)?voices?\b", re.IGNORECASE), "voices"),
        (re.compile(r"\b(\d{1,4}\+?)\s+templates?\b", re.IGNORECASE), "templates"),
        (re.compile(r"\b(\d{1,4}\+?)\s+integrations?\b", re.IGNORECASE), "integrations"),
        (re.compile(r"\b(\d{1,3}\+?)\s+(?:accents?|dialects?)\b", re.IGNORECASE), "accents"),
        (
            re.compile(
                r"\b(?:max\.?|maximum|up to|limited to)\s+(\d{1,4})\s+(?:min|minutes?|sec|seconds?)\b",
                re.IGNORECASE,
            ),
            "duration_limit",
        ),
        (
            re.compile(
                r"\b(\d{1,4})\s+(?:min|minutes?|hours?)\s*(?:/|per)\s*(?:mo|month|year|yr)\b",
                re.IGNORECASE,
            ),
            "volume_per_period",
        ),
        (
            re.compile(
                r"\b(\d{1,4})\s+(?:videos?|renders?)\s*(?:/|per)\s*(?:mo|month|year|yr)\b",
                re.IGNORECASE,
            ),
            "videos_per_period",
        ),
    ]

    for pat, subtype in patterns:
        for m in pat.finditer(text):
            near_brand = _find_nearest_brand(m.start(), brand_positions, max_distance=200)
            if near_brand is None:
                continue
            findings.append({
                "type": "feature",
                "text": m.group(0).strip(),
                "context": context_window(text, m.start(), m.end()),
                "span": [m.start(), m.end()],
                "meta": {
                    "subtype": subtype,
                    "brand": near_brand,
                    "value": m.group(1),
                },
            })
    return findings


def extract_stats(text: str) -> list[dict]:
    """
    Numeric claims that tend to go stale:
      - "N%" (any percent)
      - "Nx" multiplier claims
      - explicit year references ("in 2023", "as of 2024", "since 2022")
      - large round-number claims ("50,000 customers", "2 billion videos")
    """
    findings = []
    patterns = [
        (re.compile(r"\b\d{1,4}(?:\.\d+)?\s?%"), "percent"),
        (re.compile(r"\b\d{1,3}(?:\.\d+)?x\b", re.IGNORECASE), "multiplier"),
        (re.compile(r"\b(?:in|as of|since|by)\s+(20\d{2})\b", re.IGNORECASE), "year_ref"),
        (
            re.compile(
                r"\b(?:over|more than|nearly|around|about|approximately)?\s*"
                r"\d{1,3}(?:,\d{3})+\s+(?:customers|companies|users|videos|hours|organizations|teams|businesses)\b",
                re.IGNORECASE,
            ),
            "large_count",
        ),
        (
            re.compile(
                r"\b\d{1,3}(?:\.\d+)?\s+(?:million|billion|thousand)\s+(?:customers|companies|users|videos|hours|views)\b",
                re.IGNORECASE,
            ),
            "large_magnitude",
        ),
    ]
    for pat, subtype in patterns:
        for m in pat.finditer(text):
            findings.append({
                "type": "stat",
                "text": m.group(0).strip(),
                "context": context_window(text, m.start(), m.end()),
                "span": [m.start(), m.end()],
                "meta": {"subtype": subtype},
            })
    return findings


INTERNAL_DOMAINS = {"synthesia.io", "www.synthesia.io"}

# Domains that only serve the site's own static assets — skip entirely.
ASSET_DOMAIN_PREFIXES = (
    "cdn.prod.website-files.com",  # Webflow CDN
    "assets.website-files.com",
    "uploads-ssl.webflow.com",
    "global-uploads.webflow.com",
)

# File extensions that indicate an asset, not a navigable page.
ASSET_EXTS = re.compile(
    r"\.(svg|png|jpe?g|gif|webp|avif|ico|bmp|tiff?|"
    r"css|js|mjs|map|woff2?|ttf|otf|eot|"
    r"mp4|webm|ogg|mp3|wav|m4a|"
    r"pdf|zip|tar|gz)(\?|$)",
    re.IGNORECASE,
)

# YouTube thumbnail URLs (img.youtube.com/vi/<id>/*.jpg) — not navigable.
YT_THUMB_RE = re.compile(r"^https?://(?:i\d?\.ytimg\.com|img\.youtube\.com)/")


def _is_asset_url(url: str, domain: str) -> bool:
    if any(domain == d or domain.endswith("." + d) for d in ASSET_DOMAIN_PREFIXES):
        return True
    if YT_THUMB_RE.match(url):
        return True
    if ASSET_EXTS.search(url):
        return True
    return False


_MD_LINK_RE = re.compile(r"\[([^\]]{1,200})\]\((https?://[^)\s]+)\)")
_HTML_ANCHOR_RE = re.compile(
    r'<a\s[^>]*?href=["\'](?P<url>https?://[^"\']+)["\'][^>]*>(?P<anchor>.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)


def _clean_anchor(s: str) -> str:
    # Strip nested HTML tags + collapse whitespace
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:200]


def extract_links(text: str, html: str | None = None) -> list[dict]:
    """
    External *navigable* links worth HEAD-checking. Filters out the site's
    own static asset URLs (images, stylesheets, fonts, media). Captures
    anchor text when the link came from an HTML <a> tag or a markdown
    `[anchor](url)` form.
    """
    findings = []
    by_url: dict[str, dict] = {}

    def add(url: str, span: tuple[int, int], anchor: str | None = None):
        url_clean = url.rstrip(".,);:\"'")
        domain_match = re.search(r"https?://([^/]+)", url_clean)
        if not domain_match:
            return
        domain = domain_match.group(1).lower()
        if domain in INTERNAL_DOMAINS:
            return
        if _is_asset_url(url_clean, domain):
            return
        existing = by_url.get(url_clean)
        if existing is None:
            f = {
                "type": "link",
                "text": url_clean,
                "context": "",
                "span": list(span),
                "meta": {"domain": domain, "anchor": anchor or ""},
            }
            by_url[url_clean] = f
            findings.append(f)
        else:
            # Prefer non-empty anchor if a later match has one
            if anchor and not existing["meta"].get("anchor"):
                existing["meta"]["anchor"] = anchor

    # 1. Markdown `[anchor](url)` — most reliable anchor source for blog posts
    for m in _MD_LINK_RE.finditer(text):
        anchor = _clean_anchor(m.group(1))
        add(m.group(2), (m.start(2), m.end(2)), anchor=anchor)

    # 2. Bare URLs in text (no anchor available)
    url_re = re.compile(r"https?://[^\s\"'<>)\]]+")
    for m in url_re.finditer(text):
        add(m.group(0), (m.start(), m.end()))

    # 3. Raw HTML <a href="..."></a> — fallback if html is supplied
    if html:
        for m in _HTML_ANCHOR_RE.finditer(html):
            anchor = _clean_anchor(m.group("anchor"))
            add(m.group("url"), (m.start(), m.end()), anchor=anchor)

    return findings


def _months_old(ref: date, today: date) -> int:
    return (today.year - ref.year) * 12 + (today.month - ref.month)


def extract_dated_titles(text: str, today: date | None = None, max_age_months: int = 5) -> list[dict]:
    """
    Flag H1s / page titles that contain a year or month-year reference more
    than `max_age_months` old (default 5). Examples:
      - "Top 5 Clipchamp Alternatives For Video Editing (In 2024)"   → stale
      - "How to Reduce Training Costs [April 2026]"                 → fresh today
      - "AI Statistics 2025: Top Trends, Usage Data and Insights"   → stale by Jul 2026

    Year-only references resolve to year-end (Dec of that year). Month-year
    references resolve to the first of that month. The extractor only inspects
    the first H1 (the article title).
    """
    today = today or date.today()
    cutoff_date = date(today.year, today.month, 1)
    findings: list[dict] = []

    h1 = re.search(r"(?m)^#\s+(?P<title>.+?)\s*$", text)
    if not h1:
        return findings
    title_text = h1.group("title")
    title_start = h1.start("title")

    # Try month-year match first (more specific). If a month-year is present,
    # it WINS — return whatever it produces and skip year-only fallback,
    # otherwise we'd double-flag a fresh "November 2025" as if it were a
    # bare "2025" reference.
    m = _MONTH_YEAR_RE.search(title_text)
    if m:
        month_key = m.group("month").lower()[:3]
        month_num = _MONTH_TO_NUM.get(month_key)
        year = int(m.group("year"))
        if month_num:
            ref = date(year, month_num, 1)
            months_old = (cutoff_date.year - ref.year) * 12 + (cutoff_date.month - ref.month)
            if months_old > max_age_months:
                span_start = title_start + m.start()
                span_end = title_start + m.end()
                findings.append({
                    "type": "title",
                    "text": m.group(0),
                    "context": title_text,
                    "span": [span_start, span_end],
                    "meta": {
                        "subtype": "dated_title_month",
                        "ref_year": year,
                        "ref_month": month_num,
                        "months_old": months_old,
                    },
                })
            return findings  # month-year is decisive — don't fall through

    # Year-only fallback. Use Jan 1 of the referenced year — a title saying
    # "2025" in April 2026 should be considered stale, not "fresh until Dec".
    m = _YEAR_RE.search(title_text)
    if m:
        year = int(m.group("year"))
        ref = date(year, 1, 1)
        months_old = (cutoff_date.year - ref.year) * 12 + (cutoff_date.month - ref.month)
        if months_old > max_age_months:
            span_start = title_start + m.start()
            span_end = title_start + m.end()
            findings.append({
                "type": "title",
                "text": m.group(0),
                "context": title_text,
                "span": [span_start, span_end],
                "meta": {
                    "subtype": "dated_title_year",
                    "ref_year": year,
                    "months_old": months_old,
                },
            })
    return findings


def _check_dated_string(s: str, today: date, max_age_months: int) -> tuple[dict, str] | None:
    """
    Run the dated-title detection on an arbitrary string. Returns
    ({subtype, ref_year, ref_month?, months_old, span: [start,end], text}, raw_match)
    if the string contains a stale date, else None. month-year wins; year-only is fallback.
    """
    if not s:
        return None
    cutoff_date = date(today.year, today.month, 1)
    m = _MONTH_YEAR_RE.search(s)
    if m:
        month_key = m.group("month").lower()[:3]
        month_num = _MONTH_TO_NUM.get(month_key)
        year = int(m.group("year"))
        if month_num:
            ref = date(year, month_num, 1)
            months_old = (cutoff_date.year - ref.year) * 12 + (cutoff_date.month - ref.month)
            if months_old > max_age_months:
                return ({
                    "subtype_suffix": "month",
                    "ref_year": year,
                    "ref_month": month_num,
                    "months_old": months_old,
                    "span": [m.start(), m.end()],
                    "match_text": m.group(0),
                }, m.group(0))
            return None  # month-year present but fresh — short-circuit
    m2 = _YEAR_RE.search(s)
    if m2:
        year = int(m2.group("year"))
        ref = date(year, 1, 1)
        months_old = (cutoff_date.year - ref.year) * 12 + (cutoff_date.month - ref.month)
        if months_old > max_age_months:
            return ({
                "subtype_suffix": "year",
                "ref_year": year,
                "months_old": months_old,
                "span": [m2.start(), m2.end()],
                "match_text": m2.group(0),
            }, m2.group(0))
    return None


def extract_meta_dated(metadata: dict, today: date | None = None, max_age_months: int = 5) -> list[dict]:
    """
    Check meta title and meta description for stale year / month-year refs.
    Same staleness rules as `extract_dated_titles`, but type=`meta` so it
    gets its own tag and weight.

    `metadata` is the dict from Firecrawl's scrape response — looks at
    `title`/`ogTitle` (first non-empty wins) and `description`/`ogDescription`.
    """
    today = today or date.today()
    findings: list[dict] = []
    if not isinstance(metadata, dict):
        return findings

    meta_title = metadata.get("title") or metadata.get("ogTitle") or metadata.get("metaTitle") or ""
    meta_desc = metadata.get("description") or metadata.get("ogDescription") or metadata.get("metaDescription") or ""

    for label, value in (("meta_title", meta_title), ("meta_description", meta_desc)):
        result = _check_dated_string(value, today, max_age_months)
        if not result:
            continue
        info, _ = result
        findings.append({
            "type": "meta",
            "text": info["match_text"],
            "context": value,
            "span": info["span"],  # offsets within the meta value, not the body
            "meta": {
                "subtype": label,                    # meta_title | meta_description
                "date_subtype": info["subtype_suffix"],  # year | month
                "ref_year": info["ref_year"],
                "ref_month": info.get("ref_month"),
                "months_old": info["months_old"],
                "field_value": value,
            },
        })
    return findings


def extract_ai_models(text: str, cfg: dict) -> list[dict]:
    """Mentions of specific AI model versions that age fast."""
    findings = []
    for term in cfg["ai_model_terms"]:
        pat = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        for m in pat.finditer(text):
            findings.append({
                "type": "ai-news",
                "text": m.group(0),
                "context": context_window(text, m.start(), m.end()),
                "span": [m.start(), m.end()],
                "meta": {"model": term},
            })
    return findings


def dedupe_by_span(findings: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for f in findings:
        key = (f["type"], tuple(f["span"]), f["text"])
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def extract_all(text: str, html: str | None = None, article_body_only: bool = False, metadata: dict | None = None) -> list[dict]:
    cfg = load_config()
    if article_body_only:
        # Strip page template (top banner, related posts, pre-footer, about-synthesia, etc.)
        text = restrict_to_article_body(text)
    # Pre-process to recover prices that were split across per-char headings.
    text = collapse_fragmented_headings(text)
    all_findings = []
    all_findings.extend(extract_pricing(text, cfg))
    all_findings.extend(extract_brand_features(text, cfg))
    all_findings.extend(extract_dated_titles(text))
    all_findings.extend(extract_meta_dated(metadata or {}))
    all_findings.extend(extract_stats(text))
    all_findings.extend(extract_links(text, html))
    all_findings.extend(extract_ai_models(text, cfg))
    deduped = dedupe_by_span(all_findings)

    # Annotate every finding with section location + the FULL sentence it
    # appears in (so the Notion page shows the actual copy, not a chopped
    # context window). For meta findings the span is in the meta value, not
    # the body — fall back to the meta value itself as the "sentence".
    headings = _all_headings(text)
    for f in deduped:
        start, end = f["span"]
        if f.get("type") == "meta":
            # Span is into the meta value, not the body text — skip body location.
            f["location"] = {"heading": "Meta tags", "heading_level": 0, "line": None}
            f["sentence"] = (f.get("meta", {}).get("field_value") or f.get("context") or "").strip()
        elif f.get("type") == "link":
            # Link findings render URL + anchor directly; sentence is optional
            # and may have an HTML-derived span that doesn't map to body text.
            if 0 <= start < len(text):
                f["location"] = _location_for(text, start, headings)
                f["sentence"] = extract_sentence(text, start, end)
            else:
                f["location"] = {"heading": "(link found in HTML only)", "heading_level": 0, "line": None}
                f["sentence"] = ""
        else:
            f["location"] = _location_for(text, start, headings)
            f["sentence"] = extract_sentence(text, start, end)
    return deduped


def main():
    raw = sys.stdin.read()
    # Accept either plain text or a JSON {"text": ..., "html": ..., "article_body_only": bool, "metadata": {...}} payload.
    html = None
    article_body_only = False
    metadata = None
    if raw.lstrip().startswith("{"):
        try:
            payload = json.loads(raw)
            text = payload.get("text", "")
            html = payload.get("html")
            article_body_only = bool(payload.get("article_body_only", False))
            metadata = payload.get("metadata")
        except json.JSONDecodeError:
            text = raw
    else:
        text = raw

    findings = extract_all(text, html=html, article_body_only=article_body_only, metadata=metadata)
    counts = {}
    for f in findings:
        counts[f["type"]] = counts.get(f["type"], 0) + 1

    print(json.dumps({
        "counts": counts,
        "total": len(findings),
        "findings": findings,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
