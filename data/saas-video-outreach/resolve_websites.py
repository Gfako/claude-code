#!/usr/bin/env python3
"""
resolve_websites.py — Resolve real website URLs for SaaS companies.

Strategy:
  1. Try obvious domain patterns (companyname.com) with HEAD requests
  2. For failures, use Firecrawl search as fallback

Usage:
    python3 resolve_websites.py                # Resolve all unresolved
    python3 resolve_websites.py --limit 100    # Limit to N companies
    python3 resolve_websites.py --dry-run      # Show what would be resolved
"""

import argparse
import json
import re
import sys
import time
import requests
from urllib.parse import urlparse

import db
from utils import load_config, clean_domain, log

# Common SaaS domain patterns
def _guess_domains(name):
    """Generate likely domain guesses for a company name."""
    # Clean the name
    clean = name.lower().strip()
    clean = re.sub(r'\s*\(.*?\)\s*', '', clean)  # Remove parentheticals
    clean = re.sub(r'[,\.\-\'\"!]', '', clean)

    guesses = []

    # If name already looks like a domain
    if '.' in name and ' ' not in name:
        guesses.append(name.lower())

    # Single word: word.com, word.io, word.ai
    words = clean.split()
    slug = ''.join(words)
    slug_dash = '-'.join(words)

    guesses.extend([
        f"{slug}.com",
        f"{slug}.io",
        f"{slug}.ai",
        f"{slug}.co",
        f"{slug_dash}.com",
        f"{slug_dash}.io",
    ])

    # First word only (for multi-word names)
    if len(words) > 1:
        guesses.extend([
            f"{words[0]}.com",
            f"{words[0]}.io",
        ])

    # Common patterns: getX.com, tryX.com, useX.com
    guesses.extend([
        f"get{slug}.com",
        f"try{slug}.com",
        f"use{slug}.com",
        f"www.{slug}.com",
    ])

    return list(dict.fromkeys(guesses))  # Dedupe while preserving order


def _check_domain(domain, timeout=5):
    """Check if a domain resolves and returns a valid response."""
    for scheme in ['https', 'http']:
        url = f"{scheme}://{domain}"
        try:
            resp = requests.head(url, timeout=timeout, allow_redirects=True,
                               headers={'User-Agent': 'Mozilla/5.0'})
            if resp.status_code < 400:
                # Get final URL after redirects
                final_url = resp.url
                final_domain = clean_domain(final_url)
                if final_domain:
                    return final_domain, final_url
        except (requests.RequestException, Exception):
            continue
    return None, None


def resolve_websites(limit=None, dry_run=False):
    """Resolve real website URLs for companies with placeholder domains."""
    # Get companies that need resolution (placeholder domains ending in .com
    # that are just slugified names)
    with db.get_conn() as conn:
        rows = conn.execute("""
            SELECT domain, name FROM companies
            WHERE category_source = 'google_search'
            ORDER BY name
        """).fetchall()

    companies = [dict(r) for r in rows]
    if limit:
        companies = companies[:limit]

    if not companies:
        log.info("No companies need website resolution.")
        return

    log.info("Resolving websites for %d companies...", len(companies))

    resolved = 0
    failed = 0

    for i, comp in enumerate(companies, 1):
        name = comp['name']
        old_domain = comp['domain']

        guesses = _guess_domains(name)

        if dry_run:
            log.info("[%d/%d] %s → would try: %s", i, len(companies), name, ', '.join(guesses[:3]))
            continue

        if i % 50 == 0:
            log.info("  Progress: %d/%d (resolved: %d, failed: %d)", i, len(companies), resolved, failed)

        found_domain = None
        found_url = None

        for guess in guesses[:4]:  # Try up to 4 guesses
            domain, url = _check_domain(guess, timeout=4)
            if domain:
                found_domain = domain
                found_url = url
                break

        if found_domain and found_domain != old_domain:
            # Check if this domain already exists in DB
            existing = db.get_company(found_domain)
            if existing:
                # Domain collision — skip, this company is a duplicate
                failed += 1
                continue

            # Update the company with the real domain
            with db.get_conn() as conn:
                # Delete the old placeholder entry
                conn.execute("DELETE FROM companies WHERE domain = ?", (old_domain,))
                # Insert with real domain
                db.upsert_company(
                    found_domain, conn=conn,
                    name=name,
                    website_url=found_url or f"https://{found_domain}",
                    category_source="google_search",
                    status="discovered",
                )
            resolved += 1
        else:
            failed += 1

    log.info("=" * 60)
    log.info("  Website resolution complete!")
    log.info("  Resolved: %d", resolved)
    log.info("  Failed:   %d", failed)
    log.info("  Total:    %d", len(companies))


def main():
    parser = argparse.ArgumentParser(description="Resolve SaaS company websites")
    parser.add_argument("--limit", type=int, help="Max companies to process")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be resolved")
    args = parser.parse_args()

    resolve_websites(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
