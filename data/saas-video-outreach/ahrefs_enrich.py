#!/usr/bin/env python3
"""
ahrefs_enrich.py — Enrich SaaS companies with Ahrefs SEO metrics.

For every company domain, fetches:
  - Domain Rating (DR)
  - Estimated monthly organic traffic
  - Number of ranking keywords

Primary workflow: MCP-based (Claude calls Ahrefs batch-analysis directly).
  1. `python3 ahrefs_enrich.py --domains` → prints domains needing enrichment
  2. Claude calls `mcp__ahrefs__batch-analysis` in batches of 100
  3. Results saved via `save_ahrefs_results()`

Also supports direct REST API calls as fallback.

Usage:
    python3 ahrefs_enrich.py             # Enrich via REST API
    python3 ahrefs_enrich.py --force     # Re-enrich even if already done
    python3 ahrefs_enrich.py --domains   # List domains needing enrichment (for MCP)
"""

import argparse
import sys
from datetime import datetime

import requests

import db
from utils import load_config, retry, log

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
# Save results (called after MCP enrichment)
# ============================================================

def save_ahrefs_results(results_dict):
    """
    Save Ahrefs results to database.
    results_dict: {domain: {dr, traffic, keywords}}
    """
    updated = 0
    with db.get_conn() as conn:
        for domain, metrics in results_dict.items():
            db.upsert_company(
                domain, conn=conn,
                domain_rating=metrics.get("dr"),
                org_traffic=metrics.get("traffic"),
                org_keywords=metrics.get("keywords"),
                ahrefs_enriched_at=datetime.now().isoformat(),
            )
            updated += 1
    log.info("Saved Ahrefs data for %d domains.", updated)
    return updated


# ============================================================
# Domain listing (for MCP runs)
# ============================================================

def get_domains_needing_enrichment(force=False):
    """Return list of domains that need Ahrefs enrichment."""
    with db.get_conn() as conn:
        if force:
            rows = conn.execute(
                "SELECT domain FROM companies ORDER BY domain"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT domain FROM companies WHERE ahrefs_enriched_at IS NULL ORDER BY domain"
            ).fetchall()
    return [r["domain"] for r in rows]


def list_domains_needing_enrichment(force=False):
    """Print domains that need Ahrefs enrichment — for MCP-based runs."""
    domains = get_domains_needing_enrichment(force)
    if not domains:
        print("All companies already enriched with Ahrefs data.")
        return

    print(f"{len(domains)} domains need Ahrefs enrichment:\n")
    for d in domains:
        print(f"  {d}")


# ============================================================
# REST API enrichment pipeline
# ============================================================

def run_ahrefs_enrichment(force=False):
    """Enrich all companies via Ahrefs REST API."""
    config = load_config()
    api_key = config.get("ahrefs_api_key", "")
    if not api_key:
        log.error("No ahrefs_api_key configured. Set AHREFS_API_KEY in .env")
        sys.exit(1)

    domains = get_domains_needing_enrichment(force)
    if not domains:
        log.info("No domains to enrich. Use --force to re-run all.")
        return

    batch_size = config.get("enrichment", {}).get("ahrefs_batch_size", 100)
    log.info("Querying Ahrefs for %d domains...", len(domains))

    all_results = {}
    for i in range(0, len(domains), batch_size):
        batch = domains[i:i + batch_size]
        log.info("  Batch %d: %d domains", i // batch_size + 1, len(batch))
        try:
            results = batch_ahrefs_lookup(api_key, batch)
            all_results.update(results)
        except Exception as e:
            log.error("  Batch failed: %s", e)

    print(f"\n{'Domain':<40} {'DR':>5} {'Traffic':>10} {'Keywords':>10}")
    print("-" * 70)

    for domain, metrics in sorted(all_results.items()):
        dr = metrics.get("dr")
        traffic = metrics.get("traffic")
        keywords = metrics.get("keywords")
        print(f"{domain:<40} {dr or 0:>5.1f} {traffic or 0:>10,} {keywords or 0:>10,}")

    save_ahrefs_results(all_results)


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Ahrefs SEO Enrichment")
    parser.add_argument("--force", action="store_true", help="Re-enrich all, even if already done")
    parser.add_argument("--domains", action="store_true", help="List domains needing enrichment (for MCP)")
    args = parser.parse_args()

    if args.domains:
        list_domains_needing_enrichment(force=args.force)
        return

    run_ahrefs_enrichment(force=args.force)


if __name__ == "__main__":
    main()
