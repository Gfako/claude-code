#!/usr/bin/env python3
"""
pipeline.py — SaaS Video Outreach Pipeline Orchestrator

CLI entry point that runs individual steps or the full pipeline.

Usage:
    python3 pipeline.py discover-capterra [--category SLUG] [--limit N]
    python3 pipeline.py dedup
    python3 pipeline.py detect-video [--youtube-only] [--google-only] [--limit N]
    python3 pipeline.py ahrefs [--domains] [--force]
    python3 pipeline.py lusha [--dry-run] [--credits] [--limit N]
    python3 pipeline.py review [--port 8080]
    python3 pipeline.py export [--output PATH] [--approved-only] [--min-dr N]
    python3 pipeline.py stats
"""

import argparse
import json
import sys

from utils import load_config, log


def cmd_discover_capterra(args):
    from discover_capterra import run_capterra_discovery
    config = load_config()
    run_capterra_discovery(config, category_filter=args.category, limit=args.limit)


def cmd_dedup(args):
    from dedup import run_dedup
    run_dedup()


def cmd_detect_video(args):
    from detect_video import run_video_detection
    config = load_config()
    run_video_detection(config, youtube_only=args.youtube_only,
                        google_only=args.google_only, limit=args.limit)


def cmd_ahrefs(args):
    from ahrefs_enrich import run_ahrefs_enrichment, list_domains_needing_enrichment
    if args.domains:
        list_domains_needing_enrichment(force=args.force)
    else:
        run_ahrefs_enrichment(force=args.force)


def cmd_lusha(args):
    from lusha_enrich import enrich_with_lusha, lusha_check_credits
    config = load_config()
    api_key = config.get("lusha_api_key", "")

    if args.credits:
        if not api_key:
            log.error("No lusha_api_key configured.")
            return
        usage = lusha_check_credits(api_key)
        if usage:
            print(json.dumps(usage, indent=2))
        return

    if not api_key and not args.dry_run:
        log.error("No lusha_api_key configured. Set LUSHA_API_KEY in .env or use --dry-run")
        sys.exit(1)

    enrich_with_lusha(api_key, dry_run=args.dry_run, limit=args.limit)


def cmd_review(args):
    from review_server import main as review_main
    # Override sys.argv for the review server's argparse
    sys.argv = ["review_server.py", "--port", str(args.port)]
    review_main()


def cmd_export(args):
    from export import export_leads
    export_leads(
        output_path=args.output,
        video_only=not args.all_companies,
        approved_only=args.approved_only,
        min_dr=args.min_dr,
    )


def cmd_stats(args):
    import db
    stats = db.get_stats()

    print("\n" + "=" * 60)
    print("  SaaS Video Outreach — Pipeline Statistics")
    print("=" * 60)
    print(f"\n  Companies")
    print(f"    Total discovered:      {stats['total_companies']:>6,}")
    print(f"    Discovered (pending):  {stats['discovered']:>6,}")
    print(f"    Video checked:         {stats['video_checked']:>6,}")
    print(f"    Enriched:              {stats['enriched']:>6,}")
    print(f"\n  Video Detection")
    print(f"    With YouTube channel:  {stats['with_youtube']:>6,}")
    print(f"    With website videos:   {stats['with_website_videos']:>6,}")
    print(f"    With any video:        {stats['with_any_video']:>6,}")
    print(f"    Total videos found:    {stats['total_videos']:>6,}")
    print(f"    Videos pending review: {stats['videos_pending']:>6,}")
    print(f"    Videos approved:       {stats['videos_approved']:>6,}")
    print(f"\n  Enrichment")
    print(f"    Ahrefs enriched:       {stats['ahrefs_enriched']:>6,}")
    print(f"    Companies w/ contacts: {stats['companies_with_contacts']:>6,}")
    print(f"    Total contacts:        {stats['total_contacts']:>6,}")

    if stats.get("categories"):
        print(f"\n  Categories")
        for cat, cnt in stats["categories"].items():
            print(f"    {cat or 'Unknown':<30} {cnt:>6,}")

    if stats.get("sources"):
        print(f"\n  Discovery Sources")
        for src, cnt in stats["sources"].items():
            print(f"    {src:<30} {cnt:>6,}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="SaaS Video Outreach Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Steps (in order):
  discover-capterra  Scrape Capterra via Apify
  dedup              Cross-source deduplication
  detect-video       YouTube API + Google Video search
  ahrefs             Ahrefs SEO enrichment
  lusha              Lusha contact enrichment
  review             Web UI for video review
  export             Export leads to CSV
  stats              Show pipeline statistics
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="Pipeline step to run")

    # discover-capterra
    p = subparsers.add_parser("discover-capterra", help="Capterra discovery via Apify")
    p.add_argument("--category", type=str, help="Single category slug")
    p.add_argument("--limit", type=int, help="Max listings per category")

    # dedup
    subparsers.add_parser("dedup", help="Cross-source deduplication")

    # detect-video
    p = subparsers.add_parser("detect-video", help="Video detection (YouTube + Google)")
    p.add_argument("--youtube-only", action="store_true")
    p.add_argument("--google-only", action="store_true")
    p.add_argument("--limit", type=int, help="Max companies to process")

    # ahrefs
    p = subparsers.add_parser("ahrefs", help="Ahrefs SEO enrichment")
    p.add_argument("--force", action="store_true")
    p.add_argument("--domains", action="store_true", help="List domains for MCP enrichment")

    # lusha
    p = subparsers.add_parser("lusha", help="Lusha contact enrichment")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--credits", action="store_true")
    p.add_argument("--limit", type=int, help="Max companies to enrich")

    # review
    p = subparsers.add_parser("review", help="Web UI for video review")
    p.add_argument("--port", type=int, default=8080)

    # export
    p = subparsers.add_parser("export", help="Export to CSV")
    p.add_argument("--output", "-o", type=str)
    p.add_argument("--approved-only", action="store_true")
    p.add_argument("--all-companies", action="store_true")
    p.add_argument("--min-dr", type=float)

    # stats
    subparsers.add_parser("stats", help="Show pipeline statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "discover-capterra": cmd_discover_capterra,
        "dedup": cmd_dedup,
        "detect-video": cmd_detect_video,
        "ahrefs": cmd_ahrefs,
        "lusha": cmd_lusha,
        "review": cmd_review,
        "export": cmd_export,
        "stats": cmd_stats,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
