#!/usr/bin/env python3
"""
export.py — Export SaaS outreach data to CSV.

Uses a single JOIN query with GROUP_CONCAT to avoid N+1 queries.
Exports company info, YouTube data, Ahrefs metrics, approved video URLs,
and contact details.

Usage:
    python3 export.py                                    # Export all with videos
    python3 export.py --approved-only                    # Only approved videos
    python3 export.py --min-dr 20                        # Filter by Domain Rating
    python3 export.py --output data/custom_export.csv    # Custom output path
"""

import argparse
import csv
import os

import db
from utils import log, DATA_DIR


MAX_VIDEO_COLS = 5
MAX_CONTACT_COLS = 3


def export_leads(output_path=None, video_only=True, approved_only=False, min_dr=None):
    """Export enriched leads with all data, using JOIN queries."""
    if output_path is None:
        output_path = os.path.join(DATA_DIR, "saas_leads.csv")

    # Build WHERE clauses
    where_parts = []
    if video_only:
        where_parts.append("(c.has_youtube_channel = 1 OR c.has_website_videos = 1)")
    if min_dr is not None:
        where_parts.append(f"c.domain_rating >= {float(min_dr)}")

    where = "WHERE " + " AND ".join(where_parts) if where_parts else ""

    video_status_filter = ""
    if approved_only:
        video_status_filter = "AND v.review_status = 'approved'"

    with db.get_conn() as conn:
        rows = conn.execute(f"""
            SELECT
                c.domain,
                c.name,
                c.website_url,
                c.category,
                c.category_source,
                c.employee_count,
                c.review_count,
                c.rating,
                c.has_youtube_channel,
                c.youtube_channel_url,
                c.youtube_subscriber_count,
                c.youtube_video_count,
                c.has_website_videos,
                c.domain_rating,
                c.org_traffic,
                c.org_keywords,
                c.status,
                GROUP_CONCAT(
                    DISTINCT CASE WHEN v.video_url IS NOT NULL {video_status_filter}
                    THEN v.video_url END,
                    ' | '
                ) as video_urls,
                GROUP_CONCAT(
                    DISTINCT CASE WHEN v.video_url IS NOT NULL {video_status_filter}
                    THEN v.video_type END,
                    ' | '
                ) as video_types
            FROM companies c
            LEFT JOIN company_videos v ON c.domain = v.domain
            {where}
            GROUP BY c.domain
            ORDER BY c.domain_rating DESC NULLS LAST, c.org_traffic DESC NULLS LAST
        """).fetchall()

    if not rows:
        log.info("No data to export.")
        return

    # Get contacts separately to handle multiple per company
    contacts_by_domain = {}
    with db.get_conn() as conn:
        contact_rows = conn.execute("""
            SELECT domain, first_name, last_name, job_title, email, phone, linkedin_url
            FROM contacts
            ORDER BY domain, id
        """).fetchall()
    for cr in contact_rows:
        cr = dict(cr)
        d = cr["domain"]
        contacts_by_domain.setdefault(d, []).append(cr)

    fieldnames = [
        "Company Name", "Domain", "Website", "Category", "Sources",
        "Employees", "Reviews", "Rating",
        "Has YouTube", "YouTube Channel", "YouTube Subscribers", "YouTube Videos",
        "Has Website Videos",
        "Domain Rating", "Organic Traffic", "Organic Keywords",
        "Status",
    ] + [f"Video URL {i+1}" for i in range(MAX_VIDEO_COLS)
    ] + [f"Video Type {i+1}" for i in range(MAX_VIDEO_COLS)]

    # Contact columns
    for i in range(MAX_CONTACT_COLS):
        fieldnames.extend([
            f"Contact {i+1} Name",
            f"Contact {i+1} Title",
            f"Contact {i+1} Email",
            f"Contact {i+1} Phone",
            f"Contact {i+1} LinkedIn",
        ])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            r = dict(row)
            domain = r["domain"]

            # Split video URLs into separate columns
            video_urls_raw = r.get("video_urls", "") or ""
            video_urls = [u.strip() for u in video_urls_raw.split(" | ") if u.strip()]
            video_types_raw = r.get("video_types", "") or ""
            video_types = [t.strip() for t in video_types_raw.split(" | ") if t.strip()]

            row_data = {
                "Company Name": r["name"],
                "Domain": domain,
                "Website": r.get("website_url", ""),
                "Category": r.get("category", ""),
                "Sources": r.get("category_source", ""),
                "Employees": r.get("employee_count", ""),
                "Reviews": r.get("review_count", ""),
                "Rating": r.get("rating", ""),
                "Has YouTube": "Yes" if r.get("has_youtube_channel") else "No",
                "YouTube Channel": r.get("youtube_channel_url", ""),
                "YouTube Subscribers": r.get("youtube_subscriber_count", ""),
                "YouTube Videos": r.get("youtube_video_count", ""),
                "Has Website Videos": "Yes" if r.get("has_website_videos") else "No",
                "Domain Rating": r.get("domain_rating", ""),
                "Organic Traffic": r.get("org_traffic", ""),
                "Organic Keywords": r.get("org_keywords", ""),
                "Status": r.get("status", ""),
            }

            for i in range(MAX_VIDEO_COLS):
                row_data[f"Video URL {i+1}"] = video_urls[i] if i < len(video_urls) else ""
                row_data[f"Video Type {i+1}"] = video_types[i] if i < len(video_types) else ""

            # Add contacts
            contacts = contacts_by_domain.get(domain, [])
            for i in range(MAX_CONTACT_COLS):
                if i < len(contacts):
                    c = contacts[i]
                    name = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
                    row_data[f"Contact {i+1} Name"] = name
                    row_data[f"Contact {i+1} Title"] = c.get("job_title", "")
                    row_data[f"Contact {i+1} Email"] = c.get("email", "")
                    row_data[f"Contact {i+1} Phone"] = c.get("phone", "")
                    row_data[f"Contact {i+1} LinkedIn"] = c.get("linkedin_url", "")
                else:
                    row_data[f"Contact {i+1} Name"] = ""
                    row_data[f"Contact {i+1} Title"] = ""
                    row_data[f"Contact {i+1} Email"] = ""
                    row_data[f"Contact {i+1} Phone"] = ""
                    row_data[f"Contact {i+1} LinkedIn"] = ""

            writer.writerow(row_data)

    log.info("Exported %d leads to %s", len(rows), output_path)


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Export SaaS outreach data to CSV")
    parser.add_argument("--output", "-o", type=str, help="Output CSV path")
    parser.add_argument("--video-only", action="store_true", default=True,
                        help="Only export companies with videos (default)")
    parser.add_argument("--all-companies", action="store_true",
                        help="Export all companies, not just those with videos")
    parser.add_argument("--approved-only", action="store_true",
                        help="Only include approved videos")
    parser.add_argument("--min-dr", type=float, help="Minimum Domain Rating filter")
    args = parser.parse_args()

    video_only = not args.all_companies
    export_leads(
        output_path=args.output,
        video_only=video_only,
        approved_only=args.approved_only,
        min_dr=args.min_dr,
    )


if __name__ == "__main__":
    main()
