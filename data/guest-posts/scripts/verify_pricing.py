#!/usr/bin/env python3
"""Verify the prices used in an article against current vendor pricing pages.

Workflow:
  1. Parse the article for `tool_id -> price_string` from the comparison table
     and from inline mentions in each H3 body.
  2. Push the list of pricing URLs to the AirOps Firecrawl scrape grid
     (Grid 61652, Table 79641) and ask the operator to trigger the workflow.
  3. Read the scraped markdown back and extract candidate prices.
  4. Diff: flag any article price not present in the scraped markdown.

The mapping `tool -> pricing_url` lives in tools_registry.json (sibling file).
Tools without a URL are skipped with a warning.

Usage:
  python3 verify_pricing.py <article.md>            # interactive grid mode
  python3 verify_pricing.py <article.md> --offline  # use cached scrape (cached/*.md)

The scrape-side integration uses the airops MCP. In headless mode (no MCP), pass
--offline plus a directory of pre-scraped markdown files named after each tool
slug (e.g. cached/synthesia.md, cached/hubspot.md).
"""
import argparse, json, re, sys
from pathlib import Path

REGISTRY = Path(__file__).parent / "tools_registry.json"

PRICE_PATTERN = re.compile(
    r"(?P<currency>[$£€])\s?(?P<amount>\d+(?:[,.]\d{2,3})?)\s?"
    r"(?:per|/|a)?\s?"
    r"(?P<unit>seat|user|agent|channel|placement|month|mo|year|annual)?",
    re.IGNORECASE,
)

H3 = re.compile(r"^###\s+(?:\d+\\?\.\s*)?(.+?)\s*$", re.MULTILINE)


def load_registry():
    if REGISTRY.exists():
        return json.loads(REGISTRY.read_text())
    return {}


def parse_article(md: str):
    """Return {tool_slug: {'table_price': str, 'body_prices': [str], 'section_text': str}}."""
    registry = load_registry()
    tools = {}

    # Parse comparison table
    for line in md.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 5:
            continue
        if not cells[0].isdigit():
            continue
        tool_name = cells[1].strip()
        slug = slugify(tool_name)
        tools.setdefault(slug, {"display_name": tool_name, "table_price": None, "body_prices": [], "section_text": ""})
        tools[slug]["table_price"] = cells[3]

    # Parse body sections
    sections = split_h3_sections(md)
    for title, body in sections:
        # try to match section title to a known tool name
        for slug, info in tools.items():
            display = info["display_name"].lower()
            if display in title.lower():
                tools[slug]["section_text"] = body
                tools[slug]["body_prices"] = extract_prices(body)
                break
    return tools


def split_h3_sections(md: str):
    matches = list(H3.finditer(md))
    out = []
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        out.append((title, md[start:end].strip()))
    return out


def extract_prices(text: str):
    return [m.group(0).strip() for m in PRICE_PATTERN.finditer(text)]


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def verify_against_scraped(article_tools: dict, scraped_dir: Path):
    """Compare each article price against scraped markdown for that tool."""
    report = []
    for slug, info in article_tools.items():
        cache_file = scraped_dir / f"{slug}.md"
        if not cache_file.exists():
            report.append({"tool": slug, "status": "no_scrape", "table_price": info.get("table_price"),
                           "body_prices": info.get("body_prices", [])})
            continue
        scraped = cache_file.read_text().lower()
        article_prices = []
        if info.get("table_price"):
            article_prices.append(("table", info["table_price"]))
        for p in info.get("body_prices", []):
            article_prices.append(("body", p))

        flagged = []
        for source, price in article_prices:
            normalized = normalize_price(price)
            if normalized and normalized not in scraped:
                flagged.append({"source": source, "price": price, "normalized": normalized})

        report.append({
            "tool": slug,
            "status": "stale" if flagged else "ok",
            "table_price": info.get("table_price"),
            "body_prices": info.get("body_prices", []),
            "flagged": flagged,
        })
    return report


def normalize_price(price: str):
    """'$29 a month' -> '29'  (search for the numeric on the scraped page)."""
    m = re.search(r"(\d+(?:[.,]\d{2})?)", price)
    if not m:
        return None
    return m.group(1).replace(",", ".")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article", type=Path)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--scraped-dir", type=Path, default=Path("cached"))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    md = args.article.read_text()
    tools = parse_article(md)
    print(f"Detected {len(tools)} tools in article", file=sys.stderr)

    if not args.offline:
        print("\nNON-OFFLINE MODE: push pricing URLs to AirOps grid 61652 (table 79641),", file=sys.stderr)
        print("trigger Firecrawl, then re-run with --offline pointing at the saved scrape files.", file=sys.stderr)
        print("\nPricing URLs to scrape (one per tool):", file=sys.stderr)
        registry = load_registry()
        for slug in tools:
            url = registry.get(slug, {}).get("pricing_url", "<UNKNOWN — add to tools_registry.json>")
            print(f"  {slug:<30}  {url}", file=sys.stderr)
        sys.exit(2)

    report = verify_against_scraped(tools, args.scraped_dir)
    stale = [r for r in report if r["status"] == "stale"]

    if args.json:
        print(json.dumps({"article": str(args.article), "stale_count": len(stale), "report": report}, indent=2))
    else:
        print(f"{'STATUS':<10} {'TOOL':<30} TABLE        BODY")
        print("-" * 90)
        for r in report:
            tbl = (r.get("table_price") or "-")[:20]
            body = ", ".join(r.get("body_prices") or [])[:30]
            print(f"{r['status']:<10} {r['tool']:<30} {tbl:<12} {body}")
        if stale:
            print(f"\n{len(stale)} tools have stale prices:")
            for r in stale:
                print(f"  {r['tool']}")
                for f in r["flagged"]:
                    print(f"    {f['source']}: {f['price']!r} not found in scrape")
    sys.exit(1 if stale else 0)


if __name__ == "__main__":
    main()
