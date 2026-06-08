"""
utils.py — Shared utilities for the YouTube Outreach pipeline.

Provides:
  - Config loading (YAML + .env)
  - HTTP session with YouTube consent cookies
  - @retry decorator for API calls
  - clean_domain() for URL → domain extraction
  - setup_logging()
  - Column whitelists for SQL injection prevention
"""

import functools
import logging
import os
import time
from urllib.parse import urlparse

import requests
import yaml
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(PROJECT_DIR, "config.yaml")
ENV_PATH = os.path.join(PROJECT_DIR, ".env")
DB_PATH = os.path.join(PROJECT_DIR, "data", "outreach.db")
DATA_DIR = os.path.join(PROJECT_DIR, "data")
VIDEOS_DIR = os.path.join(DATA_DIR, "videos")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_config_cache = None


def load_config():
    """Load config.yaml + .env, merge API keys from environment."""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    load_dotenv(ENV_PATH)

    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)

    # Override keys from .env (env vars take priority)
    cfg["youtube_api_key"] = os.getenv("YOUTUBE_API_KEY", cfg.get("youtube_api_key", ""))
    cfg["ahrefs_api_key"] = os.getenv("AHREFS_API_KEY", cfg.get("ahrefs_api_key", ""))
    cfg["lusha_api_key"] = os.getenv("LUSHA_API_KEY", cfg.get("lusha_api_key", ""))
    cfg["synthesia_api_key"] = os.getenv("SYNTHESIA_API_KEY", cfg.get("synthesia_api_key", ""))

    _config_cache = cfg
    return cfg


def clear_config_cache():
    """Clear the cached config (useful for testing)."""
    global _config_cache
    _config_cache = None


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def setup_logging(level=logging.INFO):
    """Configure the 'outreach' logger used across all modules."""
    logger = logging.getLogger("outreach")
    if logger.handlers:
        return logger
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    ))
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger


log = setup_logging()


# ---------------------------------------------------------------------------
# HTTP Session (shared, with YouTube consent cookies)
# ---------------------------------------------------------------------------
_session = None


def get_http_session():
    """Return a requests.Session with YouTube consent cookies pre-set."""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        _session.cookies.set("CONSENT", "PENDING+987", domain=".youtube.com")
        _session.cookies.set(
            "SOCS",
            "CAISNQgDEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjMwODI5LjA3X3AxGgJlbiACGgYIgJnPpwY",
            domain=".youtube.com",
        )
    return _session


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------
def retry(max_attempts=3, delay=2, backoff=2, exceptions=(requests.RequestException,)):
    """
    Decorator that retries a function on specified exceptions.

    Args:
        max_attempts: Total attempts (1 = no retry).
        delay: Initial delay between retries in seconds.
        backoff: Multiplier applied to delay after each retry.
        exceptions: Tuple of exception types to catch.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _delay = delay
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_attempts:
                        log.warning(
                            "%s attempt %d/%d failed: %s — retrying in %.1fs",
                            func.__name__, attempt, max_attempts, e, _delay,
                        )
                        time.sleep(_delay)
                        _delay *= backoff
                    else:
                        log.error(
                            "%s failed after %d attempts: %s",
                            func.__name__, max_attempts, e,
                        )
            raise last_exc
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Domain cleaning
# ---------------------------------------------------------------------------
# Social / platform domains to skip when looking for a creator's own website
SKIP_DOMAINS = frozenset([
    "t.me", "instagram.com", "twitter.com", "x.com", "facebook.com",
    "linkedin.com", "tiktok.com", "linktr.ee", "beacons.ai", "bio.link",
    "youtube.com", "youtu.be", "substack.com", "skool.com", "discord.gg",
    "patreon.com", "twitch.tv", "fb.com", "discord.com", "ko-fi.com",
])


def clean_domain(url):
    """
    Extract a clean domain from a URL, stripping paths and www.
    Returns None for social/platform domains or empty input.
    """
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path.split("/")[0]
    if domain.startswith("www."):
        domain = domain[4:]
    domain = domain.lower().strip()
    if not domain:
        return None
    if any(domain.endswith(d) or domain == d for d in SKIP_DOMAINS):
        return None
    return domain


# ---------------------------------------------------------------------------
# Column whitelists (SQL injection prevention)
# ---------------------------------------------------------------------------
CHANNELS_COLUMNS = frozenset({
    "channel_id", "name", "custom_url", "description", "country",
    "default_language", "subscriber_count", "view_count", "video_count",
    "topic_categories", "creator_score", "has_dubbing", "dubbed_languages",
    "discovered_via", "discovered_at", "status", "updated_at",
})

VIDEOS_COLUMNS = frozenset({
    "video_id", "channel_id", "title", "published_at", "duration_seconds",
    "default_audio_language", "audio_tracks", "has_auto_dub", "has_creator_dub",
    "checked_at", "review_status", "review_note", "reviewed_at",
    "selected_for_dubbing",
})

CONTACTS_COLUMNS = frozenset({
    "id", "channel_id", "website_url", "website_domain",
    "email_from_desc", "email_from_about", "email_enriched", "email_source",
    "twitter_url", "instagram_url", "linkedin_url", "tiktok_url",
    "other_links", "enriched_at",
    "website_dr", "website_traffic", "website_keywords", "ahrefs_enriched_at",
    "lusha_first_name", "lusha_last_name", "lusha_job_title", "lusha_company",
    "lusha_enriched_at",
})

DUB_JOBS_COLUMNS = frozenset({
    "id", "channel_id", "source_video_id", "source_language", "target_language",
    "synthesia_asset_id", "synthesia_job_id", "status", "error_message",
    "output_url", "output_path", "created_at", "completed_at",
})

OUTREACH_LOG_COLUMNS = frozenset({
    "id", "channel_id", "outreach_type", "email_to", "subject",
    "gong_call_id", "response_status", "created_at",
})


def validate_columns(kwargs, whitelist, table_name):
    """Raise ValueError if any key in kwargs is not in the whitelist."""
    bad = set(kwargs.keys()) - whitelist
    if bad:
        raise ValueError(f"Invalid column(s) for {table_name}: {bad}")
