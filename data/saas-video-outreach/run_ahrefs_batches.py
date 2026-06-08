#!/usr/bin/env python3
"""
Run Ahrefs batch analysis via REST API in batches of 25.
Saves results to DB as it goes.
"""

import json
import sys
import time
from datetime import datetime

import requests

import db
from utils import load_config, log

AHREFS_BASE = "https://api.ahrefs.com/v3"


def batch_lookup(api_key, domains):
    """Query Ahrefs for up to 25 domains."""
    targets = [{"url": d, "mode": "subdomains", "protocol": "both"} for d in domains]
    resp = requests.post(
        f"{AHREFS_BASE}/site-explorer/batch-analysis",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"select": ["domain_rating", "org_traffic", "org_keywords"], "targets": targets},
        timeout=30,
    )
    if resp.status_code != 200:
        log.warning("Ahrefs error %d: %s", resp.status_code, resp.text[:200])
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


def main():
    config = load_config()
    api_key = config.get("ahrefs_api_key", "")
    if not api_key:
        log.error("No AHREFS_API_KEY configured")
        sys.exit(1)

    with db.get_conn() as conn:
        rows = conn.execute("""
            SELECT domain FROM companies
            WHERE (has_youtube_channel = 1 OR has_website_videos = 1)
              AND ahrefs_enriched_at IS NULL
            ORDER BY domain
        """).fetchall()

    domains = [r["domain"] for r in rows]
    log.info("Enriching %d domains with Ahrefs (batches of 25)...", len(domains))

    total_enriched = 0
    batch_size = 25

    for i in range(0, len(domains), batch_size):
        batch = domains[i:i + batch_size]
        batch_num = i // batch_size + 1
        log.info("  Batch %d: %d domains (total so far: %d)", batch_num, len(batch), total_enriched)

        try:
            results = batch_lookup(api_key, batch)
        except Exception as e:
            log.error("  Batch %d failed: %s", batch_num, e)
            time.sleep(5)
            continue

        if results:
            now = datetime.now().isoformat()
            with db.get_conn() as conn:
                for domain, metrics in results.items():
                    db.upsert_company(domain, conn=conn,
                                      domain_rating=metrics.get("dr"),
                                      org_traffic=metrics.get("traffic"),
                                      org_keywords=metrics.get("keywords"),
                                      ahrefs_enriched_at=now)
            total_enriched += len(results)

        time.sleep(2)  # Rate limit

    log.info("=" * 60)
    log.info("  Ahrefs enrichment complete!")
    log.info("  Total enriched: %d / %d", total_enriched, len(domains))


if __name__ == "__main__":
    main()
