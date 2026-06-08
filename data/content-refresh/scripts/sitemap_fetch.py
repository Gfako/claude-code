#!/usr/bin/env python3
"""Fetch sitemap and filter URLs to blog + alternatives sections."""

import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config.json"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def fetch_sitemap(url: str) -> str:
    """Use curl to avoid Python SSL cert bundle issues on macOS."""
    result = subprocess.run(
        ["curl", "-sSL", "--max-time", "30", "-A", "content-refresh-bot/1.0", url],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def parse_sitemap(xml_str: str) -> list[dict]:
    root = ET.fromstring(xml_str)
    entries = []
    for url_el in root.findall("sm:url", NS):
        loc_el = url_el.find("sm:loc", NS)
        lastmod_el = url_el.find("sm:lastmod", NS)
        if loc_el is None or loc_el.text is None:
            continue
        entries.append({
            "url": loc_el.text.strip(),
            "lastmod": lastmod_el.text.strip() if lastmod_el is not None and lastmod_el.text else None,
        })
    return entries


def classify(url: str, patterns: dict[str, str]) -> str | None:
    for section, pattern in patterns.items():
        if re.match(pattern, url):
            return section
    return None


def main():
    cfg = load_config()
    xml_str = fetch_sitemap(cfg["sitemap_url"])
    entries = parse_sitemap(xml_str)

    filtered = []
    for e in entries:
        section = classify(e["url"], cfg["url_patterns"])
        if section is not None:
            filtered.append({**e, "section": section})

    counts = {}
    for e in filtered:
        counts[e["section"]] = counts.get(e["section"], 0) + 1

    output = {
        "total_in_sitemap": len(entries),
        "filtered_count": len(filtered),
        "counts_by_section": counts,
        "urls": filtered,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
