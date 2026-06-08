#!/usr/bin/env python3
"""
dedup.py — Cross-source deduplication by domain.

When companies are discovered from multiple sources (Capterra, G2, etc.),
this module merges them by domain and updates category_source.

Usage:
    python3 dedup.py
"""

import db
from utils import log


def run_dedup():
    """
    Deduplicate companies that exist from multiple discovery sources.
    Updates category_source to reflect all sources.
    """
    with db.get_conn() as conn:
        # Find domains with multiple source entries
        rows = conn.execute("""
            SELECT domain, GROUP_CONCAT(DISTINCT source) as sources,
                   COUNT(DISTINCT source) as source_count
            FROM discovery_sources
            GROUP BY domain
            HAVING source_count > 1
        """).fetchall()

        updated = 0
        for row in rows:
            domain = row["domain"]
            sources = row["sources"]  # e.g. "capterra,g2"
            conn.execute(
                "UPDATE companies SET category_source = ? WHERE domain = ?",
                (sources, domain),
            )
            updated += 1

        # Also merge categories for companies found in multiple categories
        cat_rows = conn.execute("""
            SELECT domain, GROUP_CONCAT(DISTINCT category_slug) as categories
            FROM discovery_sources
            GROUP BY domain
            HAVING COUNT(DISTINCT category_slug) > 1
        """).fetchall()

    log.info("Dedup complete: %d companies found in multiple sources", updated)
    log.info("  %d companies found in multiple categories", len(cat_rows))


if __name__ == "__main__":
    run_dedup()
