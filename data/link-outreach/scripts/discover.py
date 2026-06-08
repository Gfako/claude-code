#!/usr/bin/env python3
"""Page discovery for /link-discover.

Plugin sources (only --source scrape:broken-outbounds in Phase 1):
- scrape:broken-outbounds <topic>
    Firecrawl search for topic → scrape each result → extract outbound links →
    concurrent HEAD/GET check → write a row per broken link to the campaign tab.

Usage:
  python3 discover.py --source scrape:broken-outbounds \
                      --campaign <slug> --topic "<query>" [--limit 20]
"""
from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from firecrawl import FirecrawlApp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sheets_helper import append_rows, ensure_master_sheet, sheet_url, update_summary  # noqa: E402
from filter_articles import is_article_url  # noqa: E402

ssl._create_default_https_context = ssl._create_unverified_context

PROJECT_ROOT = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects")
CONFIG_PATH = PROJECT_ROOT / "link-outreach" / "config.json"
FIRECRAWL_API_KEY = (PROJECT_ROOT / ".credentials" / "firecrawl-api-key.txt").read_text().strip()

# URL prefixes / schemes that aren't real outbound targets
SKIP_SCHEMES = ("mailto:", "tel:", "javascript:", "#")
# Domains that are never worth flagging as a "broken link to replace"
DEFAULT_NEVER_FLAG = {
    "youtube.com", "www.youtube.com", "youtu.be",
    "twitter.com", "x.com", "facebook.com", "www.facebook.com",
    "linkedin.com", "www.linkedin.com", "instagram.com", "www.instagram.com",
    "t.me", "wa.me", "pinterest.com",
}
USER_AGENT = "Mozilla/5.0 (compatible; LinkDiscoverBot/1.0; +https://www.synthesia.io)"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def _root_domain(netloc: str) -> str:
    parts = netloc.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else netloc


def _normalize_url(url: str) -> str:
    if not url:
        return ""
    return url.strip().split("#", 1)[0]


def _is_skippable_link(url: str) -> bool:
    if not url:
        return True
    lower = url.lower()
    return any(lower.startswith(s) for s in SKIP_SCHEMES)


def extract_outbound_links(html: str, source_url: str, exclude_domains: set[str]) -> list[tuple[str, str]]:
    """Return (anchor_text, absolute_url) pairs for outbound links worth checking."""
    soup = BeautifulSoup(html or "", "html.parser")
    source_root = _root_domain(_domain(source_url))
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = _normalize_url(a["href"])
        if _is_skippable_link(href):
            continue
        if not href.startswith("http"):
            # skip relative or protocol-relative — assume same site
            continue
        netloc = _domain(href)
        if not netloc:
            continue
        root = _root_domain(netloc)
        if netloc in DEFAULT_NEVER_FLAG or root in DEFAULT_NEVER_FLAG:
            continue
        if root == source_root:
            continue
        if root in exclude_domains or netloc in exclude_domains:
            continue
        if href in seen:
            continue
        seen.add(href)
        anchor = (a.get_text() or "").strip()
        out.append((anchor[:200], href))
    return out


def _request(url: str, method: str, timeout: int) -> int:
    req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status


def check_link(url: str, timeout: int = 8) -> tuple[str, int | str]:
    """Return (url, status_code_or_error_string).

    Marks 404/410/5xx as broken. 401/403 are NOT broken — page exists, restricted.
    """
    for method in ("HEAD", "GET"):
        try:
            code = _request(url, method, timeout)
            return url, code
        except urllib.error.HTTPError as e:
            # 405 from HEAD → fall through to GET
            if method == "HEAD" and e.code in (405, 501):
                continue
            return url, e.code
        except (urllib.error.URLError, TimeoutError) as e:
            return url, f"err:{type(e).__name__}"
        except Exception as e:
            return url, f"err:{type(e).__name__}"
    return url, "err:unreachable"


def is_broken(status: int | str) -> bool:
    """Only HTTP 404/410/5xx count as broken. Connection errors are too noisy
    (anti-bot, timeouts, transient DNS) — flag as 'suspect' instead."""
    if isinstance(status, int):
        return status in (404, 410) or status >= 500
    return False


def firecrawl_search(app: FirecrawlApp, query: str, limit: int) -> list[dict]:
    """Return [{'url','title'}, ...] for the top `limit` results."""
    resp = app.search(query, limit=limit)
    results = getattr(resp, "web", None) or []
    out = []
    for r in results:
        url = getattr(r, "url", None)
        title = getattr(r, "title", None) or ""
        if url:
            out.append({"url": url, "title": title})
    return out


def scrape_with_html(app: FirecrawlApp, url: str) -> tuple[str, str] | None:
    """Return (title, html) for a URL, or None on failure."""
    try:
        result = app.scrape(url, formats=["html"], only_main_content=False)
        html = getattr(result, "html", None) or ""
        meta = getattr(result, "metadata", None) or {}
        title = ""
        if meta:
            title = getattr(meta, "title", None) or (meta.get("title") if isinstance(meta, dict) else "") or ""
        if not html:
            return None
        return title, html
    except Exception as e:
        print(f"  scrape failed: {url[:80]} — {e}")
        return None


def run_broken_outbounds(campaign: str, topic: str, limit: int) -> None:
    cfg = load_config()
    exclude_domains: set[str] = set(cfg.get("exclude_domains", []))
    timeout = int(cfg.get("link_discover", {}).get("outbound_check_timeout_sec", 8))
    concurrency = int(cfg.get("link_discover", {}).get("outbound_check_concurrency", 10))

    print(f"=== broken-outbounds | campaign={campaign} | topic={topic!r} | limit={limit} ===")
    app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

    print(f"[1/3] Firecrawl search...")
    search_results = firecrawl_search(app, topic, limit)
    print(f"  found {len(search_results)} candidate pages")

    new_rows: list[dict] = []
    today = date.today().isoformat()

    for i, hit in enumerate(search_results, 1):
        page_url = hit["url"]
        page_root = _root_domain(_domain(page_url))
        if page_root in exclude_domains or _domain(page_url) in exclude_domains:
            print(f"  [{i}/{len(search_results)}] skip (excluded domain): {page_url[:80]}")
            continue
        if not is_article_url(page_url):
            print(f"  [{i}/{len(search_results)}] skip (not article-like): {page_url[:80]}")
            continue
        print(f"  [{i}/{len(search_results)}] scrape: {page_url[:80]}")
        scraped = scrape_with_html(app, page_url)
        if not scraped:
            continue
        page_title, html = scraped
        title = page_title or hit.get("title", "")
        outbound = extract_outbound_links(html, page_url, exclude_domains)
        if not outbound:
            print(f"    no outbound links")
            continue
        print(f"    {len(outbound)} outbound links → checking…")

        broken_for_page: list[tuple[str, str, int | str]] = []
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            futs = {ex.submit(check_link, url, timeout): (anchor, url) for anchor, url in outbound}
            for fut in as_completed(futs):
                anchor, url = futs[fut]
                _, status = fut.result()
                if is_broken(status):
                    broken_for_page.append((anchor, url, status))

        if not broken_for_page:
            print(f"    no broken links")
            continue
        print(f"    BROKEN: {len(broken_for_page)}")

        for anchor, broken_url, status in broken_for_page:
            new_rows.append({
                "source_technique": "broken-outbounds",
                "source_page": page_url,
                "source_page_title": title,
                "domain": _domain(page_url),
                "broken_url": broken_url,
                "anchor_text": anchor,
                "added_to_sequence": False,
                "email_sent": False,
                "reply_status": f"http_{status}",
                "discovered_at": today,
            })

    if not new_rows:
        print("\nNo broken links discovered.")
        return

    print(f"\n[2/3] Writing {len(new_rows)} rows to master sheet…")
    sid = ensure_master_sheet()
    n_appended = append_rows(sid, campaign, new_rows)
    update_summary(sid, campaign)
    print(f"  appended {n_appended} new rows (dedup skipped {len(new_rows) - n_appended})")

    print(f"\n[3/3] Done.")
    print(f"  sheet: {sheet_url(sid, campaign)}")


def main() -> int:
    p = argparse.ArgumentParser(description="link-discover discovery stage")
    p.add_argument("--source", required=True, choices=["scrape:broken-outbounds"])
    p.add_argument("--campaign", required=True, help="campaign slug used as tab name")
    p.add_argument("--topic", required=True, help="query/topic to discover pages for")
    p.add_argument("--limit", type=int, default=20, help="max pages to scrape (default 20)")
    args = p.parse_args()

    if args.source == "scrape:broken-outbounds":
        run_broken_outbounds(args.campaign, args.topic, args.limit)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
