#!/usr/bin/env python3
"""
export.py — Export pipeline data to CSV

All export logic in one place. Uses a single JOIN query with
GROUP_CONCAT to avoid N+1 queries.

Usage:
    python3 export.py                     # Export full leads CSV
    python3 export.py --zoominfo          # Export for ZoomInfo/Cognism/Lusha
    python3 export.py --dubbed-only       # Export only dubbed channels
    python3 export.py --output path.csv   # Custom output path
"""

import argparse
import csv
import os

import db
from utils import log, DATA_DIR


# ============================================================
# Main export — full leads with all columns
# ============================================================

def export_leads(output_path=None, dubbed_only=False):
    """Export enriched leads with all data, using a single JOIN query."""
    if output_path is None:
        output_path = os.path.join(DATA_DIR, "final_leads.csv")

    where = "WHERE c.has_dubbing = 1" if dubbed_only else ""

    with db.get_conn() as conn:
        rows = conn.execute(f"""
            SELECT
                c.channel_id,
                c.name,
                c.custom_url,
                c.country,
                c.default_language,
                c.subscriber_count,
                c.view_count,
                c.video_count,
                c.creator_score,
                c.has_dubbing,
                c.dubbed_languages,
                c.discovered_via,
                c.status,
                ct.website_url,
                ct.website_domain,
                ct.email_from_desc,
                ct.email_from_about,
                ct.email_enriched,
                ct.email_source,
                ct.twitter_url,
                ct.instagram_url,
                ct.linkedin_url,
                ct.tiktok_url,
                ct.website_dr,
                ct.website_traffic,
                ct.website_keywords,
                ct.lusha_first_name,
                ct.lusha_last_name,
                ct.lusha_job_title,
                ct.lusha_company,
                GROUP_CONCAT(
                    CASE WHEN v.has_auto_dub = 1
                    THEN 'https://www.youtube.com/watch?v=' || v.video_id
                    END,
                    ' | '
                ) as dubbed_video_urls,
                GROUP_CONCAT(
                    CASE WHEN v.review_status = 'approved'
                    THEN v.video_id
                    END,
                    ','
                ) as approved_video_ids
            FROM channels c
            LEFT JOIN contacts ct ON c.channel_id = ct.channel_id
            LEFT JOIN videos v ON c.channel_id = v.channel_id
            {where}
            GROUP BY c.channel_id
            ORDER BY c.subscriber_count DESC
        """).fetchall()

    if not rows:
        log.info("No data to export.")
        return

    # Figure out max dubbed videos across all channels for column count
    MAX_VIDEO_COLS = 10

    fieldnames = [
        "Channel Name", "Subscribers", "Country", "Language", "Niche",
        "Channel URL", "Creator Score", "Status",
        "Email", "Email Source", "Website", "Website Domain",
        "Website DR", "Website Traffic", "Website Keywords",
        "Lusha Name", "Lusha Job Title", "Lusha Company",
        "Twitter", "Instagram", "LinkedIn", "TikTok",
        "Dubbed Languages",
    ] + [f"Dubbed Video {i+1}" for i in range(MAX_VIDEO_COLS)]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            r = dict(row)
            ch_id = r["channel_id"]
            custom = r.get("custom_url", "")
            channel_url = f"https://www.youtube.com/{custom}" if custom else f"https://www.youtube.com/channel/{ch_id}"

            # Best email: enriched > about > description
            email = r.get("email_enriched") or r.get("email_from_about") or r.get("email_from_desc") or ""
            email_source = r.get("email_source") or ""
            if not email_source:
                if r.get("email_enriched"):
                    email_source = "lusha"
                elif r.get("email_from_about"):
                    email_source = "about_page"
                elif r.get("email_from_desc"):
                    email_source = "description"

            # Niche from discovered_via
            niche = r.get("discovered_via") or ""
            if "(" in niche:
                niche = niche[:niche.index("(")].strip()

            # Language
            lang = r.get("default_language") or ""
            if not lang and "/" in (r.get("discovered_via") or ""):
                lang = r["discovered_via"].split("/")[-1].rstrip(")")

            # Lusha name
            lusha_name = ""
            if r.get("lusha_first_name") or r.get("lusha_last_name"):
                lusha_name = f"{r.get('lusha_first_name', '')} {r.get('lusha_last_name', '')}".strip()

            # Split dubbed video URLs into separate columns
            dubbed_urls_raw = r.get("dubbed_video_urls", "") or ""
            dubbed_urls = [u.strip() for u in dubbed_urls_raw.split(" | ") if u.strip()]

            row_data = {
                "Channel Name": r["name"],
                "Subscribers": r["subscriber_count"],
                "Country": r.get("country", ""),
                "Language": lang,
                "Niche": niche,
                "Channel URL": channel_url,
                "Creator Score": r.get("creator_score", ""),
                "Status": r.get("status", ""),
                "Email": email,
                "Email Source": email_source,
                "Website": r.get("website_url", ""),
                "Website Domain": r.get("website_domain", ""),
                "Website DR": r.get("website_dr", ""),
                "Website Traffic": r.get("website_traffic", ""),
                "Website Keywords": r.get("website_keywords", ""),
                "Lusha Name": lusha_name,
                "Lusha Job Title": r.get("lusha_job_title", ""),
                "Lusha Company": r.get("lusha_company", ""),
                "Twitter": r.get("twitter_url", ""),
                "Instagram": r.get("instagram_url", ""),
                "LinkedIn": r.get("linkedin_url", ""),
                "TikTok": r.get("tiktok_url", ""),
                "Dubbed Languages": r.get("dubbed_languages", ""),
            }
            for i in range(MAX_VIDEO_COLS):
                row_data[f"Dubbed Video {i+1}"] = dubbed_urls[i] if i < len(dubbed_urls) else ""

            writer.writerow(row_data)

    log.info("Exported %d leads to %s", len(rows), output_path)


# ============================================================
# ZoomInfo/Cognism format export
# ============================================================

def export_for_zoominfo(output_path=None):
    """Export for ZoomInfo/Cognism/Lusha bulk lookup."""
    if output_path is None:
        output_path = os.path.join(DATA_DIR, "zoominfo_lookup.csv")

    with db.get_conn() as conn:
        rows = conn.execute("""
            SELECT c.channel_id, c.name, c.country, c.subscriber_count,
                   ct.website_url, ct.website_domain, ct.email_from_desc,
                   ct.email_from_about, ct.linkedin_url
            FROM channels c
            JOIN contacts ct ON c.channel_id = ct.channel_id
            WHERE c.has_dubbing = 1
              AND (ct.website_url IS NOT NULL OR ct.linkedin_url IS NOT NULL)
            ORDER BY c.subscriber_count DESC
        """).fetchall()

    if not rows:
        log.info("No leads with websites/LinkedIn for ZoomInfo lookup.")
        return

    fieldnames = [
        "channel_name", "website_domain", "linkedin_url", "country",
        "subscriber_count", "known_email", "channel_url",
    ]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            r = dict(row)
            writer.writerow({
                "channel_name": r["name"],
                "website_domain": r.get("website_domain", ""),
                "linkedin_url": r.get("linkedin_url", ""),
                "country": r.get("country", ""),
                "subscriber_count": r.get("subscriber_count", ""),
                "known_email": r.get("email_from_desc") or r.get("email_from_about") or "",
                "channel_url": f"https://www.youtube.com/channel/{r['channel_id']}",
            })

    log.info("Exported %d leads for ZoomInfo/Cognism to %s", len(rows), output_path)


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Export pipeline data to CSV")
    parser.add_argument("--output", "-o", type=str, help="Output CSV path")
    parser.add_argument("--zoominfo", action="store_true", help="Export for ZoomInfo/Cognism")
    parser.add_argument("--dubbed-only", action="store_true", help="Only export dubbed channels")
    args = parser.parse_args()

    if args.zoominfo:
        export_for_zoominfo(output_path=args.output)
    else:
        export_leads(output_path=args.output, dubbed_only=args.dubbed_only)


if __name__ == "__main__":
    main()
