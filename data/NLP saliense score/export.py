"""CSV export for entity salience analysis results."""

import csv
import json
import logging
import os
from pathlib import Path

from db import get_db, get_top_entities, get_clusters, get_cluster_pages
from utils import clean_domain

log = logging.getLogger("salience.export")

# ---------------------------------------------------------------------------
# CSV writers
# ---------------------------------------------------------------------------

def export_entities(domain, config, db_path=None, output_dir=None):
    """Export top entities with aggregated salience scores."""
    domain = clean_domain(domain)
    out_dir = _get_output_dir(config, output_dir)
    filepath = os.path.join(out_dir, f"{domain.replace('.', '-')}_entities.csv")

    with get_db(db_path) as conn:
        entities = get_top_entities(conn, domain, top_n=500, min_salience=0.01)

    headers = ["entity_name", "entity_type", "avg_salience", "total_mentions", "page_count"]

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for e in entities:
            writer.writerow({
                "entity_name": e["entity_name"],
                "entity_type": e.get("entity_type", ""),
                "avg_salience": round(e["avg_salience"], 4),
                "total_mentions": e["total_mentions"],
                "page_count": e["page_count"],
            })

    log.info(f"Exported {len(entities)} entities to {filepath}")
    return filepath


def export_clusters(domain, config, db_path=None, output_dir=None):
    """Export cluster assignments for all 3 methods."""
    domain = clean_domain(domain)
    out_dir = _get_output_dir(config, output_dir)
    filepath = os.path.join(out_dir, f"{domain.replace('.', '-')}_clusters.csv")

    with get_db(db_path) as conn:
        all_clusters = get_clusters(conn, domain)

        rows = []
        for c in all_clusters:
            cluster_urls = get_cluster_pages(conn, c["method"], c["cluster_id"])
            top_ents = json.loads(c["top_entities"]) if c["top_entities"] else []
            for url in cluster_urls:
                rows.append({
                    "method": c["method"],
                    "cluster_id": c["cluster_id"],
                    "cluster_label": c["label"],
                    "top_entities": " | ".join(top_ents),
                    "page_count": c["page_count"],
                    "url": url,
                })

    headers = ["method", "cluster_id", "cluster_label", "top_entities", "page_count", "url"]

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    log.info(f"Exported {len(rows)} cluster assignments to {filepath}")
    return filepath


def export_comparison(comparison, config, output_dir=None):
    """Export competitor comparison data."""
    out_dir = _get_output_dir(config, output_dir)
    primary = comparison["primary"]
    filepath = os.path.join(out_dir, f"{primary.replace('.', '-')}_comparison.csv")

    all_domains = [primary] + comparison["competitors"]

    # Build rows from entity matrix
    rows = []
    for entity_name, domain_data in comparison["entity_matrix"].items():
        row = {"entity_name": entity_name}
        for d in all_domains:
            data = domain_data.get(d, {})
            row[f"{d}_salience"] = round(data.get("avg_salience", 0), 4)
            row[f"{d}_mentions"] = data.get("total_mentions", 0)
            row[f"{d}_pages"] = data.get("page_count", 0)
        rows.append(row)

    # Sort by primary salience descending
    rows.sort(key=lambda x: -x.get(f"{primary}_salience", 0))

    headers = ["entity_name"]
    for d in all_domains:
        headers.extend([f"{d}_salience", f"{d}_mentions", f"{d}_pages"])

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    log.info(f"Exported {len(rows)} entity comparisons to {filepath}")
    return filepath


def export_gaps(comparison, config, output_dir=None):
    """Export gap analysis — entities competitors have that primary lacks."""
    out_dir = _get_output_dir(config, output_dir)
    primary = comparison["primary"]
    filepath = os.path.join(out_dir, f"{primary.replace('.', '-')}_gaps.csv")

    headers = [
        "entity_name", "entity_type", "competitor",
        "competitor_salience", "competitor_mentions", "competitor_pages",
    ]

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for gap in comparison["gaps"]:
            writer.writerow({
                "entity_name": gap["entity_name"],
                "entity_type": gap.get("entity_type", ""),
                "competitor": gap["competitor"],
                "competitor_salience": round(gap["competitor_salience"], 4),
                "competitor_mentions": gap["competitor_mentions"],
                "competitor_pages": gap["competitor_pages"],
            })

    log.info(f"Exported {len(comparison['gaps'])} entity gaps to {filepath}")
    return filepath


def export_all(domain, config, comparison=None, db_path=None, output_dir=None):
    """Run all exports."""
    files = []
    files.append(export_entities(domain, config, db_path, output_dir))
    files.append(export_clusters(domain, config, db_path, output_dir))
    if comparison:
        files.append(export_comparison(comparison, config, output_dir))
        files.append(export_gaps(comparison, config, output_dir))
    log.info(f"All exports complete: {len(files)} files")
    return files


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_output_dir(config, output_dir=None):
    """Get or create output directory."""
    if output_dir:
        d = output_dir
    else:
        d = config.get("export", {}).get("output_dir", "./output")
        if not os.path.isabs(d):
            d = os.path.join(os.path.dirname(__file__), d)
    os.makedirs(d, exist_ok=True)
    return d
