"""Crawl a domain using Screaming Frog CLI + extract text with requests/BS4."""

import csv
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from db import get_db, upsert_page, page_count
from utils import (
    clean_domain,
    domain_to_url,
    load_config,
    normalize_url,
    retry,
    url_matches_subfolder,
)

log = logging.getLogger("salience.crawl")

# ---------------------------------------------------------------------------
# Screaming Frog CLI
# ---------------------------------------------------------------------------

def run_screaming_frog(domain, config, subfolder=None):
    """Run Screaming Frog headless crawl and return the output directory."""
    sf_path = config["screaming_frog"]["cli_path"]
    output_base = config["screaming_frog"]["output_dir"]
    timeout = config["screaming_frog"].get("timeout_seconds", 600)

    crawl_url = domain_to_url(domain, subfolder)
    slug = clean_domain(domain).replace(".", "-")
    if subfolder:
        slug += subfolder.strip("/").replace("/", "-")
    output_dir = os.path.join(output_base, slug)
    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        sf_path,
        "--crawl", crawl_url,
        "--headless",
        "--output-folder", output_dir,
        "--export-tabs", "Internal:All",
    ]

    log.info(f"Starting Screaming Frog crawl: {crawl_url}")
    log.info(f"Output: {output_dir}")
    log.info(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            log.error(f"Screaming Frog exited with code {result.returncode}")
            if result.stderr:
                log.error(f"stderr: {result.stderr[:500]}")
        else:
            log.info("Screaming Frog crawl completed successfully")
    except subprocess.TimeoutExpired:
        log.error(f"Screaming Frog timed out after {timeout}s")
        raise
    except FileNotFoundError:
        log.error(f"Screaming Frog not found at: {sf_path}")
        raise

    return output_dir


def parse_sf_output(output_dir, domain, subfolder=None, config=None):
    """Parse Screaming Frog CSV output to extract indexable HTML URLs."""
    urls = []
    csv_path = None

    # SF exports as "internal_all.csv" or similar
    for name in ["internal_all.csv", "internal_html.csv"]:
        candidate = os.path.join(output_dir, name)
        if os.path.exists(candidate):
            csv_path = candidate
            break

    if not csv_path:
        # Try to find any CSV in the output dir
        csvs = list(Path(output_dir).glob("*.csv"))
        if csvs:
            csv_path = str(csvs[0])
            log.info(f"Using CSV: {csv_path}")
        else:
            log.error(f"No CSV files found in {output_dir}")
            return urls

    exclude_patterns = config.get("crawl", {}).get("exclude_patterns", []) if config else []
    max_pages = config.get("crawl", {}).get("max_pages", 500) if config else 500

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("Address", row.get("URL", "")).strip()
            if not url:
                continue

            # Only HTML pages
            content_type = row.get("Content Type", "")
            status_code = row.get("Status Code", "")
            if content_type and "text/html" not in content_type:
                continue
            if status_code and status_code != "200":
                continue

            # Subfolder filter
            if subfolder and not url_matches_subfolder(url, domain, subfolder):
                continue

            # Exclude patterns
            skip = False
            for pattern in exclude_patterns:
                if pattern in url:
                    skip = True
                    break
            if skip:
                continue

            urls.append(normalize_url(url))

            if len(urls) >= max_pages:
                log.info(f"Reached max pages limit ({max_pages})")
                break

    log.info(f"Parsed {len(urls)} URLs from Screaming Frog output")
    return urls


# ---------------------------------------------------------------------------
# Fallback: Sitemap-based URL discovery
# ---------------------------------------------------------------------------

def discover_urls_sitemap(domain, subfolder=None, config=None):
    """Fallback URL discovery via sitemap.xml when SF is unavailable."""
    max_pages = config.get("crawl", {}).get("max_pages", 500) if config else 500
    exclude_patterns = config.get("crawl", {}).get("exclude_patterns", []) if config else []
    base_url = f"https://www.{clean_domain(domain)}"

    urls = []
    sitemap_urls_to_check = [
        f"{base_url}/sitemap.xml",
        f"{base_url}/sitemap_index.xml",
        f"{base_url}/sitemap-index.xml",
    ]

    session = requests.Session()
    session.headers.update({"User-Agent": config.get("crawl", {}).get("user_agent", "EntitySalienceBot/1.0")})

    def parse_sitemap(sitemap_url, depth=0):
        if depth > 3 or len(urls) >= max_pages:
            return
        try:
            resp = session.get(sitemap_url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            log.warning(f"Failed to fetch sitemap {sitemap_url}: {e}")
            return

        soup = BeautifulSoup(resp.content, "lxml-xml")

        # Check for sitemap index (nested sitemaps)
        for sitemap in soup.find_all("sitemap"):
            loc = sitemap.find("loc")
            if loc:
                parse_sitemap(loc.text.strip(), depth + 1)

        # Extract URLs
        for url_tag in soup.find_all("url"):
            if len(urls) >= max_pages:
                break
            loc = url_tag.find("loc")
            if not loc:
                continue
            url = loc.text.strip()

            if subfolder and not url_matches_subfolder(url, domain, subfolder):
                continue

            skip = False
            for pattern in exclude_patterns:
                if pattern in url:
                    skip = True
                    break
            if skip:
                continue

            urls.append(normalize_url(url))

    for sitemap_url in sitemap_urls_to_check:
        parse_sitemap(sitemap_url)
        if urls:
            break

    log.info(f"Discovered {len(urls)} URLs from sitemap")
    return list(dict.fromkeys(urls))  # dedupe preserving order


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

@retry(max_attempts=2, delay=1)
def fetch_page_text(url, config=None):
    """Fetch a page and extract body text using BeautifulSoup."""
    timeout = config.get("crawl", {}).get("timeout", 30) if config else 30
    user_agent = config.get("crawl", {}).get("user_agent", "EntitySalienceBot/1.0") if config else "EntitySalienceBot/1.0"

    resp = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": user_agent},
        allow_redirects=True,
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    # Remove non-content elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                      "noscript", "iframe", "svg", "form"]):
        tag.decompose()

    # Try to find main content area
    main = soup.find("main") or soup.find("article") or soup.find(attrs={"role": "main"})
    if main:
        text = main.get_text(separator=" ", strip=True)
    else:
        body = soup.find("body")
        text = body.get_text(separator=" ", strip=True) if body else ""

    # Clean up whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------------------------------------------------
# Main crawl function
# ---------------------------------------------------------------------------

def crawl_domain(domain, config, subfolder=None, limit=None, use_sitemap=False, db_path=None):
    """Crawl a domain: discover URLs then extract text.

    Returns list of (url, text) tuples for pages that need analysis.
    """
    domain = clean_domain(domain)
    max_pages = limit or config.get("crawl", {}).get("max_pages", 500)
    delay = config.get("crawl", {}).get("request_delay", 0.5)

    # Step 1: Discover URLs
    if use_sitemap:
        urls = discover_urls_sitemap(domain, subfolder, config)
    else:
        try:
            output_dir = run_screaming_frog(domain, config, subfolder)
            urls = parse_sf_output(output_dir, domain, subfolder, config)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            log.warning("Screaming Frog failed, falling back to sitemap discovery")
            urls = discover_urls_sitemap(domain, subfolder, config)

    if not urls:
        log.error(f"No URLs found for {domain}")
        return []

    urls = urls[:max_pages]

    # Step 2: Register URLs in database
    with get_db(db_path) as conn:
        existing = {p["url"] for p in get_pages_with_status(conn, domain, "analyzed")}
        for url in urls:
            if url not in existing:
                upsert_page(conn, url, domain, "pending")

    # Step 3: Extract text for pending pages
    results = []
    with get_db(db_path) as conn:
        pending = [u for u in urls if u not in existing]

    log.info(f"Extracting text from {len(pending)} pages ({len(existing)} already analyzed, skipping)")

    for i, url in enumerate(pending, 1):
        try:
            text = fetch_page_text(url, config)
            if len(text) < 50:
                log.warning(f"Skipping {url} — too little text ({len(text)} chars)")
                continue

            results.append((url, text))

            with get_db(db_path) as conn:
                upsert_page(conn, url, domain, "crawled")

            if i % 10 == 0:
                log.info(f"  Extracted {i}/{len(pending)} pages")

            time.sleep(delay)

        except Exception as e:
            log.warning(f"Failed to extract text from {url}: {e}")
            continue

    log.info(f"Crawl complete: {len(results)} pages with text ready for analysis")
    return results


def get_pages_with_status(conn, domain, status):
    """Helper to get pages with a specific status."""
    rows = conn.execute(
        "SELECT url FROM pages WHERE domain=? AND status=?", (domain, status)
    ).fetchall()
    return [dict(r) for r in rows]
