#!/usr/bin/env python3
"""
pipeline.py — YouTube Outreach Pipeline Orchestrator

CLI entry point that runs individual steps or the full pipeline.

Usage:
    python3 pipeline.py discover [--country ES] [--keyword "tutorial"]
    python3 pipeline.py enrich [--dubbed-only]
    python3 pipeline.py ahrefs [--force] [--domains]
    python3 pipeline.py lusha [--dry-run]
    python3 pipeline.py review [--list] [--approve-all] [--approve VIDEO_ID]
    python3 pipeline.py dub --video VIDEO_ID --target-lang es
    python3 pipeline.py export [--dubbed-only] [--zoominfo]
    python3 pipeline.py stats
    python3 pipeline.py all [--country ES]   # Run discover → enrich → review prompt
"""

import argparse
import sys

from utils import load_config, log


def cmd_discover(args):
    from discover import discover_channels, check_dubbing_only, print_stats
    config = load_config()

    if args.stats:
        print_stats()
        return

    if args.check_only:
        check_dubbing_only(config)
        return

    total_new, total_dubbed = discover_channels(
        config,
        country_filter=args.country,
        keyword_filter=args.keyword,
        language_filter=args.language,
    )
    log.info("Discovery complete. New: %d, Dubbed: %d", total_new, total_dubbed)
    print_stats()


def cmd_enrich(args):
    from enrich import run_enrichment
    run_enrichment(dubbed_only=args.dubbed_only)


def cmd_ahrefs(args):
    from ahrefs_enrich import run_ahrefs_enrichment, list_domains_needing_enrichment
    if args.domains:
        list_domains_needing_enrichment()
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
        import json
        usage = lusha_check_credits(api_key)
        if usage:
            print(json.dumps(usage, indent=2))
        return

    if not api_key and not args.dry_run:
        log.error("No lusha_api_key configured. Set LUSHA_API_KEY in .env or use --dry-run")
        sys.exit(1)

    enrich_with_lusha(api_key, dry_run=args.dry_run)


def cmd_review(args):
    from review import (
        interactive_review, list_pending, list_all,
        approve_all, approve_video, reject_video, select_video,
    )

    if args.list:
        list_pending()
    elif args.list_all:
        list_all()
    elif args.approve_all:
        approve_all()
    elif args.approve:
        approve_video(args.approve)
    elif args.reject:
        reject_video(args.reject)
    elif args.select:
        select_video(args.select)
    else:
        interactive_review()


def cmd_dub(args):
    from dub import dub_video, pick_best_video, list_jobs, check_dubbing_status
    config = load_config()

    if args.list_jobs:
        list_jobs()
        return

    if args.status:
        import json
        data = check_dubbing_status(config["synthesia_api_key"], args.status)
        if data:
            print(json.dumps(data, indent=2))
        return

    if args.no_lipsync:
        config["synthesia"]["lipsync_enabled"] = False

    video_id = args.video
    channel_id = args.channel

    if channel_id and not video_id:
        video_id = pick_best_video(channel_id)
        if not video_id:
            log.error("Could not auto-pick a video.")
            sys.exit(1)

    if not video_id:
        log.error("Provide --video VIDEO_ID or --channel CHANNEL_ID")
        sys.exit(1)

    dub_video(video_id, args.target_lang, config, channel_id=channel_id, max_duration=getattr(args, 'duration', None))


def cmd_export(args):
    from export import export_leads, export_for_zoominfo
    if args.zoominfo:
        export_for_zoominfo(output_path=args.output)
    else:
        export_leads(output_path=args.output, dubbed_only=args.dubbed_only)


def cmd_stats(args):
    from discover import print_stats
    print_stats()


def cmd_all(args):
    """Run discover -> enrich -> prompt for review."""
    config = load_config()

    # Step 1: Discover
    log.info("=" * 60)
    log.info("  STEP 1: Discovery")
    log.info("=" * 60)
    from discover import discover_channels
    total_new, total_dubbed = discover_channels(
        config,
        country_filter=args.country,
        keyword_filter=args.keyword,
        language_filter=args.language,
    )
    log.info("Discovery done. New: %d, Dubbed: %d", total_new, total_dubbed)

    # Step 2: Enrich
    log.info("=" * 60)
    log.info("  STEP 2: Enrichment")
    log.info("=" * 60)
    from enrich import run_enrichment
    run_enrichment(dubbed_only=True)

    # Step 3: Prompt for Ahrefs (MCP)
    log.info("=" * 60)
    log.info("  STEP 3: Ahrefs (needs MCP)")
    log.info("=" * 60)
    from ahrefs_enrich import list_domains_needing_enrichment
    list_domains_needing_enrichment()
    log.info("Ask Claude: 'Run Ahrefs enrichment on these domains'")

    # Step 4: Prompt for review
    log.info("=" * 60)
    log.info("  STEP 4: Review")
    log.info("=" * 60)
    log.info("Run: python3 pipeline.py review")

    # Show stats
    from discover import print_stats
    print_stats()


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Outreach Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Steps (in order):
  discover   Find channels via YouTube API, detect dubbing
  enrich     Scrape About pages for contacts
  ahrefs     Enrich with Ahrefs SEO metrics
  lusha      Enrich with Lusha emails
  review     Approve/reject videos for dubbing
  dub        Dub approved videos via Synthesia
  export     Export leads to CSV
  stats      Show pipeline statistics
  all        Run discover + enrich + prompt for next steps
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="Pipeline step to run")

    # discover
    p = subparsers.add_parser("discover", help="Channel discovery + dubbing detection")
    p.add_argument("--stats", action="store_true")
    p.add_argument("--check-only", action="store_true")
    p.add_argument("--country", type=str)
    p.add_argument("--keyword", type=str)
    p.add_argument("--language", type=str)

    # enrich
    p = subparsers.add_parser("enrich", help="YouTube About page scraping")
    p.add_argument("--dubbed-only", action="store_true")

    # ahrefs
    p = subparsers.add_parser("ahrefs", help="Ahrefs SEO enrichment")
    p.add_argument("--force", action="store_true")
    p.add_argument("--domains", action="store_true")

    # lusha
    p = subparsers.add_parser("lusha", help="Lusha email enrichment")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--credits", action="store_true")

    # review
    p = subparsers.add_parser("review", help="Video review workflow")
    p.add_argument("--list", action="store_true")
    p.add_argument("--list-all", action="store_true")
    p.add_argument("--approve-all", action="store_true")
    p.add_argument("--approve", type=str, metavar="VIDEO_ID")
    p.add_argument("--reject", type=str, metavar="VIDEO_ID")
    p.add_argument("--select", type=str, metavar="VIDEO_ID")

    # dub
    p = subparsers.add_parser("dub", help="Synthesia video dubbing")
    p.add_argument("--video", type=str)
    p.add_argument("--channel", type=str)
    p.add_argument("--target-lang", type=str, default="en")
    p.add_argument("--duration", type=int, help="Only dub first N seconds")
    p.add_argument("--no-lipsync", action="store_true")
    p.add_argument("--status", type=str)
    p.add_argument("--list-jobs", action="store_true")

    # export
    p = subparsers.add_parser("export", help="Export to CSV")
    p.add_argument("--output", "-o", type=str)
    p.add_argument("--zoominfo", action="store_true")
    p.add_argument("--dubbed-only", action="store_true")

    # stats
    subparsers.add_parser("stats", help="Show pipeline statistics")

    # all
    p = subparsers.add_parser("all", help="Run full pipeline (discover + enrich + review prompt)")
    p.add_argument("--country", type=str)
    p.add_argument("--keyword", type=str)
    p.add_argument("--language", type=str)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "discover": cmd_discover,
        "enrich": cmd_enrich,
        "ahrefs": cmd_ahrefs,
        "lusha": cmd_lusha,
        "review": cmd_review,
        "dub": cmd_dub,
        "export": cmd_export,
        "stats": cmd_stats,
        "all": cmd_all,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
