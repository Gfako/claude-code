"""
db.py — SQLite database layer for the SaaS Video Outreach pipeline.

Tracks companies, discovery sources, videos, and contacts.
Uses context managers to prevent resource leaks, and column whitelist
validation to prevent SQL injection in dynamic upserts.
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from utils import (
    DB_PATH, DATA_DIR, log,
    validate_columns,
    COMPANIES_COLUMNS, DISCOVERY_SOURCES_COLUMNS,
    COMPANY_VIDEOS_COLUMNS, CONTACTS_COLUMNS,
)


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

@contextmanager
def get_conn():
    """
    Context manager that yields a SQLite connection.
    Commits on success, rolls back on exception, always closes.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema — initial table creation
# ---------------------------------------------------------------------------

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS companies (
    domain           TEXT PRIMARY KEY,
    name             TEXT,
    website_url      TEXT,
    description      TEXT,
    category         TEXT,
    category_source  TEXT,
    employee_count   INTEGER,
    review_count     INTEGER,
    rating           REAL,
    has_youtube_channel   INTEGER DEFAULT 0,
    youtube_channel_id    TEXT,
    youtube_channel_url   TEXT,
    youtube_subscriber_count INTEGER,
    youtube_video_count   INTEGER,
    has_website_videos    INTEGER DEFAULT 0,
    website_video_platforms TEXT,
    website_video_count   INTEGER,
    domain_rating    REAL,
    org_traffic      INTEGER,
    org_keywords     INTEGER,
    ahrefs_enriched_at TEXT,
    status           TEXT DEFAULT 'discovered'
        CHECK (status IN (
            'discovered','video_checked','enriched','exported'
        )),
    discovered_at    TEXT DEFAULT (datetime('now')),
    updated_at       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS discovery_sources (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    domain           TEXT REFERENCES companies(domain),
    source           TEXT CHECK (source IN ('capterra','g2','crunchbase')),
    source_url       TEXT,
    category_slug    TEXT,
    name_on_source   TEXT,
    scraped_at       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS company_videos (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    domain           TEXT REFERENCES companies(domain),
    video_type       TEXT CHECK (video_type IN (
        'youtube_channel','youtube_embed','vimeo','wistia','vidyard','loom','unknown'
    )),
    video_url        TEXT,
    video_id         TEXT,
    page_found_on    TEXT,
    title            TEXT,
    detection_method TEXT CHECK (detection_method IN ('youtube_api','google_video_search')),
    review_status    TEXT DEFAULT 'pending'
        CHECK (review_status IN ('pending','approved','rejected')),
    review_note      TEXT,
    reviewed_at      TEXT,
    detected_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS contacts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    domain           TEXT REFERENCES companies(domain),
    first_name       TEXT,
    last_name        TEXT,
    job_title        TEXT,
    email            TEXT,
    email_type       TEXT,
    email_confidence TEXT,
    phone            TEXT,
    linkedin_url     TEXT,
    source           TEXT DEFAULT 'lusha',
    enriched_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_companies_status ON companies(status);
CREATE INDEX IF NOT EXISTS idx_companies_category ON companies(category);
CREATE INDEX IF NOT EXISTS idx_companies_has_youtube ON companies(has_youtube_channel);
CREATE INDEX IF NOT EXISTS idx_companies_dr ON companies(domain_rating);
CREATE INDEX IF NOT EXISTS idx_sources_domain ON discovery_sources(domain);
CREATE INDEX IF NOT EXISTS idx_sources_source ON discovery_sources(source);
CREATE INDEX IF NOT EXISTS idx_videos_domain ON company_videos(domain);
CREATE INDEX IF NOT EXISTS idx_videos_review ON company_videos(review_status);
CREATE INDEX IF NOT EXISTS idx_contacts_domain ON contacts(domain);
"""


# ---------------------------------------------------------------------------
# Migration — add columns that might be missing from an older schema
# ---------------------------------------------------------------------------

_MIGRATIONS = [
    # (table, column, type + default)
]


def _get_table_columns(conn, table):
    """Return set of column names for a table."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _run_migrations(conn):
    """Add missing columns via ALTER TABLE (idempotent)."""
    for table, column, col_def in _MIGRATIONS:
        existing = _get_table_columns(conn, table)
        if column not in existing:
            sql = f"ALTER TABLE {table} ADD COLUMN {column} {col_def}"
            try:
                conn.execute(sql)
                log.info("Migration: added %s.%s", table, column)
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    raise


def init_db():
    """Create tables and run migrations. Called once on startup."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_CREATE_TABLES)
    _run_migrations(conn)
    conn.commit()
    conn.close()
    log.debug("Database initialized at %s", DB_PATH)


# ---------------------------------------------------------------------------
# Safe upsert helper (column-whitelist validated)
# ---------------------------------------------------------------------------

def _safe_upsert(conn, table, pk_col, pk_val, kwargs, whitelist):
    """
    Insert-or-update a row, validating all column names against a whitelist.
    """
    validate_columns(kwargs, whitelist, table)

    existing = conn.execute(
        f"SELECT 1 FROM {table} WHERE {pk_col} = ?", (pk_val,)
    ).fetchone()

    if existing:
        if "updated_at" in whitelist and "updated_at" not in kwargs:
            kwargs["updated_at"] = datetime.now().isoformat()
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [pk_val]
        conn.execute(f"UPDATE {table} SET {sets} WHERE {pk_col} = ?", vals)
    else:
        kwargs[pk_col] = pk_val
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join("?" for _ in kwargs)
        conn.execute(
            f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
            list(kwargs.values()),
        )


# ---------------------------------------------------------------------------
# Company operations
# ---------------------------------------------------------------------------

def upsert_company(domain, conn=None, **kwargs):
    """Insert or update a company. Accepts an optional open connection."""
    if conn is not None:
        _safe_upsert(conn, "companies", "domain", domain, kwargs, COMPANIES_COLUMNS)
    else:
        with get_conn() as c:
            _safe_upsert(c, "companies", "domain", domain, kwargs, COMPANIES_COLUMNS)


def get_company(domain):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM companies WHERE domain = ?", (domain,)).fetchone()
    return dict(row) if row else None


def get_companies_by_status(status):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM companies WHERE status = ? ORDER BY domain_rating DESC NULLS LAST",
            (status,),
        ).fetchall()
    return [dict(r) for r in rows]


def company_exists(domain):
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM companies WHERE domain = ?", (domain,)).fetchone()
    return row is not None


# ---------------------------------------------------------------------------
# Discovery source operations
# ---------------------------------------------------------------------------

def add_discovery_source(domain, source, source_url=None, category_slug=None, name_on_source=None, conn=None):
    """Record which directory found this company."""
    def _insert(c):
        # Check for duplicate
        existing = c.execute(
            "SELECT 1 FROM discovery_sources WHERE domain = ? AND source = ? AND category_slug = ?",
            (domain, source, category_slug),
        ).fetchone()
        if existing:
            return
        c.execute(
            "INSERT INTO discovery_sources (domain, source, source_url, category_slug, name_on_source) "
            "VALUES (?, ?, ?, ?, ?)",
            (domain, source, source_url, category_slug, name_on_source),
        )

    if conn is not None:
        _insert(conn)
    else:
        with get_conn() as c:
            _insert(c)


# ---------------------------------------------------------------------------
# Video operations
# ---------------------------------------------------------------------------

def add_video(domain, video_type, video_url, detection_method, conn=None,
              video_id=None, page_found_on=None, title=None):
    """Add a discovered video for a company."""
    def _insert(c):
        # Check for duplicate by video_url
        existing = c.execute(
            "SELECT 1 FROM company_videos WHERE domain = ? AND video_url = ?",
            (domain, video_url),
        ).fetchone()
        if existing:
            return
        c.execute(
            "INSERT INTO company_videos (domain, video_type, video_url, video_id, "
            "page_found_on, title, detection_method) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (domain, video_type, video_url, video_id, page_found_on, title, detection_method),
        )

    if conn is not None:
        _insert(conn)
    else:
        with get_conn() as c:
            _insert(c)


def get_videos_for_company(domain):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM company_videos WHERE domain = ? ORDER BY detected_at DESC",
            (domain,),
        ).fetchall()
    return [dict(r) for r in rows]


def update_video_review(video_id, review_status, review_note=None):
    """Update a video's review status."""
    with get_conn() as conn:
        updates = {"review_status": review_status, "reviewed_at": datetime.now().isoformat()}
        if review_note is not None:
            updates["review_note"] = review_note
        _safe_upsert(conn, "company_videos", "id", video_id, updates, COMPANY_VIDEOS_COLUMNS)


# ---------------------------------------------------------------------------
# Contact operations
# ---------------------------------------------------------------------------

def add_contact(domain, first_name, last_name, job_title, email=None,
                email_type=None, email_confidence=None, phone=None,
                linkedin_url=None, source="lusha", conn=None):
    """Add a contact for a company."""
    def _insert(c):
        c.execute(
            "INSERT INTO contacts (domain, first_name, last_name, job_title, "
            "email, email_type, email_confidence, phone, linkedin_url, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (domain, first_name, last_name, job_title,
             email, email_type, email_confidence, phone, linkedin_url, source),
        )

    if conn is not None:
        _insert(conn)
    else:
        with get_conn() as c:
            _insert(c)


def get_contacts_for_company(domain):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM contacts WHERE domain = ? ORDER BY enriched_at DESC",
            (domain,),
        ).fetchall()
    return [dict(r) for r in rows]


def count_contacts_for_company(domain, conn=None):
    """Return number of contacts for a company."""
    def _count(c):
        return c.execute("SELECT COUNT(*) FROM contacts WHERE domain = ?", (domain,)).fetchone()[0]

    if conn is not None:
        return _count(conn)
    with get_conn() as c:
        return _count(c)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def get_stats():
    with get_conn() as conn:
        stats = {}
        stats["total_companies"] = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
        stats["discovered"] = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE status = 'discovered'"
        ).fetchone()[0]
        stats["video_checked"] = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE status = 'video_checked'"
        ).fetchone()[0]
        stats["enriched"] = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE status = 'enriched'"
        ).fetchone()[0]
        stats["with_youtube"] = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE has_youtube_channel = 1"
        ).fetchone()[0]
        stats["with_website_videos"] = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE has_website_videos = 1"
        ).fetchone()[0]
        stats["with_any_video"] = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE has_youtube_channel = 1 OR has_website_videos = 1"
        ).fetchone()[0]
        stats["total_videos"] = conn.execute("SELECT COUNT(*) FROM company_videos").fetchone()[0]
        stats["videos_pending"] = conn.execute(
            "SELECT COUNT(*) FROM company_videos WHERE review_status = 'pending'"
        ).fetchone()[0]
        stats["videos_approved"] = conn.execute(
            "SELECT COUNT(*) FROM company_videos WHERE review_status = 'approved'"
        ).fetchone()[0]
        stats["total_contacts"] = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
        stats["companies_with_contacts"] = conn.execute(
            "SELECT COUNT(DISTINCT domain) FROM contacts"
        ).fetchone()[0]
        stats["ahrefs_enriched"] = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE ahrefs_enriched_at IS NOT NULL"
        ).fetchone()[0]

        # Category breakdown
        cats = conn.execute(
            "SELECT category, COUNT(*) as cnt FROM companies GROUP BY category ORDER BY cnt DESC"
        ).fetchall()
        stats["categories"] = {r["category"]: r["cnt"] for r in cats}

        # Source breakdown
        sources = conn.execute(
            "SELECT source, COUNT(DISTINCT domain) as cnt FROM discovery_sources GROUP BY source"
        ).fetchall()
        stats["sources"] = {r["source"]: r["cnt"] for r in sources}

    return stats


# ---------------------------------------------------------------------------
# Auto-init on import
# ---------------------------------------------------------------------------
init_db()
