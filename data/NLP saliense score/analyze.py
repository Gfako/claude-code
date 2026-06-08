"""Google Cloud Natural Language API entity extraction with salience scoring."""

import logging
import os

from google.cloud import language_v2

from db import get_db, upsert_entity, mark_analyzed, get_pages, get_entities_for_domain
from utils import clean_domain, retry

log = logging.getLogger("salience.analyze")

# ---------------------------------------------------------------------------
# Google NLP client
# ---------------------------------------------------------------------------

def get_nlp_client():
    """Create a Google Cloud NLP client.

    Uses GOOGLE_APPLICATION_CREDENTIALS env var for authentication.
    """
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and not os.path.isabs(creds_path):
        # Resolve relative to project root
        from pathlib import Path
        creds_path = str(Path(__file__).parent / creds_path)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

    return language_v2.LanguageServiceClient()


# ---------------------------------------------------------------------------
# Entity extraction
# ---------------------------------------------------------------------------

@retry(max_attempts=3, delay=2)
def analyze_entities(client, text, max_bytes=500000):
    """Call Google NLP analyzeEntities on text content.

    Returns list of entity dicts with name, type, salience, mention_count.
    """
    # Truncate if too long (API limit is 1MB, we use 500KB for safety)
    encoded = text.encode("utf-8")
    if len(encoded) > max_bytes:
        text = encoded[:max_bytes].decode("utf-8", errors="ignore")
        log.debug(f"Truncated text to {max_bytes} bytes")

    document = language_v2.Document(
        content=text,
        type_=language_v2.Document.Type.PLAIN_TEXT,
        language_code="en",
    )

    response = client.analyze_entities(
        request={"document": document, "encoding_type": language_v2.EncodingType.UTF8}
    )

    entities = []
    for entity in response.entities:
        entities.append({
            "name": entity.name,
            "type": language_v2.Entity.Type(entity.type_).name,
            "salience": round(entity.salience, 6),
            "mention_count": len(entity.mentions),
        })

    return entities


# ---------------------------------------------------------------------------
# Batch analysis
# ---------------------------------------------------------------------------

def analyze_page(client, url, text, domain, config, db_path=None):
    """Analyze a single page and store results."""
    min_salience = config.get("nlp", {}).get("min_salience", 0.01)
    max_bytes = config.get("nlp", {}).get("max_text_bytes", 500000)

    entities = analyze_entities(client, text, max_bytes)

    with get_db(db_path) as conn:
        for ent in entities:
            if ent["salience"] < min_salience:
                continue
            upsert_entity(
                conn,
                url=url,
                entity_name=ent["name"],
                entity_type=ent["type"],
                salience=ent["salience"],
                mention_count=ent["mention_count"],
                domain=domain,
            )
        mark_analyzed(conn, url)

    return len(entities)


def analyze_domain(domain, page_texts, config, db_path=None):
    """Analyze all pages for a domain.

    page_texts: list of (url, text) tuples from crawl step.
    """
    domain = clean_domain(domain)
    batch_size = config.get("nlp", {}).get("batch_size", 50)

    if not page_texts:
        log.warning(f"No pages to analyze for {domain}")
        return 0

    # Estimate cost
    estimated_cost = len(page_texts) / 1000  # $1 per 1000 records
    log.info(
        f"Analyzing {len(page_texts)} pages for {domain}. "
        f"Estimated NLP API cost: ${estimated_cost:.2f}"
    )

    client = get_nlp_client()
    total_entities = 0

    for i, (url, text) in enumerate(page_texts, 1):
        try:
            count = analyze_page(client, url, text, domain, config, db_path)
            total_entities += count

            if i % batch_size == 0:
                log.info(f"  Analyzed {i}/{len(page_texts)} pages ({total_entities} entities so far)")

        except Exception as e:
            log.error(f"Failed to analyze {url}: {e}")
            continue

    log.info(f"Analysis complete for {domain}: {total_entities} entities from {len(page_texts)} pages")
    return total_entities


def analyze_from_db(domain, config, db_path=None):
    """Analyze pages that are crawled but not yet analyzed (for re-runs)."""
    domain = clean_domain(domain)

    with get_db(db_path) as conn:
        pages = get_pages(conn, domain, status="crawled")

    if not pages:
        log.info(f"No unanalyzed pages for {domain}")
        return 0

    log.info(f"Found {len(pages)} crawled but unanalyzed pages for {domain}")

    # We need text for these pages — re-fetch
    from crawl import fetch_page_text
    page_texts = []
    for p in pages:
        try:
            text = fetch_page_text(p["url"], config)
            if len(text) >= 50:
                page_texts.append((p["url"], text))
        except Exception as e:
            log.warning(f"Could not re-fetch {p['url']}: {e}")

    return analyze_domain(domain, page_texts, config, db_path)


# ---------------------------------------------------------------------------
# Domain-level aggregation queries
# ---------------------------------------------------------------------------

def get_domain_entity_summary(domain, config, db_path=None, top_n=100):
    """Get aggregated entity summary for a domain."""
    from db import get_top_entities
    with get_db(db_path) as conn:
        min_sal = config.get("nlp", {}).get("min_salience", 0.01)
        return get_top_entities(conn, domain, top_n, min_sal)
