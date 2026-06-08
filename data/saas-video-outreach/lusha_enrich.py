#!/usr/bin/env python3
"""
lusha_enrich.py — Enrich SaaS companies with decision-maker contacts via Lusha API.

Searches by company domain + target job titles to find marketing/leadership contacts.
Caps at 3 contacts per company, prioritized by job title order from config.

Usage:
    python3 lusha_enrich.py                  # Enrich all companies
    python3 lusha_enrich.py --dry-run        # Show what would be looked up
    python3 lusha_enrich.py --credits        # Check Lusha credit usage
"""

import argparse
import json
import sys
import time
from datetime import datetime

import requests

import db
from utils import load_config, retry, log

LUSHA_BASE = "https://api.lusha.com"


# ============================================================
# Lusha API calls
# ============================================================

@retry(max_attempts=3, delay=5, exceptions=(requests.RequestException,))
def lusha_company_search(api_key, domain, job_title, limit=3):
    """
    Search Lusha for contacts at a company by domain and job title.
    Returns list of contact dicts.
    """
    resp = requests.get(
        f"{LUSHA_BASE}/v2/company/search",
        headers={"api_key": api_key},
        params={
            "companyDomain": domain,
            "jobTitle": job_title,
            "limit": limit,
            "filterBy": "emailAddresses",
        },
        timeout=15,
    )
    return _handle_lusha_response(resp)


@retry(max_attempts=3, delay=5, exceptions=(requests.RequestException,))
def lusha_person_by_domain(api_key, first_name, last_name, domain):
    """Look up a specific person by name and company domain."""
    resp = requests.get(
        f"{LUSHA_BASE}/v2/person",
        headers={"api_key": api_key},
        params={
            "firstName": first_name,
            "lastName": last_name,
            "companyDomain": domain,
            "filterBy": "emailAddresses",
        },
        timeout=15,
    )
    return _handle_lusha_response(resp)


def _handle_lusha_response(resp):
    """Parse Lusha API response."""
    if resp.status_code == 200:
        data = resp.json()

        # Company search returns a list of people
        if isinstance(data, list):
            contacts = []
            for person in data:
                contact = _parse_person(person)
                if contact:
                    contacts.append(contact)
            return {"found": True, "contacts": contacts}

        # Person search returns a single person
        if isinstance(data, dict) and (data.get("firstName") or data.get("emailAddresses")):
            contact = _parse_person(data)
            return {"found": True, "contacts": [contact] if contact else []}

        return {"found": False, "contacts": []}

    elif resp.status_code == 404:
        return {"found": False, "contacts": []}
    elif resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", 60))
        return {"found": False, "contacts": [], "rate_limited": True, "retry_after": retry_after}
    elif resp.status_code == 402:
        return {"found": False, "contacts": [], "no_credits": True}
    else:
        return {"found": False, "contacts": [], "error": f"{resp.status_code}: {resp.text[:200]}"}


def _parse_person(person):
    """Parse a single person result from Lusha."""
    emails = person.get("emailAddresses", [])
    best_email = None
    email_type = None
    email_confidence = None

    if emails:
        best = emails[0]
        best_email = best.get("email", "")
        email_type = best.get("emailType", "")
        email_confidence = best.get("emailConfidence", "")

    phones = person.get("phoneNumbers", [])
    phone = phones[0].get("localizedNumber", "") if phones else None

    return {
        "first_name": person.get("firstName", ""),
        "last_name": person.get("lastName", ""),
        "job_title": person.get("jobTitle", ""),
        "email": best_email,
        "email_type": email_type,
        "email_confidence": email_confidence,
        "phone": phone,
        "linkedin_url": person.get("linkedinUrl", ""),
    }


def lusha_check_credits(api_key):
    """Check remaining Lusha credits."""
    resp = requests.get(
        f"{LUSHA_BASE}/account/usage",
        headers={"api_key": api_key},
        timeout=15,
    )
    if resp.status_code == 200:
        return resp.json()
    return None


# ============================================================
# Enrichment pipeline
# ============================================================

def enrich_with_lusha(api_key, dry_run=False, limit=None):
    """Enrich companies with Lusha contact data."""
    config = load_config()
    target_titles = config.get("enrichment", {}).get("lusha_target_titles", [
        "VP Marketing", "Head of Marketing", "CMO", "CEO", "Founder",
    ])
    max_contacts = config.get("enrichment", {}).get("lusha_max_contacts", 3)
    lusha_delay = config.get("rate_limits", {}).get("lusha_delay", 2.0)

    # Get companies that have videos but no contacts yet
    with db.get_conn() as conn:
        rows = conn.execute("""
            SELECT c.domain, c.name
            FROM companies c
            WHERE (c.has_youtube_channel = 1 OR c.has_website_videos = 1)
              AND c.domain NOT IN (SELECT DISTINCT domain FROM contacts)
            ORDER BY c.domain_rating DESC NULLS LAST
        """).fetchall()
    companies = [dict(r) for r in rows]

    if limit:
        companies = companies[:limit]

    if not companies:
        log.info("No companies need Lusha enrichment.")
        return

    log.info("Enriching %d companies via Lusha (target titles: %s)", len(companies), ", ".join(target_titles[:3]))

    found_count = 0
    skipped_count = 0
    failed_count = 0

    for i, comp in enumerate(companies, 1):
        domain = comp["domain"]
        name = comp["name"]

        existing_contacts = db.count_contacts_for_company(domain)
        if existing_contacts >= max_contacts:
            skipped_count += 1
            continue

        log.info("[%d/%d] %s (%s)", i, len(companies), name, domain)

        if dry_run:
            log.info("  Would search: %s with titles: %s", domain, ", ".join(target_titles[:3]))
            continue

        contacts_added = 0
        for title in target_titles:
            if contacts_added >= max_contacts:
                break

            try:
                result = lusha_company_search(api_key, domain, title, limit=1)
            except Exception as e:
                log.warning("  Lusha error for %s/%s: %s", domain, title, e)
                continue

            if result.get("rate_limited"):
                wait = result.get("retry_after", 60)
                log.warning("  Rate limited! Waiting %ds...", wait)
                time.sleep(wait)
                try:
                    result = lusha_company_search(api_key, domain, title, limit=1)
                except Exception:
                    continue

            if result.get("no_credits"):
                log.error("  Out of Lusha credits. Stopping.")
                return

            if result.get("found") and result.get("contacts"):
                for contact in result["contacts"]:
                    if contacts_added >= max_contacts:
                        break
                    if not contact.get("email"):
                        continue

                    log.info("  Found: %s %s — %s (%s)",
                             contact["first_name"], contact["last_name"],
                             contact["job_title"], contact["email"])

                    db.add_contact(
                        domain,
                        first_name=contact["first_name"],
                        last_name=contact["last_name"],
                        job_title=contact["job_title"],
                        email=contact["email"],
                        email_type=contact.get("email_type"),
                        email_confidence=contact.get("email_confidence"),
                        phone=contact.get("phone"),
                        linkedin_url=contact.get("linkedin_url"),
                    )
                    contacts_added += 1

            time.sleep(lusha_delay)

        if contacts_added > 0:
            found_count += 1
        else:
            failed_count += 1

    log.info("=" * 60)
    log.info("  Lusha enrichment complete!")
    log.info("  Companies with contacts: %d", found_count)
    log.info("  Skipped (already had):   %d", skipped_count)
    log.info("  No contacts found:       %d", failed_count)


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Lusha Contact Enrichment")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be looked up")
    parser.add_argument("--credits", action="store_true", help="Check Lusha credit usage")
    parser.add_argument("--limit", type=int, help="Max companies to enrich")
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

    enrich_with_lusha(api_key, dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    main()
