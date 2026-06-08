"""
db.py — SQLite database layer for the YouTube Outreach pipeline.

Tracks channels, videos, contacts, dubbing jobs, and outreach logs.
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
    CHANNELS_COLUMNS, VIDEOS_COLUMNS, CONTACTS_COLUMNS,
    DUB_JOBS_COLUMNS, OUTREACH_LOG_COLUMNS,
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
CREATE TABLE IF NOT EXISTS channels (
    channel_id       TEXT PRIMARY KEY,
    name             TEXT,
    custom_url       TEXT,
    description      TEXT,
    country          TEXT,
    default_language TEXT,
    subscriber_count INTEGER,
    view_count       INTEGER,
    video_count      INTEGER,
    topic_categories TEXT,
    creator_score    INTEGER DEFAULT 50,
    has_dubbing      INTEGER DEFAULT 0,
    dubbed_languages TEXT,
    discovered_via   TEXT,
    discovered_at    TEXT DEFAULT (datetime('now')),
    status           TEXT DEFAULT 'discovered'
        CHECK (status IN (
            'discovered','enriched','reviewed','approved',
            'rejected','dubbed','pitched','responded'
        )),
    updated_at       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS videos (
    video_id         TEXT PRIMARY KEY,
    channel_id       TEXT REFERENCES channels(channel_id),
    title            TEXT,
    published_at     TEXT,
    duration_seconds INTEGER,
    default_audio_language TEXT,
    audio_tracks     TEXT,
    has_auto_dub     INTEGER DEFAULT 0,
    has_creator_dub  INTEGER DEFAULT 0,
    checked_at       TEXT DEFAULT (datetime('now')),
    review_status    TEXT DEFAULT 'pending'
        CHECK (review_status IN ('pending','approved','rejected')),
    review_note      TEXT,
    reviewed_at      TEXT,
    selected_for_dubbing INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS contacts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id       TEXT UNIQUE REFERENCES channels(channel_id),
    website_url      TEXT,
    website_domain   TEXT,
    email_from_desc  TEXT,
    email_from_about TEXT,
    email_enriched   TEXT,
    email_source     TEXT,
    twitter_url      TEXT,
    instagram_url    TEXT,
    linkedin_url     TEXT,
    tiktok_url       TEXT,
    other_links      TEXT,
    enriched_at      TEXT,
    website_dr       REAL,
    website_traffic  INTEGER,
    website_keywords INTEGER,
    ahrefs_enriched_at TEXT,
    lusha_first_name TEXT,
    lusha_last_name  TEXT,
    lusha_job_title  TEXT,
    lusha_company    TEXT,
    lusha_enriched_at TEXT
);

CREATE TABLE IF NOT EXISTS dub_jobs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id       TEXT REFERENCES channels(channel_id),
    source_video_id  TEXT REFERENCES videos(video_id),
    source_language  TEXT,
    target_language  TEXT,
    synthesia_asset_id   TEXT,
    synthesia_job_id     TEXT,
    status           TEXT DEFAULT 'pending',
    error_message    TEXT,
    output_url       TEXT,
    output_path      TEXT,
    created_at       TEXT DEFAULT (datetime('now')),
    completed_at     TEXT
);

CREATE TABLE IF NOT EXISTS outreach_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id       TEXT REFERENCES channels(channel_id),
    outreach_type    TEXT,
    email_to         TEXT,
    subject          TEXT,
    gong_call_id     TEXT,
    response_status  TEXT,
    created_at       TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_channels_status ON channels(status);
CREATE INDEX IF NOT EXISTS idx_channels_has_dubbing ON channels(has_dubbing);
CREATE INDEX IF NOT EXISTS idx_channels_subs ON channels(subscriber_count);
CREATE INDEX IF NOT EXISTS idx_videos_channel ON videos(channel_id);
CREATE INDEX IF NOT EXISTS idx_contacts_channel ON contacts(channel_id);
CREATE INDEX IF NOT EXISTS idx_outreach_channel ON outreach_log(channel_id);
"""

# Indexes on columns that may not exist until after migration
_POST_MIGRATION_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_videos_review ON videos(review_status)",
]


# ---------------------------------------------------------------------------
# Migration — add columns that might be missing from an older schema
# ---------------------------------------------------------------------------

_MIGRATIONS = [
    # (table, column, type + default)
    ("channels", "updated_at", "TEXT"),
    ("videos", "review_status", "TEXT DEFAULT 'pending'"),
    ("videos", "review_note", "TEXT"),
    ("videos", "reviewed_at", "TEXT"),
    ("videos", "selected_for_dubbing", "INTEGER DEFAULT 0"),
    ("contacts", "website_domain", "TEXT"),
    ("contacts", "email_source", "TEXT"),
    ("contacts", "lusha_first_name", "TEXT"),
    ("contacts", "lusha_last_name", "TEXT"),
    ("contacts", "lusha_job_title", "TEXT"),
    ("contacts", "lusha_company", "TEXT"),
    ("contacts", "lusha_enriched_at", "TEXT"),
    ("dub_jobs", "error_message", "TEXT"),
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
    # Create indexes that depend on migrated columns
    for idx_sql in _POST_MIGRATION_INDEXES:
        try:
            conn.execute(idx_sql)
        except sqlite3.OperationalError:
            pass  # column may still not exist in edge cases
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
# Channel operations
# ---------------------------------------------------------------------------

def upsert_channel(channel_id, conn=None, **kwargs):
    """Insert or update a channel. Accepts an optional open connection."""
    if conn is not None:
        _safe_upsert(conn, "channels", "channel_id", channel_id, kwargs, CHANNELS_COLUMNS)
    else:
        with get_conn() as c:
            _safe_upsert(c, "channels", "channel_id", channel_id, kwargs, CHANNELS_COLUMNS)


def get_channel(channel_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM channels WHERE channel_id = ?", (channel_id,)).fetchone()
    return dict(row) if row else None


def get_channels_by_status(status):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM channels WHERE status = ? ORDER BY subscriber_count DESC",
            (status,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_dubbed_channels():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM channels WHERE has_dubbing = 1 ORDER BY subscriber_count DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def channel_exists(channel_id):
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM channels WHERE channel_id = ?", (channel_id,)).fetchone()
    return row is not None


# ---------------------------------------------------------------------------
# Video operations
# ---------------------------------------------------------------------------

def upsert_video(video_id, conn=None, **kwargs):
    if conn is not None:
        _safe_upsert(conn, "videos", "video_id", video_id, kwargs, VIDEOS_COLUMNS)
    else:
        with get_conn() as c:
            _safe_upsert(c, "videos", "video_id", video_id, kwargs, VIDEOS_COLUMNS)


def get_videos_for_channel(channel_id):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM videos WHERE channel_id = ?", (channel_id,)).fetchall()
    return [dict(r) for r in rows]


def get_videos_pending_review():
    """Get all videos with review_status='pending' on dubbed channels."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT v.*, c.name as channel_name, c.subscriber_count
            FROM videos v
            JOIN channels c ON v.channel_id = c.channel_id
            WHERE v.has_auto_dub = 1
              AND v.review_status = 'pending'
            ORDER BY c.subscriber_count DESC, v.duration_seconds ASC
        """).fetchall()
    return [dict(r) for r in rows]


def update_video_review(video_id, review_status, review_note=None, selected=None):
    """Update a video's review status."""
    with get_conn() as conn:
        updates = {"review_status": review_status, "reviewed_at": datetime.now().isoformat()}
        if review_note is not None:
            updates["review_note"] = review_note
        if selected is not None:
            updates["selected_for_dubbing"] = 1 if selected else 0
        _safe_upsert(conn, "videos", "video_id", video_id, updates, VIDEOS_COLUMNS)


# ---------------------------------------------------------------------------
# Contact operations
# ---------------------------------------------------------------------------

def upsert_contact(channel_id, conn=None, **kwargs):
    if conn is not None:
        _safe_upsert(conn, "contacts", "channel_id", channel_id, kwargs, CONTACTS_COLUMNS)
    else:
        with get_conn() as c:
            _safe_upsert(c, "contacts", "channel_id", channel_id, kwargs, CONTACTS_COLUMNS)


def get_contact(channel_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM contacts WHERE channel_id = ?", (channel_id,)).fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Dub job operations
# ---------------------------------------------------------------------------

def create_dub_job(channel_id, source_video_id, source_language, target_language):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO dub_jobs (channel_id, source_video_id, source_language, target_language) "
            "VALUES (?, ?, ?, ?)",
            (channel_id, source_video_id, source_language, target_language),
        )
        job_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return job_id


def update_dub_job(job_id, conn=None, **kwargs):
    if conn is not None:
        _safe_upsert(conn, "dub_jobs", "id", job_id, kwargs, DUB_JOBS_COLUMNS)
    else:
        with get_conn() as c:
            _safe_upsert(c, "dub_jobs", "id", job_id, kwargs, DUB_JOBS_COLUMNS)


# ---------------------------------------------------------------------------
# Outreach log operations
# ---------------------------------------------------------------------------

def create_outreach_log(channel_id, outreach_type, email_to=None, subject=None,
                        gong_call_id=None, response_status=None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO outreach_log (channel_id, outreach_type, email_to, subject, "
            "gong_call_id, response_status) VALUES (?, ?, ?, ?, ?, ?)",
            (channel_id, outreach_type, email_to, subject, gong_call_id, response_status),
        )


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def get_stats():
    with get_conn() as conn:
        stats = {}
        stats["total_channels"] = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
        stats["dubbed_channels"] = conn.execute(
            "SELECT COUNT(*) FROM channels WHERE has_dubbing = 1"
        ).fetchone()[0]
        stats["enriched_channels"] = conn.execute(
            "SELECT COUNT(*) FROM channels WHERE status IN ('enriched','reviewed','approved','dubbed','pitched','responded')"
        ).fetchone()[0]
        stats["approved_channels"] = conn.execute(
            "SELECT COUNT(*) FROM channels WHERE status = 'approved'"
        ).fetchone()[0]
        stats["channels_with_email"] = conn.execute(
            "SELECT COUNT(*) FROM contacts WHERE "
            "email_from_desc IS NOT NULL OR email_from_about IS NOT NULL OR email_enriched IS NOT NULL"
        ).fetchone()[0]
        stats["channels_with_website"] = conn.execute(
            "SELECT COUNT(*) FROM contacts WHERE website_url IS NOT NULL"
        ).fetchone()[0]
        stats["total_videos_checked"] = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
        stats["videos_pending_review"] = conn.execute(
            "SELECT COUNT(*) FROM videos WHERE has_auto_dub = 1 AND review_status = 'pending'"
        ).fetchone()[0]
        stats["videos_approved"] = conn.execute(
            "SELECT COUNT(*) FROM videos WHERE review_status = 'approved'"
        ).fetchone()[0]
        stats["dub_jobs_complete"] = conn.execute(
            "SELECT COUNT(*) FROM dub_jobs WHERE status = 'complete'"
        ).fetchone()[0]
    return stats


# ---------------------------------------------------------------------------
# Auto-init on import
# ---------------------------------------------------------------------------
init_db()
