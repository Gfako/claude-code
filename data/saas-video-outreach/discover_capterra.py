#!/usr/bin/env python3
"""
discover_capterra.py — Discover SaaS companies from Capterra via Firecrawl.

Two-phase scraping:
  1. Scrape category listing pages (paginated) to get product names + Capterra URLs
  2. Scrape each product's Capterra page to get the real website URL + details

Usage:
    python3 discover_capterra.py                         # All categories
    python3 discover_capterra.py --category crm-software # Single category
    python3 discover_capterra.py --limit 50              # Limit per category
"""

import argparse
import json
import sys
import time

import requests

import db
from discover_base import DiscoverySource
from utils import load_config, clean_domain, log, retry

# Firecrawl API
FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"

# Schema for extracting products from a category listing page
LISTING_SCHEMA = {
    "type": "object",
    "properties": {
        "products": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "capterra_url": {"type": "string"},
                    "description": {"type": "string"},
                    "rating": {"type": "number"},
                    "review_count": {"type": "integer"},
                },
            },
        },
    },
}

# Schema for extracting details from a product page
PRODUCT_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "website_url": {"type": "string"},
        "description": {"type": "string"},
        "rating": {"type": "number"},
        "review_count": {"type": "integer"},
        "pricing": {"type": "string"},
        "company_size": {"type": "string"},
    },
}


class CapterraSource(DiscoverySource):
    """Discover SaaS companies from Capterra via Firecrawl scraping."""

    def __init__(self, firecrawl_api_key):
        self.api_key = firecrawl_api_key
        self.headers = {
            "Authorization": f"Bearer {firecrawl_api_key}",
            "Content-Type": "application/json",
        }

    @property
    def source_name(self):
        return "capterra"

    def discover_category(self, category_slug, category_url, limit=200):
        """
        Scrape a Capterra category: listing pages + individual product pages.
        Returns list of company dicts with real website URLs.
        """
        log.info("Scraping Capterra category: %s (limit=%d)", category_slug, limit)

        # Phase 1: Get product names + Capterra URLs from listing pages
        listings = self._scrape_listing_pages(category_url, limit)
        log.info("  Found %d product listings", len(listings))

        if not listings:
            return []

        # Phase 2: Scrape each product page for real website URL
        companies = []
        for i, listing in enumerate(listings, 1):
            capterra_url = listing.get("capterra_url", "")
            if not capterra_url or not capterra_url.startswith("http"):
                # Try to construct URL from name
                if capterra_url and capterra_url.startswith("/"):
                    capterra_url = f"https://www.capterra.com{capterra_url}"
                else:
                    log.debug("  Skipping %s — no valid Capterra URL", listing.get("name"))
                    continue

            log.info("  [%d/%d] Fetching details: %s", i, len(listings), listing["name"])

            details = self._scrape_product_page(capterra_url)
            if details and details.get("website_url"):
                domain = clean_domain(details["website_url"])
                if domain:
                    companies.append({
                        "name": details.get("name") or listing.get("name", ""),
                        "website_url": details["website_url"],
                        "domain": domain,
                        "description": (details.get("description") or listing.get("description", ""))[:500],
                        "rating": _safe_float(details.get("rating") or listing.get("rating")),
                        "review_count": _safe_int(details.get("review_count") or listing.get("review_count")),
                        "employee_count": _parse_employee_count(details.get("company_size", "")),
                        "capterra_url": capterra_url,
                    })
                else:
                    log.debug("  Skipped %s — website URL filtered out", listing["name"])
            else:
                log.debug("  No website URL for %s", listing.get("name"))

            # Rate limit: be respectful
            time.sleep(0.5)

        log.info("  Got %d companies with valid website URLs", len(companies))
        return companies

    @retry(max_attempts=2, delay=3, exceptions=(requests.RequestException,))
    def _scrape_listing_pages(self, category_url, limit):
        """Scrape paginated listing pages to get product names + Capterra URLs."""
        all_products = []
        page = 1
        max_pages = (limit // 25) + 1  # ~25 products per page

        while len(all_products) < limit and page <= max_pages:
            url = category_url if page == 1 else f"{category_url}?page={page}"
            log.info("  Scraping listing page %d: %s", page, url)

            resp = requests.post(
                f"{FIRECRAWL_BASE}/scrape",
                headers=self.headers,
                json={
                    "url": url,
                    "formats": ["json"],
                    "jsonOptions": {
                        "prompt": "Extract all software products listed on this page. For each get: name, Capterra profile URL (full URL starting with https://www.capterra.com/p/), description, rating, review count.",
                        "schema": LISTING_SCHEMA,
                    },
                    "waitFor": 5000,
                },
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()

            products = (data.get("data", {}).get("json", {}) or {}).get("products", [])
            if not products:
                log.info("  No more products on page %d, stopping", page)
                break

            all_products.extend(products)
            log.info("  Page %d: got %d products (total: %d)", page, len(products), len(all_products))
            page += 1
            time.sleep(1)  # Rate limit between pages

        return all_products[:limit]

    @retry(max_attempts=2, delay=3, exceptions=(requests.RequestException,))
    def _scrape_product_page(self, capterra_url):
        """Scrape a single product page to get real website URL + details."""
        resp = requests.post(
            f"{FIRECRAWL_BASE}/scrape",
            headers=self.headers,
            json={
                "url": capterra_url,
                "formats": ["json"],
                "jsonOptions": {
                    "prompt": "Extract the product's actual website URL (not capterra.com), company name, description, rating, review count, pricing, and company size if shown.",
                    "schema": PRODUCT_SCHEMA,
                },
                "waitFor": 3000,
            },
            timeout=45,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("json", {})


def _safe_float(val):
    try:
        return float(val) if val else None
    except (ValueError, TypeError):
        return None


def _safe_int(val):
    try:
        return int(val) if val else None
    except (ValueError, TypeError):
        return None


def _parse_employee_count(size_str):
    """Parse employee count from strings like '51-200' or '1,001 - 5,000'."""
    if not size_str:
        return None
    parts = str(size_str).replace(",", "").replace(" ", "").split("-")
    try:
        return int(parts[-1].strip())
    except (ValueError, IndexError):
        return None


def run_capterra_discovery(config, category_filter=None, limit=None):
    """
    Run Capterra discovery for configured categories.
    Saves results to DB.
    """
    firecrawl_key = config.get("firecrawl_api_key", "")
    if not firecrawl_key:
        log.error("No firecrawl_api_key configured. Set FIRECRAWL_API_KEY in .env")
        sys.exit(1)

    categories = config.get("discovery", {}).get("categories", [])
    default_limit = limit or config.get("discovery", {}).get("max_per_category", 200)

    if category_filter:
        categories = [c for c in categories if c["slug"] == category_filter]
        if not categories:
            log.error("Category '%s' not found in config.", category_filter)
            sys.exit(1)

    source = CapterraSource(firecrawl_key)
    total_new = 0
    total_skipped = 0

    for cat in categories:
        slug = cat["slug"]
        url = cat["url"]
        label = cat.get("label", slug)

        log.info("=" * 60)
        log.info("  Category: %s (%s)", label, slug)
        log.info("=" * 60)

        companies = source.discover_category(slug, url, limit=default_limit)

        new_in_cat = 0
        with db.get_conn() as conn:
            for comp in companies:
                domain = comp["domain"]

                if db.company_exists(domain):
                    db.add_discovery_source(
                        domain, "capterra", source_url=comp.get("capterra_url", url),
                        category_slug=slug, name_on_source=comp["name"],
                        conn=conn,
                    )
                    total_skipped += 1
                    continue

                db.upsert_company(
                    domain, conn=conn,
                    name=comp["name"],
                    website_url=comp["website_url"],
                    description=comp.get("description"),
                    category=label,
                    category_source="capterra",
                    employee_count=comp.get("employee_count"),
                    review_count=comp.get("review_count"),
                    rating=comp.get("rating"),
                )
                db.add_discovery_source(
                    domain, "capterra", source_url=comp.get("capterra_url", url),
                    category_slug=slug, name_on_source=comp["name"],
                    conn=conn,
                )
                new_in_cat += 1

        total_new += new_in_cat
        log.info("  New companies added: %d (skipped existing: %d)",
                 new_in_cat, len(companies) - new_in_cat)

    log.info("=" * 60)
    log.info("  Capterra discovery complete!")
    log.info("  New companies: %d", total_new)
    log.info("  Already existed: %d", total_skipped)
    return total_new


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Capterra Discovery via Firecrawl")
    parser.add_argument("--category", type=str, help="Single category slug to scrape")
    parser.add_argument("--limit", type=int, help="Max listings per category")
    args = parser.parse_args()

    config = load_config()
    run_capterra_discovery(config, category_filter=args.category, limit=args.limit)


if __name__ == "__main__":
    main()
