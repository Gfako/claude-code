"""Cross-domain entity comparison and gap analysis."""

import logging
from collections import defaultdict

from db import get_db, get_top_entities, get_entities_for_domain, get_unique_entities
from utils import clean_domain

log = logging.getLogger("salience.compare")

# ---------------------------------------------------------------------------
# Entity overlap / gap analysis
# ---------------------------------------------------------------------------

def compare_domains(primary_domain, competitor_domains, config, db_path=None, top_n=100):
    """Compare entity salience across domains.

    Returns a comparison dict with:
    - entity_matrix: {entity_name: {domain: avg_salience}}
    - gaps: entities competitors have that primary doesn't
    - unique: entities only primary has
    - overlap: entities shared between primary and competitors
    """
    primary = clean_domain(primary_domain)
    competitors = [clean_domain(d) for d in competitor_domains]
    all_domains = [primary] + competitors
    min_sal = config.get("nlp", {}).get("min_salience", 0.01)

    log.info(f"Comparing {primary} against {len(competitors)} competitors")

    with get_db(db_path) as conn:
        # Get top entities per domain
        domain_entities = {}
        for d in all_domains:
            entities = get_top_entities(conn, d, top_n=top_n, min_salience=min_sal)
            domain_entities[d] = {e["entity_name"]: e for e in entities}

        # Build entity matrix: every entity seen across any domain
        all_entity_names = set()
        for d_ents in domain_entities.values():
            all_entity_names.update(d_ents.keys())

        entity_matrix = {}
        for name in all_entity_names:
            entity_matrix[name] = {}
            for d in all_domains:
                if name in domain_entities[d]:
                    e = domain_entities[d][name]
                    entity_matrix[name][d] = {
                        "avg_salience": e["avg_salience"],
                        "total_mentions": e["total_mentions"],
                        "page_count": e["page_count"],
                    }
                else:
                    entity_matrix[name][d] = {
                        "avg_salience": 0.0,
                        "total_mentions": 0,
                        "page_count": 0,
                    }

        # Gap analysis: high-salience entities competitors have that primary lacks
        primary_entities = set(domain_entities[primary].keys())
        gaps = []
        for comp in competitors:
            comp_entities = set(domain_entities[comp].keys())
            comp_only = comp_entities - primary_entities
            for name in comp_only:
                e = domain_entities[comp][name]
                gaps.append({
                    "entity_name": name,
                    "competitor": comp,
                    "competitor_salience": e["avg_salience"],
                    "competitor_mentions": e["total_mentions"],
                    "competitor_pages": e["page_count"],
                    "entity_type": e.get("entity_type", "UNKNOWN"),
                })

        # Sort gaps by competitor salience (most important first)
        gaps.sort(key=lambda x: -x["competitor_salience"])

        # Entities unique to primary
        all_competitor_entities = set()
        for comp in competitors:
            all_competitor_entities.update(domain_entities[comp].keys())
        unique_to_primary = primary_entities - all_competitor_entities
        unique = []
        for name in unique_to_primary:
            e = domain_entities[primary][name]
            unique.append({
                "entity_name": name,
                "avg_salience": e["avg_salience"],
                "total_mentions": e["total_mentions"],
                "page_count": e["page_count"],
            })
        unique.sort(key=lambda x: -x["avg_salience"])

        # Overlap: entities shared between primary and at least one competitor
        overlap = []
        for name in primary_entities & all_competitor_entities:
            entry = {
                "entity_name": name,
                "primary_salience": domain_entities[primary][name]["avg_salience"],
                "primary_pages": domain_entities[primary][name]["page_count"],
            }
            for comp in competitors:
                if name in domain_entities[comp]:
                    entry[f"{comp}_salience"] = domain_entities[comp][name]["avg_salience"]
                    entry[f"{comp}_pages"] = domain_entities[comp][name]["page_count"]
                else:
                    entry[f"{comp}_salience"] = 0.0
                    entry[f"{comp}_pages"] = 0
            overlap.append(entry)
        overlap.sort(key=lambda x: -x["primary_salience"])

    comparison = {
        "primary": primary,
        "competitors": competitors,
        "entity_matrix": entity_matrix,
        "gaps": gaps,
        "unique_to_primary": unique,
        "overlap": overlap,
        "stats": {
            "primary_entities": len(primary_entities),
            "total_unique_entities": len(all_entity_names),
            "gap_count": len(gaps),
            "unique_count": len(unique),
            "overlap_count": len(overlap),
        },
    }

    log.info(
        f"Comparison complete: {len(all_entity_names)} unique entities, "
        f"{len(gaps)} gaps, {len(unique)} unique to primary, "
        f"{len(overlap)} shared"
    )
    return comparison


def get_entity_type_distribution(domain, config, db_path=None):
    """Get entity type distribution for a domain (for radar chart)."""
    min_sal = config.get("nlp", {}).get("min_salience", 0.01)

    with get_db(db_path) as conn:
        rows = conn.execute(
            """SELECT entity_type, COUNT(*) as count, AVG(salience) as avg_salience
               FROM entities
               WHERE domain=? AND salience>=?
               GROUP BY entity_type
               ORDER BY count DESC""",
            (clean_domain(domain), min_sal),
        ).fetchall()

    return [dict(r) for r in rows]
