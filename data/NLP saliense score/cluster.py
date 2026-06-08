"""Three clustering methods for entity salience data."""

import json
import logging
from collections import defaultdict

import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
from scipy.spatial.distance import pdist
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from db import (
    get_db,
    get_entities_for_domain,
    get_pages,
    save_clusters,
)
from utils import clean_domain

log = logging.getLogger("salience.cluster")

# ---------------------------------------------------------------------------
# Build entity-salience matrix
# ---------------------------------------------------------------------------

def build_salience_matrix(conn, domain, top_n=100, min_salience=0.01):
    """Build a pages × entities salience matrix.

    Returns (matrix, page_urls, entity_names).
    """
    # Get top entities by frequency across domain
    rows = conn.execute(
        """SELECT entity_name, COUNT(DISTINCT url) as freq
           FROM entities
           WHERE domain=? AND salience>=?
           GROUP BY entity_name
           ORDER BY freq DESC
           LIMIT ?""",
        (domain, min_salience, top_n),
    ).fetchall()

    entity_names = [r["entity_name"] for r in rows]
    entity_idx = {name: i for i, name in enumerate(entity_names)}

    # Get analyzed pages
    pages = get_pages(conn, domain, status="analyzed")
    page_urls = [p["url"] for p in pages]

    if not page_urls or not entity_names:
        return np.array([]), page_urls, entity_names

    # Build matrix
    matrix = np.zeros((len(page_urls), len(entity_names)))
    url_idx = {url: i for i, url in enumerate(page_urls)}

    all_entities = get_entities_for_domain(conn, domain, min_salience)
    for ent in all_entities:
        if ent["entity_name"] in entity_idx and ent["url"] in url_idx:
            row = url_idx[ent["url"]]
            col = entity_idx[ent["entity_name"]]
            matrix[row, col] = ent["salience"]

    log.info(f"Built salience matrix: {matrix.shape[0]} pages × {matrix.shape[1]} entities")
    return matrix, page_urls, entity_names


def label_cluster(conn, urls, entity_names_all, top_k=5):
    """Generate a cluster label from its top shared entities."""
    entity_scores = defaultdict(float)
    for url in urls:
        rows = conn.execute(
            "SELECT entity_name, salience FROM entities WHERE url=? ORDER BY salience DESC LIMIT 20",
            (url,),
        ).fetchall()
        for r in rows:
            entity_scores[r["entity_name"]] += r["salience"]

    top = sorted(entity_scores.items(), key=lambda x: -x[1])[:top_k]
    label = " | ".join(name for name, _ in top)
    top_entities = [name for name, _ in top]
    return label, top_entities


# ---------------------------------------------------------------------------
# Method 1: Co-occurrence groups
# ---------------------------------------------------------------------------

def cooccurrence_clusters(domain, config, db_path=None):
    """Cluster pages by shared high-salience entities using co-occurrence.

    Two pages are linked if they share >= min_shared_entities above min_salience.
    Connected components form clusters.
    """
    domain = clean_domain(domain)
    cc_config = config.get("clustering", {}).get("cooccurrence", {})
    min_shared = cc_config.get("min_shared_entities", 3)
    min_sal = cc_config.get("min_salience", 0.1)

    log.info(f"Running co-occurrence clustering (min_shared={min_shared}, min_salience={min_sal})")

    with get_db(db_path) as conn:
        pages = get_pages(conn, domain, status="analyzed")
        if len(pages) < 2:
            log.warning("Not enough pages for clustering")
            return []

        # Build page → entity sets
        page_entities = {}
        for p in pages:
            rows = conn.execute(
                "SELECT entity_name FROM entities WHERE url=? AND salience>=?",
                (p["url"], min_sal),
            ).fetchall()
            page_entities[p["url"]] = {r["entity_name"] for r in rows}

        # Build adjacency via shared entities
        urls = list(page_entities.keys())
        adjacency = defaultdict(set)
        for i in range(len(urls)):
            for j in range(i + 1, len(urls)):
                shared = page_entities[urls[i]] & page_entities[urls[j]]
                if len(shared) >= min_shared:
                    adjacency[urls[i]].add(urls[j])
                    adjacency[urls[j]].add(urls[i])

        # Find connected components (BFS)
        visited = set()
        clusters_data = []
        cluster_id = 0

        for url in urls:
            if url in visited:
                continue
            # BFS
            component = []
            queue = [url]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                component.append(current)
                for neighbor in adjacency.get(current, []):
                    if neighbor not in visited:
                        queue.append(neighbor)

            if len(component) >= 2:
                label, top_ents = label_cluster(conn, component, [])
                clusters_data.append({
                    "cluster_id": cluster_id,
                    "label": label,
                    "top_entities": top_ents,
                    "urls": component,
                })
                cluster_id += 1

        # Add singleton cluster for unclustered pages
        unclustered = [u for u in urls if u not in visited or
                       not any(u in c["urls"] for c in clusters_data)]
        if unclustered:
            clusters_data.append({
                "cluster_id": cluster_id,
                "label": "Unclustered",
                "top_entities": [],
                "urls": unclustered,
            })

        save_clusters(conn, "cooccurrence", clusters_data, domain)

    log.info(f"Co-occurrence clustering: {len(clusters_data)} clusters")
    return clusters_data


# ---------------------------------------------------------------------------
# Method 2: KMeans
# ---------------------------------------------------------------------------

def kmeans_clusters(domain, config, db_path=None):
    """Cluster pages using KMeans on entity-salience vectors.

    Auto-detects optimal K via silhouette score.
    """
    domain = clean_domain(domain)
    km_config = config.get("clustering", {}).get("kmeans", {})
    min_k = km_config.get("min_k", 2)
    max_k = km_config.get("max_k", 20)
    top_entities = km_config.get("top_entities", 100)

    log.info(f"Running KMeans clustering (k range: {min_k}-{max_k})")

    with get_db(db_path) as conn:
        matrix, page_urls, entity_names = build_salience_matrix(
            conn, domain, top_n=top_entities
        )

        if matrix.size == 0 or len(page_urls) < min_k:
            log.warning(f"Not enough data for KMeans ({len(page_urls)} pages)")
            return []

        # Cap max_k to number of pages - 1
        max_k = min(max_k, len(page_urls) - 1)
        if max_k < min_k:
            max_k = min_k

        # Find optimal K via silhouette score
        best_k = min_k
        best_score = -1

        for k in range(min_k, max_k + 1):
            km = KMeans(n_clusters=k, n_init=10, random_state=42)
            labels = km.fit_predict(matrix)

            if len(set(labels)) < 2:
                continue

            score = silhouette_score(matrix, labels)
            if score > best_score:
                best_score = score
                best_k = k

        log.info(f"Optimal K={best_k} (silhouette={best_score:.3f})")

        # Final clustering with optimal K
        km = KMeans(n_clusters=best_k, n_init=10, random_state=42)
        labels = km.fit_predict(matrix)

        # Build cluster data
        clusters_data = []
        for cid in range(best_k):
            cluster_urls = [page_urls[i] for i in range(len(labels)) if labels[i] == cid]
            if not cluster_urls:
                continue

            # Top entities by centroid values
            centroid = km.cluster_centers_[cid]
            top_indices = np.argsort(centroid)[::-1][:5]
            top_ents = [entity_names[idx] for idx in top_indices if centroid[idx] > 0]

            label = " | ".join(top_ents) if top_ents else f"Cluster {cid}"

            clusters_data.append({
                "cluster_id": cid,
                "label": label,
                "top_entities": top_ents,
                "urls": cluster_urls,
            })

        save_clusters(conn, "kmeans", clusters_data, domain)

    log.info(f"KMeans clustering: {len(clusters_data)} clusters")
    return clusters_data


# ---------------------------------------------------------------------------
# Method 3: Hierarchical (Agglomerative)
# ---------------------------------------------------------------------------

def hierarchical_clusters(domain, config, db_path=None):
    """Cluster pages using agglomerative hierarchical clustering.

    Returns flat clusters + linkage data for dendrogram visualization.
    """
    domain = clean_domain(domain)
    h_config = config.get("clustering", {}).get("hierarchical", {})
    top_entities = h_config.get("top_entities", 100)
    distance_threshold = h_config.get("distance_threshold", None)

    log.info("Running hierarchical clustering")

    with get_db(db_path) as conn:
        matrix, page_urls, entity_names = build_salience_matrix(
            conn, domain, top_n=top_entities
        )

        if matrix.size == 0 or len(page_urls) < 2:
            log.warning(f"Not enough data for hierarchical clustering ({len(page_urls)} pages)")
            return [], None

        # Compute linkage
        linkage_matrix = linkage(matrix, method="ward")

        # Determine optimal cut if no threshold given
        if distance_threshold is None:
            # Use silhouette score to find best cut
            best_t = None
            best_score = -1
            # Try different thresholds
            max_dist = linkage_matrix[-1, 2]
            for frac in np.linspace(0.3, 0.8, 20):
                t = max_dist * frac
                labels = fcluster(linkage_matrix, t=t, criterion="distance")
                n_clusters = len(set(labels))
                if n_clusters < 2 or n_clusters >= len(page_urls):
                    continue
                score = silhouette_score(matrix, labels)
                if score > best_score:
                    best_score = score
                    best_t = t

            if best_t is None:
                best_t = max_dist * 0.5
            distance_threshold = best_t

        labels = fcluster(linkage_matrix, t=distance_threshold, criterion="distance")
        n_clusters = len(set(labels))

        log.info(f"Hierarchical clustering: {n_clusters} clusters (threshold={distance_threshold:.2f})")

        # Build cluster data
        clusters_data = []
        for cid in sorted(set(labels)):
            cluster_urls = [page_urls[i] for i in range(len(labels)) if labels[i] == cid]
            if not cluster_urls:
                continue

            label, top_ents = label_cluster(conn, cluster_urls, entity_names)

            clusters_data.append({
                "cluster_id": int(cid),
                "label": label,
                "top_entities": top_ents,
                "urls": cluster_urls,
            })

        save_clusters(conn, "hierarchical", clusters_data, domain)

    log.info(f"Hierarchical clustering: {len(clusters_data)} clusters")

    # Return linkage data for dendrogram visualization
    linkage_info = {
        "linkage_matrix": linkage_matrix.tolist(),
        "page_urls": page_urls,
        "labels": [int(l) for l in labels],
    }
    return clusters_data, linkage_info


# ---------------------------------------------------------------------------
# Run all clustering methods
# ---------------------------------------------------------------------------

def run_all_clustering(domain, config, db_path=None):
    """Run all three clustering methods and return results."""
    results = {}

    log.info(f"Running all clustering methods for {domain}")

    results["cooccurrence"] = cooccurrence_clusters(domain, config, db_path)
    results["kmeans"] = kmeans_clusters(domain, config, db_path)
    hier_clusters, linkage_info = hierarchical_clusters(domain, config, db_path)
    results["hierarchical"] = hier_clusters
    results["linkage_info"] = linkage_info

    total = sum(len(v) for k, v in results.items() if k != "linkage_info")
    log.info(f"All clustering complete: {total} total clusters across 3 methods")
    return results
