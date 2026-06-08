#!/usr/bin/env python3
"""Discover affiliate-intent pages promoting AI video competitors.

Pipeline:
1. Firecrawl search across affiliate-intent queries (alternatives / best-of / review / comparison)
2. Dedupe URLs across queries
3. Scrape each candidate (markdown + HTML) via Firecrawl
4. Detect three signals on every page:
     - Affiliate URL patterns in outbound <a href=> links (e.g. ?ref=, ?aff_id=, /go/,
       known networks like impact.com / partnerstack / rewardful / awin / cj / clickbank)
     - Affiliate-disclosure phrases in the text
     - Synthesia presence (page text OR any link to synthesia.io)
5. Classify into tiers:
     - Tier A: mentions Synthesia AND has affiliate intent
                 → pitch: "monetize what you're already doing — apply to our program"
     - Tier B: does NOT mention Synthesia AND has affiliate intent AND mentions 2+ competitors
                 → pitch: "we beat HeyGen on cookie + lifetime value — add us"
     - Skip: no affiliate intent, or single-competitor pages with no affiliate signals
6. Write surviving rows to a campaign tab (default: competitor-affiliates).

Usage:
  python3 discover_competitor_affiliates.py [--campaign <slug>] [--limit-queries N]
                                            [--limit-scrape N] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from firecrawl import FirecrawlApp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sheets_helper import append_rows, ensure_master_sheet, sheet_url, update_summary  # noqa: E402
from filter_articles import is_article_url  # noqa: E402

ssl._create_default_https_context = ssl._create_unverified_context

PROJECT_ROOT = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects")
CONFIG_PATH = PROJECT_ROOT / "link-outreach" / "config.json"
FIRECRAWL_API_KEY = (PROJECT_ROOT / ".credentials" / "firecrawl-api-key.txt").read_text().strip()

# ─── search queries ─────────────────────────────────────────────────────
ALTERNATIVE_QUERIES = [
    "best HeyGen alternatives", "best HeyGen alternatives 2024",
    "best Veed alternatives", "best Veed.io alternatives",
    "best D-ID alternatives",
    "best Colossyan alternatives",
    "best Hour One alternatives", "best HourOne alternatives",
    "best InVideo alternatives",
    "best DeepBrain AI alternatives",
    "best Vyond alternatives",
    "best Descript alternatives",
    "best Runway alternatives",
    "best Luma AI alternatives",
    "best Kling AI alternatives",
]
CATEGORY_QUERIES = [
    "best AI video generators 2024",
    "best AI video tools",
    "best AI avatar tools",
    "best AI video generator for marketing",
    "best text to video AI",
    "top AI video editing software",
    "best AI video maker for business",
    "best AI talking head video",
    "best AI video for e-learning",
    "best AI explainer video tools",
    "best AI corporate video tools",
    "best AI presenter video",
]
REVIEW_QUERIES = [
    "HeyGen review", "Veed.io review", "D-ID review", "Colossyan review",
    "Hour One review", "InVideo review", "DeepBrain review",
    "Descript review", "Runway ML review", "Vyond review",
]
COMPARISON_QUERIES = [
    "HeyGen vs Synthesia", "Veed vs Synthesia", "Colossyan vs Synthesia",
    "D-ID vs Synthesia", "Runway vs HeyGen", "DeepBrain vs HeyGen",
]
DEFAULT_QUERIES = ALTERNATIVE_QUERIES + CATEGORY_QUERIES + REVIEW_QUERIES + COMPARISON_QUERIES

# ─── affiliate / disclosure detection ───────────────────────────────────
AFFILIATE_URL_PATTERNS = [
    r"[?&](ref|aff|affiliate|partner|partner_id|aff_id|affiliate_id|via)=",
    r"utm_(source|medium)=affiliate",
    r"/(?:go|aff|affiliate|recommends?|out|redirect|r)/",
    r"//(?:impact|impactradius|partnerstack|tapfiliate|rewardful|awin1?|cj\.dotomi|clickbank|tune|shareasale|tradetracker|tradedoubler)\.com",
    r"//(?:get|join|try)\.[a-z0-9-]+\.com",  # try.heygen.com, join.veed.io, etc.
]
AFFILIATE_URL_RE = re.compile("|".join(AFFILIATE_URL_PATTERNS), re.IGNORECASE)

DISCLOSURE_PHRASES = [
    "affiliate link", "affiliate disclosure", "affiliate disclaimer",
    "we may earn", "we earn a commission", "earn a commission",
    "may receive a commission", "may be paid a commission",
    "this post contains affiliate", "this site contains affiliate",
    "as an amazon associate",
    "compensation when you", "compensated when you",
]
DISCLOSURE_RE = re.compile("|".join(re.escape(p) for p in DISCLOSURE_PHRASES), re.IGNORECASE)

SYNTHESIA_RE = re.compile(r"\bsynthesia\b", re.IGNORECASE)

# AI video / avatar / TTS tools beyond config.competitors — page-domain self-promo guard.
# These tools write "X alternatives" articles to promote themselves; they'll never join an affiliate program.
KNOWN_AI_TOOL_DOMAINS = {
    "jogg.ai", "rask.ai", "creatify.ai", "immersive-fox.com",
    "tavus.io", "kreadoai.com", "fliki.ai", "pictory.ai",
    "lumen5.com", "animaker.com", "doodly.com", "videoscribe.com",
    "biteable.com", "powtoon.com", "wibbitz.com", "raw.studio",
    "speechify.com", "happyscribe.com", "recast.studio", "supademo.com",
    "quso.ai", "arcade.software", "eesel.ai", "puppydog.io",
    "vidmetoo.com", "ahrefs.com", "semrush.com",
}

# Platform / builder / social / news / aggregator hosts where pages aren't editable
# by the page-owning publisher in the way we need for outreach. Exclude these.
PLATFORM_HOSTS = {
    # video / social
    "youtube.com", "youtu.be", "vimeo.com", "tiktok.com", "dailymotion.com",
    "facebook.com", "fb.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "pinterest.com", "tumblr.com", "mastodon.social", "threads.net",
    "reddit.com", "quora.com",
    # messaging
    "t.me", "telegram.me", "wa.me", "discord.gg", "discord.com",
    # podcast platforms
    "spotify.com", "buzzsprout.com", "soundcloud.com", "podigee.io", "pocketcasts.com",
    "iheart.com", "castbox.fm", "goodpods.com", "ivoox.com", "ardsounds.de",
    "matchmaker.fm", "captivate.fm", "podscan.fm", "podme.com", "ausha.co",
    # newsletters / blog builders
    "substack.com", "beehiiv.com", "mailchi.mp", "kit.com", "medium.com", "readmedium.com",
    "ghost.io", "paragraph.com", "typefully.com", "mykajabi.com",
    # site builders / no-code platforms
    "notion.site", "notion.so",
    "webflow.io", "webflow.com",
    "framer.website", "framer.app", "framer.media",
    "tilda.ws", "tilda.cc",
    "vercel.app", "netlify.app", "pages.dev", "github.io",
    "wixsite.com", "squarespace.com", "blogspot.com", "wordpress.com",
    "hostingersite.com", "duckdns.org",
    "super.site", "navs.site", "canva.site", "manus.space", "gamma.app", "systeme.io",
    # link-in-bio + URL shorteners
    "bio.site", "linktree.com", "linktr.ee", "lnk.bio", "heylink.me", "beacons.ai",
    "rebrand.ly", "shorturl.at", "goo.su", "short.gy", "clkmg.com", "cutt.ly",
    # aggregators / directories
    "futurepedia.io", "toolify.ai", "topai.tools", "autogpt.net",
    "aitoolzdir.com", "aitoolssme.com", "whichaitool.com", "aitoolboard.com",
    "producthunt.com", "g2.com", "capterra.com", "getapp.com", "trustradius.com",
    "alternativeto.net", "crunchbase.com", "sourceforge.net",
    "theorg.com", "getlatka.com", "craft.co", "builtinsf.com",
    # forums / community
    "whop.com", "meetup.com", "indiehackers.com", "producttalk.org",
    "lobehub.com", "jiscinvolve.org", "codecanyon.net", "imooc.com",
    # news / press wires (often not relevant for outreach pitch)
    "apnews.com", "forbes.com", "bloomberg.com", "techcrunch.com", "wikipedia.org",
    "religionnews.com", "techxplore.com",
}


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _root_domain(host: str) -> str:
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def _domain(url: str) -> str:
    return (urlparse(url).netloc or "").lower()


def _competitor_brand_terms(competitors: list[str]) -> list[str]:
    """Return brand-name terms for each competitor domain (e.g. heygen.com → 'heygen')."""
    out = []
    for d in competitors:
        root = _root_domain(d.lower())
        name = root.split(".")[0]
        out.append(name)
    return out


def firecrawl_search(app: FirecrawlApp, query: str, limit: int = 10) -> list[dict]:
    resp = app.search(query, limit=limit)
    out = []
    for r in getattr(resp, "web", []) or []:
        url = getattr(r, "url", None)
        title = getattr(r, "title", None) or ""
        if url:
            out.append({"url": url, "title": title, "query": query})
    return out


def scrape(app: FirecrawlApp, url: str) -> tuple[str, str, str] | None:
    """Return (title, markdown, html) for a URL or None on failure."""
    try:
        result = app.scrape(url, formats=["markdown", "html"], only_main_content=False)
        md = getattr(result, "markdown", None) or ""
        html = getattr(result, "html", None) or ""
        meta = getattr(result, "metadata", None) or {}
        title = ""
        if meta:
            title = getattr(meta, "title", None) or (meta.get("title") if isinstance(meta, dict) else "") or ""
        return title, md, html
    except Exception:
        return None


def analyze(url: str, markdown: str, html: str, competitor_brands: list[str]) -> dict:
    """Run all detection signals on a scraped page."""
    text = (markdown or "").lower()
    html_text = (html or "")

    # Affiliate URL patterns — search in HTML
    affiliate_urls = bool(AFFILIATE_URL_RE.search(html_text))
    # Disclosure text — search in markdown
    has_disclosure = bool(DISCLOSURE_RE.search(text))
    # Synthesia mention — markdown OR any synthesia.io link
    mentions_synthesia = bool(SYNTHESIA_RE.search(text)) or "synthesia.io" in html_text.lower()

    # Competitor brand mentions — list of competitor brand-names present
    found_competitors = [b for b in competitor_brands if b in text]
    n_competitors = len(found_competitors)

    # STRICT affiliate intent: must have explicit signal (URL pattern or disclosure),
    # not just multi-competitor mentions (which catches competitor-written self-promo)
    has_affiliate_intent = affiliate_urls or has_disclosure

    # Self-promo guard: skip if page's domain is itself a competitor (config) or a known
    # AI tool from KNOWN_AI_TOOL_DOMAINS. These won't join an affiliate program for us.
    page_host = _domain(url)
    page_root = _root_domain(page_host)
    page_brand = page_root.split(".")[0]
    is_self_promo = (
        page_brand in competitor_brands
        or page_root in KNOWN_AI_TOOL_DOMAINS
        or page_host in KNOWN_AI_TOOL_DOMAINS
    )

    if is_self_promo:
        tier = None
    elif not has_affiliate_intent:
        tier = None
    elif mentions_synthesia:
        tier = "A"
    elif n_competitors >= 2:
        tier = "B"
    else:
        tier = None  # has affiliate signals but no Synthesia and not multi-competitor

    return {
        "tier": tier,
        "affiliate_urls": affiliate_urls,
        "has_disclosure": has_disclosure,
        "mentions_synthesia": mentions_synthesia,
        "competitors": found_competitors,
        "n_competitors": n_competitors,
    }


def run(campaign: str, limit_queries: int | None, limit_scrape: int | None, dry_run: bool) -> int:
    cfg = load_config()
    exclude_domains: set[str] = set(cfg.get("exclude_domains", []))
    competitors: list[str] = cfg.get("competitors", [])
    competitor_brands = _competitor_brand_terms(competitors)

    app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

    queries = DEFAULT_QUERIES
    if limit_queries:
        queries = queries[:limit_queries]

    print(f"=== competitor-affiliates discovery ===")
    print(f"campaign:   {campaign}")
    print(f"queries:    {len(queries)}")
    print(f"competitors: {len(competitors)} ({len(competitor_brands)} brand terms)")

    # 1. Search
    print(f"\n[1/4] Firecrawl search ({len(queries)} queries)...")
    all_results: dict[str, dict] = {}  # url → {url, title, queries:[]}
    for i, q in enumerate(queries, 1):
        hits = firecrawl_search(app, q, limit=10)
        for h in hits:
            u = h["url"].split("#", 1)[0]
            if u in all_results:
                all_results[u]["queries"].append(q)
            else:
                all_results[u] = {"url": u, "title": h["title"], "queries": [q]}
        print(f"  [{i:>2}/{len(queries)}] {q!r:50}  → {len(hits)} hits  (total unique: {len(all_results)})")
        time.sleep(0.3)

    # 2. Pre-filter: drop excluded domains + non-article URLs
    print(f"\n[2/4] Pre-filtering URLs...")
    candidates = []
    for u, info in all_results.items():
        host = _domain(u)
        root = _root_domain(host)
        # Synthesia's own pages
        if "synthesia.io" in host or "synthesia.io" in root:
            continue
        if host in exclude_domains or root in exclude_domains:
            continue
        if not is_article_url(u):
            continue
        candidates.append(info)
    print(f"  {len(all_results)} found → {len(candidates)} after pre-filter")

    if limit_scrape:
        candidates = candidates[:limit_scrape]
        print(f"  limited to {len(candidates)} for scraping")

    # 3. Scrape + analyze
    print(f"\n[3/4] Scraping + analyzing {len(candidates)} candidates...")
    today = date.today().isoformat()
    new_rows: list[dict] = []
    stats = {"scrape_fail": 0, "no_intent": 0, "tier_A": 0, "tier_B": 0, "tier_skip": 0}
    for i, info in enumerate(candidates, 1):
        url = info["url"]
        scraped = scrape(app, url)
        if not scraped:
            stats["scrape_fail"] += 1
            print(f"  [{i:>3}/{len(candidates)}] FAIL  {url[:80]}")
            continue
        title, md, html = scraped
        a = analyze(url, md, html, competitor_brands)
        if a["tier"] is None:
            stats["no_intent" if not (a["affiliate_urls"] or a["has_disclosure"] or a["n_competitors"] >= 2) else "tier_skip"] += 1
            print(f"  [{i:>3}/{len(candidates)}] skip  ({a['n_competitors']} compet., synthesia={a['mentions_synthesia']})  {url[:60]}")
            continue
        stats[f"tier_{a['tier']}"] += 1
        new_rows.append({
            "source_technique": f"affiliate:tier-{a['tier'].lower()}",
            "source_page": url,
            "source_page_title": title or info["title"],
            "domain": _domain(url),
            # Use broken_url/anchor_text fields to carry signal metadata:
            "broken_url": ",".join(a["competitors"]),     # competitors mentioned on the page
            "anchor_text": ("disclosure " if a["has_disclosure"] else "") + ("affiliate-urls" if a["affiliate_urls"] else ""),
            "added_to_sequence": False,
            "email_sent": False,
            "enrichment_ran": False,
            "blocked_by_replyio": False,
            "excluded": False,
            "discovered_at": today,
        })
        print(f"  [{i:>3}/{len(candidates)}] TIER {a['tier']}  {len(a['competitors'])} compet.  synthesia={a['mentions_synthesia']}  {url[:50]}")
        time.sleep(0.2)

    print(f"\nstats:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    if dry_run or not new_rows:
        print(f"\n[dry-run / nothing to write] {len(new_rows)} rows would land in '{campaign}'")
        return 0

    # 4. Write
    print(f"\n[4/4] Writing {len(new_rows)} rows to master sheet...")
    sid = ensure_master_sheet()
    n = append_rows(sid, campaign, new_rows)
    update_summary(sid, campaign)
    print(f"  appended {n} (dedup skipped {len(new_rows) - n})")
    print(f"\nsheet: {sheet_url(sid, campaign)}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--campaign", default="competitor-affiliates")
    p.add_argument("--limit-queries", type=int, default=None, help="limit number of search queries (for testing)")
    p.add_argument("--limit-scrape", type=int, default=None, help="limit number of pages to scrape (for testing)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    return run(args.campaign, args.limit_queries, args.limit_scrape, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
