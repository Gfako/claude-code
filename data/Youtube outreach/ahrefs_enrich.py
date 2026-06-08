#!/usr/bin/env python3
"""
ahrefs_enrich.py — Enrich channel websites with Ahrefs SEO metrics

For every channel that has a website, fetches:
  - Domain Rating (DR)
  - Estimated monthly organic traffic
  - Number of ranking keywords

The Ahrefs REST API may return "Insufficient plan" for some accounts.
In that case, ask Claude to run the enrichment using the Ahrefs MCP tools:
  "Run Ahrefs enrichment on the channels with websites"

Usage:
    python3 ahrefs_enrich.py             # Enrich via REST API
    python3 ahrefs_enrich.py --force     # Re-enrich even if already done
    python3 ahrefs_enrich.py --domains   # List domains needing enrichment (for MCP runs)
"""

import argparse
import sys
from datetime import datetime

import requests

import db
from utils import load_config, clean_domain, retry, log

AHREFS_BASE = "https://api.ahrefs.com/v3"


# ============================================================
# Ahrefs REST API
# ============================================================

@retry(max_attempts=3, delay=5, exceptions=(requests.RequestException,))
def batch_ahrefs_lookup(api_key, domains):
    """
    Query Ahrefs batch-analysis for multiple domains.
    Returns dict mapping domain -> {dr, traffic, keywords}.
    Max 100 per request.
    """
    if not domains:
        return {}

    targets = [{"url": d, "mode": "subdomains", "protocol": "both"} for d in domains]

    resp = requests.post(
        f"{AHREFS_BASE}/site-explorer/batch-analysis",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "select": ["domain_rating", "org_traffic", "org_keywords"],
            "targets": targets,
        },
        timeout=30,
    )

    if resp.status_code != 200:
        log.warning("Ahrefs API error (%d): %s", resp.status_code, resp.text[:200])
        return {}

    data = resp.json()
    results = {}
    for i, item in enumerate(data.get("targets", [])):
        if i < len(domains):
            results[domains[i]] = {
                "dr": item.get("domain_rating"),
                "traffic": item.get("org_traffic"),
                "keywords": item.get("org_keywords"),
            }

    return results


# ============================================================
# Enrichment pipeline
# ============================================================

def _get_domains_needing_enrichment(force=False):
    """Return list of (channel_id, name, website_url) rows needing Ahrefs data."""
    with db.get_conn() as conn:
        if force:
            rows = conn.execute("""
                SELECT c.channel_id, c.name, ct.website_url
                FROM channels c
                JOIN contacts ct ON c.channel_id = ct.channel_id
                WHERE ct.website_url IS NOT NULL AND ct.website_url != ''
            """).fetchall()
        else:
            rows = conn.execute("""
                SELECT c.channel_id, c.name, ct.website_url
                FROM channels c
                JOIN contacts ct ON c.channel_id = ct.channel_id
                WHERE ct.website_url IS NOT NULL AND ct.website_url != ''
                  AND ct.ahrefs_enriched_at IS NULL
            """).fetchall()
    return [dict(r) for r in rows]


def run_ahrefs_enrichment(force=False):
    """Enrich all channels that have websites with Ahrefs data."""
    config = load_config()
    api_key = config.get("ahrefs_api_key", "")
    if not api_key:
        log.error("No ahrefs_api_key configured. Set AHREFS_API_KEY in .env")
        sys.exit(1)

    rows = _get_domains_needing_enrichment(force)
    if not rows:
        log.info("No channels with websites to enrich (or all already done). Use --force to re-run.")
        return

    # Build domain -> channel mapping
    domain_to_channels = {}
    for r in rows:
        domain = clean_domain(r["website_url"])
        if domain:
            domain_to_channels.setdefault(domain, []).append(r)

    unique_domains = list(domain_to_channels.keys())
    log.info("Querying Ahrefs for %d domains...", len(unique_domains))

    all_results = {}
    for i in range(0, len(unique_domains), 100):
        batch = unique_domains[i:i + 100]
        log.info("  Batch %d: %d domains", i // 100 + 1, len(batch))
        try:
            results = batch_ahrefs_lookup(api_key, batch)
            all_results.update(results)
        except Exception as e:
            log.error("  Batch failed: %s", e)

    print(f"\n{'Domain':<40} {'DR':>5} {'Traffic':>10} {'Keywords':>10}")
    print("-" * 70)

    updated = 0
    for domain, metrics in all_results.items():
        dr = metrics.get("dr")
        traffic = metrics.get("traffic")
        keywords = metrics.get("keywords")

        print(f"{domain:<40} {dr or 0:>5.1f} {traffic or 0:>10,} {keywords or 0:>10,}")

        for ch_data in domain_to_channels.get(domain, []):
            db.upsert_contact(
                ch_data["channel_id"],
                website_dr=dr,
                website_traffic=traffic,
                website_keywords=keywords,
                ahrefs_enriched_at=datetime.now().isoformat(),
            )
            updated += 1

    log.info("Updated %d channels with Ahrefs data.", updated)


def list_domains_needing_enrichment():
    """Print domains that need Ahrefs enrichment — for MCP-based runs."""
    rows = _get_domains_needing_enrichment(force=False)
    if not rows:
        print("All websites already enriched.")
        return

    domains = set()
    for r in rows:
        d = clean_domain(r["website_url"])
        if d:
            domains.add(d)

    print(f"{len(domains)} domains need Ahrefs enrichment:\n")
    for d in sorted(domains):
        print(f"  {d}")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Ahrefs SEO Enrichment")
    parser.add_argument("--force", action="store_true", help="Re-enrich all, even if already done")
    parser.add_argument("--domains", action="store_true", help="List domains needing enrichment (for MCP runs)")
    args = parser.parse_args()

    if args.domains:
        list_domains_needing_enrichment()
        return

    run_ahrefs_enrichment(force=args.force)


if __name__ == "__main__":
    main()
