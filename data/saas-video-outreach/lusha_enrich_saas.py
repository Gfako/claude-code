#!/usr/bin/env python3
"""
lusha_enrich_saas.py — Enrich approved SaaS companies with Lusha contacts.

Searches for mid-level marketing/content/partnerships roles.
Saves 1 contact per company to minimize credit usage.

Usage:
    python3 lusha_enrich_saas.py --dry-run     # Preview without API calls
    python3 lusha_enrich_saas.py               # Run enrichment
    python3 lusha_enrich_saas.py --credits     # Check credit balance
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
DECISIONS_FILE = os.path.join(DATA_DIR, "review_decisions.json")

load_dotenv(ENV_PATH)
LUSHA_API_KEY = os.getenv("LUSHA_API_KEY", "")
LUSHA_BASE = "https://api.lusha.com"

# Roles to search for, in priority order
TARGET_TITLES = [
    "Content Marketing Manager",
    "SEO Manager",
    "Editor",
    "Managing Editor",
    "Partnerships Manager",
    "Business Development Manager",
    "Product Marketing Manager",
    "Localization Manager",
    "Global Content Lead",
    "Growth Manager",
    "Marketing Manager",
    "Marketing Associate",
    "Content Manager",
    "Head of Content",
    "Head of Partnerships",
    "Video Producer",
    "Marketing Director",
]


def check_credits():
    resp = requests.get(f"{LUSHA_BASE}/account/usage", headers={"api_key": LUSHA_API_KEY}, timeout=15)
    if resp.status_code == 200:
        return resp.json()
    return None


def lusha_search_by_domain_title(domain, title):
    """Search Lusha for a person by company domain + job title."""
    resp = requests.get(
        f"{LUSHA_BASE}/v2/person",
        headers={"api_key": LUSHA_API_KEY},
        params={
            "companyDomain": domain,
            "jobTitle": title,
            "filterBy": "emailAddresses",
        },
        timeout=15,
    )

    if resp.status_code == 200:
        data = resp.json()
        emails = [e.get("email", "") for e in data.get("emailAddresses", []) if e.get("email")]
        if emails:
            return {
                "found": True,
                "first_name": data.get("firstName", ""),
                "last_name": data.get("lastName", ""),
                "job_title": data.get("jobTitle", ""),
                "company": data.get("company", ""),
                "email": emails[0],
                "all_emails": emails,
            }
        return {"found": False}
    elif resp.status_code == 404:
        return {"found": False}
    elif resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", 60))
        return {"found": False, "rate_limited": True, "retry_after": retry_after}
    elif resp.status_code == 402:
        return {"found": False, "no_credits": True}
    else:
        return {"found": False, "error": f"{resp.status_code}: {resp.text[:100]}"}


def run_enrichment(dry_run=False):
    with open(DECISIONS_FILE) as f:
        decisions = json.load(f)

    # Only companies with dubbed videos
    companies = [(domain, v) for domain, v in decisions.items()
                 if v.get('status') == 'approved'
                 and v.get('synthesia_share_link')
                 and not v.get('lusha_contact')]  # Skip already enriched

    if not companies:
        print("No companies to enrich (all already done or no dubbed videos).")
        return

    print(f"\n  {len(companies)} companies to enrich")
    print(f"  Roles: {', '.join(TARGET_TITLES[:6])}...")
    print(f"  Max credits: ~{len(companies)} (1 per company)\n")

    if dry_run:
        for domain, v in companies:
            print(f"  {v.get('name','')[:35]:<36} {domain}")
        print(f"\n  Dry run — no API calls made.")
        return

    found_count = 0
    not_found_count = 0
    credits_used = 0

    for i, (domain, v) in enumerate(companies):
        name = v.get('name', domain)
        print(f"[{i+1}/{len(companies)}] {name[:35]}", end="", flush=True)

        contact = None
        for title in TARGET_TITLES:
            result = lusha_search_by_domain_title(domain, title)
            credits_used += 1

            if result.get("rate_limited"):
                print(f" — rate limited, waiting {result['retry_after']}s")
                time.sleep(result["retry_after"])
                result = lusha_search_by_domain_title(domain, title)
                credits_used += 1

            if result.get("no_credits"):
                print(" — OUT OF CREDITS. Stopping.")
                save_decisions(decisions)
                return

            if result.get("found"):
                contact = result
                print(f" → {result['first_name']} {result['last_name']} ({result['job_title']}) — {result['email']}")
                break

            time.sleep(0.5)  # Small delay between title searches

        if contact:
            decisions[domain]['lusha_contact'] = {
                'first_name': contact['first_name'],
                'last_name': contact['last_name'],
                'job_title': contact['job_title'],
                'company': contact['company'],
                'email': contact['email'],
                'enriched_at': datetime.now().isoformat(),
            }
            found_count += 1
        else:
            decisions[domain]['lusha_contact'] = {'found': False, 'enriched_at': datetime.now().isoformat()}
            not_found_count += 1
            print(f" → no contact found")

        # Save progress every 5 companies
        if (i + 1) % 5 == 0:
            save_decisions(decisions)

        time.sleep(1)  # Rate limit between companies

    save_decisions(decisions)
    export_with_contacts(decisions)

    print(f"\n{'='*50}")
    print(f"  Enrichment complete!")
    print(f"  Found:     {found_count}")
    print(f"  Not found: {not_found_count}")
    print(f"  Credits used: ~{credits_used}")
    print(f"{'='*50}\n")


def save_decisions(decisions):
    with open(DECISIONS_FILE, 'w') as f:
        json.dump(decisions, f, indent=2)


def export_with_contacts(decisions):
    """Export approved companies with contacts and Synthesia links."""
    approved = {k: v for k, v in decisions.items() if v.get('status') == 'approved'}
    output_path = os.path.join(DATA_DIR, "outreach_final.csv")

    fieldnames = [
        "Company Name", "Domain", "Website", "Category", "Domain Rating",
        "Organic Traffic", "Organic Keywords",
        "Contact First Name", "Contact Last Name", "Contact Email", "Contact Job Title",
        "Selected Video URL", "Video Source", "Dubbed To", "Synthesia Share Link",
        "Trim Start", "Trim End",
        "Outreach Status", "Matched Customer", "Customer Lifecycle", "Match Type",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for domain, d in sorted(approved.items(), key=lambda x: x[1].get('domain_rating') or 0, reverse=True):
            contact = d.get('lusha_contact', {})
            start = d.get('trim_start', 0)
            end = d.get('trim_end', 30)
            writer.writerow({
                "Company Name": d.get('name', ''),
                "Domain": domain,
                "Website": d.get('website_url', ''),
                "Category": d.get('category', ''),
                "Domain Rating": d.get('domain_rating', ''),
                "Organic Traffic": d.get('org_traffic', ''),
                "Organic Keywords": d.get('org_keywords', ''),
                "Contact First Name": contact.get('first_name', ''),
                "Contact Last Name": contact.get('last_name', ''),
                "Contact Email": contact.get('email', ''),
                "Contact Job Title": contact.get('job_title', ''),
                "Selected Video URL": d.get('selected_video_url', ''),
                "Video Source": d.get('video_source', ''),
                "Dubbed To": d.get('dubbed_to', ''),
                "Synthesia Share Link": d.get('synthesia_share_link', ''),
                "Trim Start": f"{start // 60}:{start % 60:02d}" if isinstance(start, int) else start,
                "Trim End": f"{end // 60}:{end % 60:02d}" if isinstance(end, int) else end,
                "Outreach Status": d.get('outreach_status', ''),
                "Matched Customer": d.get('matched_customer', ''),
                "Customer Lifecycle": d.get('customer_lifecycle', ''),
                "Match Type": d.get('match_type', ''),
            })

    print(f"Exported to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Lusha contact enrichment for SaaS companies")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--credits", action="store_true")
    args = parser.parse_args()

    if not LUSHA_API_KEY:
        print("ERROR: No LUSHA_API_KEY in .env")
        sys.exit(1)

    if args.credits:
        usage = check_credits()
        if usage:
            print(json.dumps(usage, indent=2))
        return

    if args.dry_run:
        run_enrichment(dry_run=True)
        return

    run_enrichment()


if __name__ == "__main__":
    main()
