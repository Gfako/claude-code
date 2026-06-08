"""SQLite database layer for entity salience analysis."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "analysis.db"

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS pages (
    url         TEXT PRIMARY KEY,
    domain      TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending → crawled → analyzed
    crawled_at  TIMESTAMP,
    analyzed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS entities (
    url           TEXT NOT NULL,
    entity_name   TEXT NOT NULL,
    entity_type   TEXT,
    salience      REAL NOT NULL,
    mention_count INTEGER DEFAULT 1,
    domain        TEXT NOT NULL,
    PRIMARY KEY (url, entity_name),
    FOREIGN KEY (url) REFERENCES pages(url)
);

CREATE TABLE IF NOT EXISTS clusters (
    method       TEXT NOT NULL,      -- cooccurrence / kmeans / hierarchical
    cluster_id   INTEGER NOT NULL,
    label        TEXT,
    top_entities TEXT,               -- JSON array
    domain       TEXT NOT NULL,
    page_count   INTEGER DEFAULT 0,
    PRIMARY KEY (method, cluster_id, domain)
);

CREATE TABLE IF NOT EXISTS cluster_pages (
    method      TEXT NOT NULL,
    cluster_id  INTEGER NOT NULL,
    url         TEXT NOT NULL,
    PRIMARY KEY (method, cluster_id, url),
    FOREIGN KEY (url) REFERENCES pages(url)
);

CREATE TABLE IF NOT EXISTS runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    domain          TEXT NOT NULL,
    competitors     TEXT,            -- JSON array of competitor domains
    subfolder       TEXT,
    started_at      TIMESTAMP NOT NULL,
    completed_at    TIMESTAMP,
    page_count      INTEGER DEFAULT 0,
    config_snapshot TEXT             -- JSON of config used
);

CREATE INDEX IF NOT EXISTS idx_entities_domain ON entities(domain);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(entity_name);
CREATE INDEX IF NOT EXISTS idx_entities_salience ON entities(domain, salience DESC);
CREATE INDEX IF NOT EXISTS idx_pages_domain ON pages(domain);
CREATE INDEX IF NOT EXISTS idx_pages_status ON pages(domain, status);
CREATE INDEX IF NOT EXISTS idx_clusters_domain ON clusters(domain, method);
"""


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

@contextmanager
def get_db(db_path=None):
    """Context manager for SQLite connection with WAL mode."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path=None):
    """Create all tables and indexes."""
    with get_db(db_path) as conn:
        conn.executescript(SCHEMA)


# ---------------------------------------------------------------------------
# Pages CRUD
# ---------------------------------------------------------------------------

def upsert_page(conn, url, domain, status="pending"):
    """Insert or update a page record."""
    now = datetime.utcnow().isoformat()
    crawled_at = now if status == "crawled" else None
    conn.execute(
        """INSERT INTO pages (url, domain, status, crawled_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(url) DO UPDATE SET
             status = excluded.status,
             crawled_at = COALESCE(excluded.crawled_at, pages.crawled_at)
        """,
        (url, domain, status, crawled_at),
    )


def mark_analyzed(conn, url):
    """Mark a page as analyzed."""
    conn.execute(
        "UPDATE pages SET status='analyzed', analyzed_at=? WHERE url=?",
        (datetime.utcnow().isoformat(), url),
    )


def get_pages(conn, domain, status=None):
    """Get pages for a domain, optionally filtered by status."""
    if status:
        rows = conn.execute(
            "SELECT * FROM pages WHERE domain=? AND status=?", (domain, status)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM pages WHERE domain=?", (domain,)
        ).fetchall()
    return [dict(r) for r in rows]


def page_count(conn, domain, status=None):
    """Count pages for a domain."""
    if status:
        return conn.execute(
            "SELECT COUNT(*) FROM pages WHERE domain=? AND status=?", (domain, status)
        ).fetchone()[0]
    return conn.execute(
        "SELECT COUNT(*) FROM pages WHERE domain=?", (domain,)
    ).fetchone()[0]


# ---------------------------------------------------------------------------
# Entities CRUD
# ---------------------------------------------------------------------------

def upsert_entity(conn, url, entity_name, entity_type, salience, mention_count, domain):
    """Insert or update an entity record."""
    conn.execute(
        """INSERT INTO entities (url, entity_name, entity_type, salience, mention_count, domain)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(url, entity_name) DO UPDATE SET
             entity_type = excluded.entity_type,
             salience = excluded.salience,
             mention_count = excluded.mention_count
        """,
        (url, entity_name, entity_type, salience, mention_count, domain),
    )


def get_entities_for_page(conn, url):
    """Get all entities for a specific page."""
    rows = conn.execute(
        "SELECT * FROM entities WHERE url=? ORDER BY salience DESC", (url,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_entities_for_domain(conn, domain, min_salience=0.0):
    """Get all entities for a domain, optionally above a salience threshold."""
    rows = conn.execute(
        "SELECT * FROM entities WHERE domain=? AND salience>=? ORDER BY salience DESC",
        (domain, min_salience),
    ).fetchall()
    return [dict(r) for r in rows]


def get_top_entities(conn, domain, top_n=50, min_salience=0.0):
    """Get top entities by average salience across all pages of a domain."""
    rows = conn.execute(
        """SELECT entity_name, entity_type,
                  AVG(salience) as avg_salience,
                  SUM(mention_count) as total_mentions,
                  COUNT(DISTINCT url) as page_count
           FROM entities
           WHERE domain=? AND salience>=?
           GROUP BY entity_name
           ORDER BY avg_salience DESC
           LIMIT ?
        """,
        (domain, min_salience, top_n),
    ).fetchall()
    return [dict(r) for r in rows]


def get_unique_entities(conn, domain):
    """Get distinct entity names for a domain."""
    rows = conn.execute(
        "SELECT DISTINCT entity_name FROM entities WHERE domain=?", (domain,)
    ).fetchall()
    return [r["entity_name"] for r in rows]


# ---------------------------------------------------------------------------
# Clusters CRUD
# ---------------------------------------------------------------------------

def save_clusters(conn, method, clusters_data, domain):
    """Save clustering results. clusters_data is a list of dicts:
    [{"cluster_id": 0, "label": "AI Video", "top_entities": [...], "urls": [...]}, ...]
    """
    # Clear old clusters for this method+domain
    conn.execute(
        "DELETE FROM clusters WHERE method=? AND domain=?", (method, domain)
    )
    conn.execute(
        "DELETE FROM cluster_pages WHERE method=? AND cluster_id IN "
        "(SELECT cluster_id FROM clusters WHERE method=? AND domain=?)",
        (method, method, domain),
    )
    # The above delete on cluster_pages won't work after clusters are deleted,
    # so let's clean cluster_pages by method + domain join
    conn.execute(
        """DELETE FROM cluster_pages WHERE method=? AND url IN
           (SELECT url FROM pages WHERE domain=?)""",
        (method, domain),
    )

    for c in clusters_data:
        conn.execute(
            """INSERT INTO clusters (method, cluster_id, label, top_entities, domain, page_count)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                method,
                c["cluster_id"],
                c["label"],
                json.dumps(c["top_entities"]),
                domain,
                len(c["urls"]),
            ),
        )
        for url in c["urls"]:
            conn.execute(
                "INSERT OR IGNORE INTO cluster_pages (method, cluster_id, url) VALUES (?, ?, ?)",
                (method, c["cluster_id"], url),
            )


def get_clusters(conn, domain, method=None):
    """Get clusters for a domain, optionally filtered by method."""
    if method:
        rows = conn.execute(
            "SELECT * FROM clusters WHERE domain=? AND method=? ORDER BY cluster_id",
            (domain, method),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM clusters WHERE domain=? ORDER BY method, cluster_id",
            (domain,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_cluster_pages(conn, method, cluster_id):
    """Get URLs belonging to a specific cluster."""
    rows = conn.execute(
        "SELECT url FROM cluster_pages WHERE method=? AND cluster_id=?",
        (method, cluster_id),
    ).fetchall()
    return [r["url"] for r in rows]


# ---------------------------------------------------------------------------
# Runs CRUD
# ---------------------------------------------------------------------------

def start_run(conn, domain, competitors=None, subfolder=None, config=None):
    """Record the start of an analysis run. Returns run_id."""
    cursor = conn.execute(
        """INSERT INTO runs (domain, competitors, subfolder, started_at, config_snapshot)
           VALUES (?, ?, ?, ?, ?)""",
        (
            domain,
            json.dumps(competitors) if competitors else None,
            subfolder,
            datetime.utcnow().isoformat(),
            json.dumps(config) if config else None,
        ),
    )
    return cursor.lastrowid


def complete_run(conn, run_id, page_count):
    """Mark a run as completed."""
    conn.execute(
        "UPDATE runs SET completed_at=?, page_count=? WHERE id=?",
        (datetime.utcnow().isoformat(), page_count, run_id),
    )


def clear_domain(conn, domain):
    """Remove all data for a domain (for --force re-analysis)."""
    conn.execute("DELETE FROM cluster_pages WHERE url IN (SELECT url FROM pages WHERE domain=?)", (domain,))
    conn.execute("DELETE FROM clusters WHERE domain=?", (domain,))
    conn.execute("DELETE FROM entities WHERE domain=?", (domain,))
    conn.execute("DELETE FROM pages WHERE domain=?", (domain,))
