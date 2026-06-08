"""Shared utilities: config loading, logging, retry decorator, URL/domain helpers."""

import functools
import logging
import os
import time
from pathlib import Path
from urllib.parse import urlparse

import yaml
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config(config_path=None):
    """Load config from YAML file, with .env overrides."""
    load_dotenv()

    if config_path is None:
        config_path = Path(__file__).parent / "config.yaml"

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # .env overrides
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if os.getenv("SF_CLI_PATH"):
        config["screaming_frog"]["cli_path"] = os.getenv("SF_CLI_PATH")
    if os.getenv("SF_OUTPUT_DIR"):
        config["screaming_frog"]["output_dir"] = os.getenv("SF_OUTPUT_DIR")

    return config


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(level=logging.INFO):
    """Configure structured logging."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    # Quiet noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    return logging.getLogger("salience")


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------

def retry(max_attempts=3, delay=2, backoff=2, exceptions=(Exception,)):
    """Retry a function with exponential backoff."""
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
                        logging.getLogger("salience").warning(
                            f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                            f"Retrying in {_delay}s..."
                        )
                        time.sleep(_delay)
                        _delay *= backoff
            raise last_exc
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# URL / Domain helpers
# ---------------------------------------------------------------------------

def clean_domain(domain_or_url):
    """Extract clean domain from a URL or domain string.

    'https://www.synthesia.io/blog/foo' → 'synthesia.io'
    'www.synthesia.io' → 'synthesia.io'
    'synthesia.io' → 'synthesia.io'
    """
    s = domain_or_url.strip().lower()
    if not s.startswith(("http://", "https://")):
        s = "https://" + s
    parsed = urlparse(s)
    host = parsed.hostname or ""
    if host.startswith("www."):
        host = host[4:]
    return host


def domain_to_url(domain, subfolder=None):
    """Convert domain to crawlable URL.

    'synthesia.io', '/blog/' → 'https://www.synthesia.io/blog/'
    """
    base = f"https://www.{clean_domain(domain)}"
    if subfolder:
        sf = subfolder.strip("/")
        base = f"{base}/{sf}/"
    return base


def url_matches_subfolder(url, domain, subfolder):
    """Check if a URL belongs to a domain + subfolder scope."""
    if subfolder is None:
        return clean_domain(url) == clean_domain(domain)
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    target = subfolder.rstrip("/")
    return clean_domain(url) == clean_domain(domain) and path.startswith(target)


def normalize_url(url):
    """Normalize URL: lowercase, strip trailing slash, remove fragments."""
    parsed = urlparse(url.lower().strip())
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"
