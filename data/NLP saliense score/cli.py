#!/usr/bin/env python3
"""CLI entry point for Entity Salience Analysis tool."""

import argparse
import json
import logging
import sys
import time

from utils import load_config, setup_logging, clean_domain
from db import init_db, get_db, start_run, complete_run, clear_domain, page_count


def cmd_crawl(args, config):
    """Crawl a domain to discover and extract page text."""
    from crawl import crawl_domain

    results = crawl_domain(
        domain=args.domain,
        config=config,
        subfolder=args.subfolder,
        limit=args.limit,
        use_sitemap=args.sitemap,
    )
    print(f"\nCrawled {len(results)} pages for {args.domain}")
    return results


def cmd_analyze(args, config):
    """Run Google NLP entity analysis on crawled pages."""
    from analyze import analyze_domain, analyze_from_db

    if hasattr(args, "_page_texts") and args._page_texts:
        # Called from run command with page texts in memory
        total = analyze_domain(args.domain, args._page_texts, config)
    else:
        # Re-analyze from DB (fetch text again for unanalyzed pages)
        total = analyze_from_db(args.domain, config)

    print(f"\nExtracted {total} entities for {args.domain}")
    return total


def cmd_cluster(args, config):
    """Run all 3 clustering methods."""
    from cluster import run_all_clustering

    results = run_all_clustering(args.domain, config)
    for method in ["cooccurrence", "kmeans", "hierarchical"]:
        if method in results:
            print(f"  {method}: {len(results[method])} clusters")
    return results


def cmd_compare(args, config):
    """Compare entity salience across domains."""
    from compare import compare_domains

    competitors = _parse_competitors(args.competitors)
    if not competitors:
        print("No competitors specified. Use --competitors 'domain1.com,domain2.com'")
        return None

    comparison = compare_domains(args.domain, competitors, config)
    stats = comparison["stats"]
    print(f"\nComparison: {args.domain} vs {', '.join(competitors)}")
    print(f"  Total unique entities: {stats['total_unique_entities']}")
    print(f"  Entity gaps: {stats['gap_count']}")
    print(f"  Shared entities: {stats['overlap_count']}")
    print(f"  Unique to {args.domain}: {stats['unique_count']}")
    return comparison


def cmd_report(args, config):
    """Generate interactive HTML report."""
    from visualize import build_report

    comparison = getattr(args, "_comparison", None)
    linkage_info = getattr(args, "_linkage_info", None)

    filepath = build_report(
        args.domain, config,
        comparison=comparison,
        linkage_info=linkage_info,
    )
    print(f"\nReport saved to: {filepath}")
    return filepath


def cmd_export(args, config):
    """Export analysis results as CSV files."""
    from export import export_all

    comparison = getattr(args, "_comparison", None)
    files = export_all(args.domain, config, comparison=comparison)
    print(f"\nExported {len(files)} CSV files:")
    for f in files:
        print(f"  {f}")
    return files


def cmd_run(args, config):
    """Full pipeline: crawl → analyze → cluster → [compare] → report → export."""
    log = logging.getLogger("salience")
    domain = clean_domain(args.domain)
    competitors = _parse_competitors(args.competitors) if args.competitors else []

    # Force mode: clear existing data
    if args.force:
        log.info(f"Force mode: clearing existing data for {domain}")
        with get_db() as conn:
            clear_domain(conn, domain)
            for comp in competitors:
                clear_domain(conn, clean_domain(comp))

    # Start run record
    with get_db() as conn:
        run_id = start_run(conn, domain, competitors, args.subfolder)

    start_time = time.time()

    # Step 1: Crawl primary domain
    print(f"\n{'='*60}")
    print(f"  STEP 1/6: Crawling {domain}")
    print(f"{'='*60}")
    page_texts = cmd_crawl(args, config)

    # Step 2: Analyze primary domain
    print(f"\n{'='*60}")
    print(f"  STEP 2/6: Analyzing entities for {domain}")
    print(f"{'='*60}")
    args._page_texts = page_texts
    cmd_analyze(args, config)

    # Step 3: Crawl + analyze competitors
    comparison = None
    if competitors:
        print(f"\n{'='*60}")
        print(f"  STEP 3/6: Processing {len(competitors)} competitors")
        print(f"{'='*60}")
        from crawl import crawl_domain
        from analyze import analyze_domain

        for comp in competitors:
            print(f"\n  --- {comp} ---")
            comp_texts = crawl_domain(
                domain=comp, config=config,
                subfolder=args.subfolder,
                limit=args.limit,
                use_sitemap=args.sitemap,
            )
            analyze_domain(comp, comp_texts, config)

        # Step 4: Compare
        print(f"\n{'='*60}")
        print(f"  STEP 4/6: Comparing entities across domains")
        print(f"{'='*60}")
        from compare import compare_domains
        comparison = compare_domains(domain, competitors, config)
        stats = comparison["stats"]
        print(f"  Gaps: {stats['gap_count']} | Shared: {stats['overlap_count']} | Unique: {stats['unique_count']}")
    else:
        print(f"\n  STEP 3-4: Skipped (no competitors specified)")

    # Step 5: Cluster
    print(f"\n{'='*60}")
    print(f"  STEP 5/6: Clustering pages")
    print(f"{'='*60}")
    cluster_results = cmd_cluster(args, config)
    linkage_info = cluster_results.get("linkage_info")

    # Step 6: Report + Export
    print(f"\n{'='*60}")
    print(f"  STEP 6/6: Generating report and exports")
    print(f"{'='*60}")
    args._comparison = comparison
    args._linkage_info = linkage_info
    report_path = cmd_report(args, config)
    csv_files = cmd_export(args, config)

    # Complete run record
    with get_db() as conn:
        total_pages = page_count(conn, domain)
        complete_run(conn, run_id, total_pages)

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"  COMPLETE — {elapsed:.1f}s")
    print(f"{'='*60}")
    print(f"  Domain: {domain}")
    if competitors:
        print(f"  Competitors: {', '.join(competitors)}")
    print(f"  Report: {report_path}")
    print(f"  CSVs: {len(csv_files)} files")
    print(f"{'='*60}\n")


def cmd_stats(args, config):
    """Show database stats."""
    with get_db() as conn:
        domains = conn.execute(
            "SELECT DISTINCT domain FROM pages"
        ).fetchall()

        print("\nDatabase Stats:")
        print("-" * 50)
        for d in domains:
            domain = d["domain"]
            pages = page_count(conn, domain)
            analyzed = page_count(conn, domain, "analyzed")
            ents = conn.execute(
                "SELECT COUNT(DISTINCT entity_name) as c FROM entities WHERE domain=?",
                (domain,),
            ).fetchone()["c"]
            clusters = conn.execute(
                "SELECT method, COUNT(*) as c FROM clusters WHERE domain=? GROUP BY method",
                (domain,),
            ).fetchall()

            print(f"\n  {domain}")
            print(f"    Pages: {pages} ({analyzed} analyzed)")
            print(f"    Entities: {ents}")
            for cl in clusters:
                print(f"    Clusters ({cl['method']}): {cl['c']}")

        if not domains:
            print("  No data yet. Run: python3 cli.py run --domain <domain>")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_competitors(comp_str):
    """Parse comma-separated competitor domains."""
    if not comp_str:
        return []
    return [clean_domain(d.strip()) for d in comp_str.split(",") if d.strip()]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Entity Salience Analysis — Google NLP powered domain analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 cli.py run --domain synthesia.io --competitors "loom.com,descript.com"
  python3 cli.py run --domain synthesia.io --subfolder /blog/ --limit 50
  python3 cli.py crawl --domain synthesia.io --sitemap
  python3 cli.py stats
        """,
    )

    # Global args
    parser.add_argument("--config", help="Path to config.yaml")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- crawl ---
    p_crawl = subparsers.add_parser("crawl", help="Crawl a domain")
    p_crawl.add_argument("--domain", "-d", required=True)
    p_crawl.add_argument("--subfolder", "-s", help="Limit to subfolder (e.g., /blog/)")
    p_crawl.add_argument("--limit", "-l", type=int, help="Max pages")
    p_crawl.add_argument("--sitemap", action="store_true", help="Use sitemap instead of Screaming Frog")

    # --- analyze ---
    p_analyze = subparsers.add_parser("analyze", help="Run NLP entity analysis")
    p_analyze.add_argument("--domain", "-d", required=True)

    # --- cluster ---
    p_cluster = subparsers.add_parser("cluster", help="Cluster pages by entities")
    p_cluster.add_argument("--domain", "-d", required=True)

    # --- compare ---
    p_compare = subparsers.add_parser("compare", help="Compare against competitors")
    p_compare.add_argument("--domain", "-d", required=True)
    p_compare.add_argument("--competitors", "-c", required=True, help="Comma-separated domains")

    # --- report ---
    p_report = subparsers.add_parser("report", help="Generate HTML report")
    p_report.add_argument("--domain", "-d", required=True)

    # --- export ---
    p_export = subparsers.add_parser("export", help="Export CSV files")
    p_export.add_argument("--domain", "-d", required=True)

    # --- run ---
    p_run = subparsers.add_parser("run", help="Full pipeline (one-click)")
    p_run.add_argument("--domain", "-d", required=True)
    p_run.add_argument("--competitors", "-c", help="Comma-separated domains")
    p_run.add_argument("--subfolder", "-s", help="Limit to subfolder")
    p_run.add_argument("--limit", "-l", type=int, help="Max pages per domain")
    p_run.add_argument("--sitemap", action="store_true", help="Use sitemap instead of Screaming Frog")
    p_run.add_argument("--force", "-f", action="store_true", help="Force re-analysis (clear cache)")

    # --- stats ---
    subparsers.add_parser("stats", help="Show database stats")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Setup
    log_level = logging.DEBUG if args.verbose else logging.INFO
    log = setup_logging(log_level)
    config = load_config(args.config)
    init_db()

    # Dispatch
    commands = {
        "crawl": cmd_crawl,
        "analyze": cmd_analyze,
        "cluster": cmd_cluster,
        "compare": cmd_compare,
        "report": cmd_report,
        "export": cmd_export,
        "run": cmd_run,
        "stats": cmd_stats,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args, config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
