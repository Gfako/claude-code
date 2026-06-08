#!/usr/bin/env python3
"""
lusha_enrich.py — Enrich YouTube creators with emails via Lusha API

Reads channels from the database that have been YouTube-enriched,
extracts person names from channel names, and uses Lusha to find
email addresses via:
  1. LinkedIn URL (best match)
  2. First name + Last name + website domain
  3. First name + Last name + company name (channel name)

Usage:
    python3 lusha_enrich.py                  # Enrich all dubbed channels
    python3 lusha_enrich.py --dry-run        # Show what would be looked up
    python3 lusha_enrich.py --credits        # Check Lusha credit usage
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime

import requests

import db
from utils import load_config, clean_domain, retry, log

LUSHA_BASE = "https://api.lusha.com"


# ============================================================
# 1. NAME EXTRACTION
# ============================================================

NAME_SEPARATORS = re.compile(r"\s*[|\-–—·•/]\s*")

NON_NAME_WORDS = {
    "tutorial", "tutoriales", "tv", "official", "oficial", "channel", "canal",
    "finanzas", "personales", "coach", "de", "del", "la", "el", "los", "las",
    "soy", "mr", "ms", "dr", "the", "my", "mi", "un", "una", "y", "and",
    "finance", "cooking", "tech", "review", "vlog", "world", "mundo",
    "piano", "guitarra", "guitar", "music", "games", "gaming", "drywall",
    "audiolibros", "riqueza", "ahorro", "inversiones", "club",
}


def extract_person_name(channel_name):
    """
    Extract (first_name, last_name) from a YouTube channel name.
    Returns (None, None) if not identifiable.
    """
    if not channel_name:
        return None, None

    parts = NAME_SEPARATORS.split(channel_name)
    candidate = parts[0].strip()
    candidate = re.sub(r"[^\w\s.\-']", "", candidate, flags=re.UNICODE).strip()

    for prefix in ["Soy ", "soy ", "Coach ", "Dr. ", "Dr "]:
        if candidate.startswith(prefix):
            candidate = candidate[len(prefix):]

    words = candidate.split()
    name_words = [w for w in words if w.lower() not in NON_NAME_WORDS and len(w) > 1]

    if len(name_words) == 2:
        return name_words[0], name_words[1]
    elif len(name_words) == 3:
        return name_words[0], name_words[-1]
    elif len(name_words) == 1:
        first = name_words[0]
        if len(parts) > 1:
            second_part = parts[1].strip().split()
            second_words = [w for w in second_part if w.lower() not in NON_NAME_WORDS and len(w) > 1]
            if second_words:
                return first, second_words[0]
        return first, None

    return None, None


# ============================================================
# 2. LUSHA API CALLS
# ============================================================

@retry(max_attempts=3, delay=5, exceptions=(requests.RequestException,))
def lusha_lookup_by_linkedin(api_key, linkedin_url):
    resp = requests.get(
        f"{LUSHA_BASE}/v2/person",
        headers={"api_key": api_key},
        params={"linkedinUrl": linkedin_url, "filterBy": "emailAddresses"},
        timeout=15,
    )
    return _handle_lusha_response(resp)


@retry(max_attempts=3, delay=5, exceptions=(requests.RequestException,))
def lusha_lookup_by_name_domain(api_key, first_name, last_name, domain):
    resp = requests.get(
        f"{LUSHA_BASE}/v2/person",
        headers={"api_key": api_key},
        params={
            "firstName": first_name, "lastName": last_name,
            "companyDomain": domain, "filterBy": "emailAddresses",
        },
        timeout=15,
    )
    return _handle_lusha_response(resp)


@retry(max_attempts=3, delay=5, exceptions=(requests.RequestException,))
def lusha_lookup_by_name_company(api_key, first_name, last_name, company_name):
    resp = requests.get(
        f"{LUSHA_BASE}/v2/person",
        headers={"api_key": api_key},
        params={
            "firstName": first_name, "lastName": last_name,
            "companyName": company_name, "filterBy": "emailAddresses",
        },
        timeout=15,
    )
    return _handle_lusha_response(resp)


def _handle_lusha_response(resp):
    """Parse Lusha API response and extract emails."""
    if resp.status_code == 200:
        data = resp.json()
        emails = []
        for e in data.get("emailAddresses", []):
            emails.append({
                "email": e.get("email", ""),
                "type": e.get("emailType", ""),
                "confidence": e.get("emailConfidence", ""),
            })
        return {
            "found": True,
            "first_name": data.get("firstName", ""),
            "last_name": data.get("lastName", ""),
            "job_title": data.get("jobTitle", ""),
            "company": data.get("company", ""),
            "emails": emails,
        }
    elif resp.status_code == 404:
        return {"found": False, "emails": []}
    elif resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", 60))
        return {"found": False, "emails": [], "rate_limited": True, "retry_after": retry_after}
    elif resp.status_code == 402:
        return {"found": False, "emails": [], "no_credits": True}
    else:
        return {"found": False, "emails": [], "error": f"{resp.status_code}: {resp.text[:200]}"}


def lusha_check_credits(api_key):
    resp = requests.get(f"{LUSHA_BASE}/account/usage", headers={"api_key": api_key}, timeout=15)
    if resp.status_code == 200:
        return resp.json()
    return None


# ============================================================
# 3. ENRICHMENT PIPELINE
# ============================================================

def enrich_with_lusha(api_key, dry_run=False):
    """Enrich all dubbed channels with Lusha email lookup."""
    channels = db.get_dubbed_channels()
    if not channels:
        log.info("No dubbed channels in database.")
        return

    log.info("Enriching %d dubbed channels via Lusha", len(channels))

    found_count = 0
    skipped_count = 0
    failed_count = 0

    for i, ch in enumerate(channels, 1):
        name = ch["name"]
        channel_id = ch["channel_id"]
        contact = db.get_contact(channel_id)

        if contact and contact.get("email_enriched"):
            log.debug("[%d/%d] %s — already has email, skipping", i, len(channels), name)
            skipped_count += 1
            continue

        first_name, last_name = extract_person_name(name)

        website_domain = None
        linkedin_url = None
        if contact:
            website_domain = clean_domain(contact.get("website_url", ""))
            linkedin_url = contact.get("linkedin_url")

        # Infer last name from website domain
        if first_name and not last_name and website_domain:
            domain_name = website_domain.split(".")[0]
            fn_lower = first_name.lower()
            if domain_name.startswith(fn_lower) and len(domain_name) > len(fn_lower):
                inferred_last = domain_name[len(fn_lower):]
                last_name = inferred_last.capitalize()
                log.info("  Inferred last name from domain: %s %s", first_name, last_name)

        log.info("[%d/%d] %s — name: %s %s, domain: %s, linkedin: %s",
                 i, len(channels), name, first_name, last_name,
                 website_domain or "none", linkedin_url or "none")

        if dry_run:
            strategies = []
            if linkedin_url:
                strategies.append(f"LinkedIn: {linkedin_url}")
            if first_name and last_name and website_domain:
                strategies.append(f"Name+Domain: {first_name} {last_name} @ {website_domain}")
            if first_name and last_name:
                strategies.append(f"Name+Company: {first_name} {last_name} @ {name}")
            log.info("  Would try: %s", " -> ".join(strategies) if strategies else "no strategy")
            continue

        result = None

        # Strategy 1: LinkedIn URL
        if linkedin_url:
            log.info("  Trying LinkedIn lookup...")
            result = lusha_lookup_by_linkedin(api_key, linkedin_url)
            if result.get("rate_limited"):
                log.warning("  Rate limited! Waiting %ds...", result["retry_after"])
                time.sleep(result["retry_after"])
                result = lusha_lookup_by_linkedin(api_key, linkedin_url)
            if result.get("no_credits"):
                log.error("  Out of Lusha credits. Stopping.")
                break
            time.sleep(2)

        # Strategy 2: Name + website domain
        if first_name and last_name and website_domain and (not result or not result.get("found")):
            log.info("  Trying name + domain: %s %s @ %s", first_name, last_name, website_domain)
            result = lusha_lookup_by_name_domain(api_key, first_name, last_name, website_domain)
            if result.get("rate_limited"):
                time.sleep(result["retry_after"])
                result = lusha_lookup_by_name_domain(api_key, first_name, last_name, website_domain)
            if result.get("no_credits"):
                log.error("  Out of Lusha credits. Stopping.")
                break
            time.sleep(2)

        # Strategy 3: Name + channel name as company
        if first_name and last_name and (not result or not result.get("found")):
            company = NAME_SEPARATORS.split(name)[0].strip()
            log.info("  Trying name + company: %s %s @ %s", first_name, last_name, company)
            result = lusha_lookup_by_name_company(api_key, first_name, last_name, company)
            if result.get("rate_limited"):
                time.sleep(result["retry_after"])
                result = lusha_lookup_by_name_company(api_key, first_name, last_name, company)
            if result.get("no_credits"):
                log.error("  Out of Lusha credits. Stopping.")
                break
            time.sleep(2)

        # Process result
        if result and result.get("found") and result.get("emails"):
            best_email = result["emails"][0]["email"]
            log.info("  >>> FOUND: %s (type=%s, confidence=%s)",
                     best_email, result["emails"][0].get("type"), result["emails"][0].get("confidence"))

            db.upsert_contact(
                channel_id,
                email_enriched=best_email,
                email_source="lusha",
                lusha_first_name=result.get("first_name", ""),
                lusha_last_name=result.get("last_name", ""),
                lusha_job_title=result.get("job_title", ""),
                lusha_company=result.get("company", ""),
                lusha_enriched_at=datetime.now().isoformat(),
            )
            found_count += 1
        else:
            error = result.get("error", "") if result else "no lookup strategy"
            log.info("  No email found. %s", error)
            failed_count += 1

    log.info("=" * 60)
    log.info("  Lusha enrichment complete!")
    log.info("  Emails found:  %d", found_count)
    log.info("  Skipped:       %d", skipped_count)
    log.info("  Not found:     %d", failed_count)


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Lusha Email Enrichment")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be looked up")
    parser.add_argument("--credits", action="store_true", help="Check Lusha credit usage")
    args = parser.parse_args()

    config = load_config()
    api_key = config.get("lusha_api_key", "")

    if args.credits:
        if not api_key:
            log.error("No lusha_api_key configured. Set LUSHA_API_KEY in .env")
            return
        usage = lusha_check_credits(api_key)
        if usage:
            print(json.dumps(usage, indent=2))
        else:
            log.error("Could not fetch credit info.")
        return

    if not api_key and not args.dry_run:
        log.error("No lusha_api_key configured. Set LUSHA_API_KEY in .env or use --dry-run")
        sys.exit(1)

    enrich_with_lusha(api_key, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
