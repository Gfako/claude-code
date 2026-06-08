#!/usr/bin/env python3
"""
Scrape all qualified prospects and extract structured data for link outreach analysis.
Uses Firecrawl's JSON extraction to pull author, topic, and content signals from each page.
Then heuristically identifies pages where a video translator link would fit.

Usage: python3 scrape_and_analyze.py
"""

import json
import time
import os
import sys
from firecrawl import FirecrawlApp

# Config
FIRECRAWL_API_KEY = open("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/firecrawl-api-key.txt").read().strip()
PROJECT_ROOT = "/Users/george.fakorellis/Desktop/SEO Custom Projects/link-outreach"
CAMPAIGN_DIR = f"{PROJECT_ROOT}/campaigns/niche-edits/2026-04-08-video-translator"
QUALIFIED_PATH = f"{CAMPAIGN_DIR}/qualified.json"
ANALYZED_PATH = f"{CAMPAIGN_DIR}/analyzed.json"
SCRAPED_PATH = f"{CAMPAIGN_DIR}/scraped_raw.json"

TARGET_URL = "https://www.synthesia.io/features/video-translator"
TARGET_TOPIC = "AI video translator — translates videos in 130+ languages with voice cloning and lip sync"

# Keywords that signal a section where a video translator link could fit
FIT_KEYWORDS = [
    "translate video", "video translation", "video localization", "localize video",
    "dub", "dubbing", "ai dubbing", "voice cloning", "lip sync", "lip-sync",
    "multilingual video", "multiple languages", "translate training",
    "translate content", "localize content", "content localization",
    "multilingual training", "global audience", "international audience",
    "multilingual onboarding", "global workforce", "non-english",
    "translate webinar", "repurpose video", "subtitle", "caption",
    "localization tool", "translation tool", "localize media",
    "video accessibility", "multilingual content", "global teams",
    "translate course", "localize training", "multilingual learning",
]

# Keywords that suggest this is a product/competitor page (not a good target)
COMPETITOR_KEYWORDS = [
    "synthesia", "heygen", "veed.io", "colossyan", "elai.io",
    "d-id", "deepbrain", "invideo", "runway", "luma ai", "kling"
]

def init_firecrawl():
    return FirecrawlApp(api_key=FIRECRAWL_API_KEY)

def load_qualified():
    with open(QUALIFIED_PATH) as f:
        return json.load(f)

def load_already_analyzed():
    """Load already analyzed prospects to skip them."""
    if os.path.exists(ANALYZED_PATH):
        with open(ANALYZED_PATH) as f:
            data = json.load(f)
            return {p["url"] for p in data.get("prospects", [])}
    return set()

def load_scraped_raw():
    """Load already scraped raw data to avoid re-scraping."""
    if os.path.exists(SCRAPED_PATH):
        with open(SCRAPED_PATH) as f:
            return json.load(f)
    return {}

def save_scraped_raw(scraped):
    with open(SCRAPED_PATH, "w") as f:
        json.dump(scraped, f, indent=2)

def scrape_page(app, url):
    """Scrape a single page with Firecrawl, return markdown content."""
    try:
        result = app.scrape(url, formats=["markdown"], only_main_content=True)
        if result and hasattr(result, "markdown") and result.markdown:
            return result.markdown[:8000]  # Truncate to save memory
        return None
    except Exception as e:
        print(f"  ERROR scraping {url}: {e}")
        return None

def analyze_content(url, domain, dr, title, markdown):
    """Analyze scraped content heuristically for fit."""
    if not markdown:
        return {
            "url": url, "domain": domain, "dr": dr,
            "is_article": False, "author_name": "", "author_title": "",
            "article_topic": title, "section_quote": "",
            "link_placement_rationale": "Scrape failed — no content retrieved.",
            "suggested_anchor_text": "", "fit_strength": "scrape_failed"
        }

    content_lower = markdown.lower()

    # Check if it's likely an article (has enough text content)
    word_count = len(markdown.split())
    is_article = word_count > 300

    # Check for competitor mentions (would make it a bad target)
    mentions_competitor = any(kw in content_lower for kw in COMPETITOR_KEYWORDS)
    mentions_synthesia = "synthesia" in content_lower

    # Find fit keywords and their surrounding context
    fit_matches = []
    for kw in FIT_KEYWORDS:
        if kw in content_lower:
            fit_matches.append(kw)

    # Extract a quote around the best fit keyword
    section_quote = ""
    if fit_matches:
        # Find the first strong match and extract surrounding text
        best_match = fit_matches[0]
        idx = content_lower.find(best_match)
        if idx >= 0:
            start = max(0, idx - 100)
            end = min(len(markdown), idx + len(best_match) + 150)
            raw_quote = markdown[start:end].strip()
            # Clean up the quote
            section_quote = raw_quote.replace("\n", " ").strip()
            if len(section_quote) > 250:
                section_quote = section_quote[:250] + "..."

    # Extract author from common patterns
    author_name = ""
    author_title_text = ""

    # Look for common author patterns in first 2000 chars
    header = markdown[:2000]
    author_patterns = [
        "Written by", "By ", "Author:", "author:", "Published by",
        "Written By:", "Posted by"
    ]
    for pattern in author_patterns:
        if pattern in header:
            idx = header.find(pattern)
            after = header[idx + len(pattern):idx + len(pattern) + 100]
            # Extract name (first line after pattern)
            name_line = after.strip().split("\n")[0].strip()
            # Clean markdown artifacts
            name_line = name_line.replace("[", "").replace("]", "").replace("*", "")
            name_line = name_line.split("(")[0].strip()  # Remove link URLs
            if 2 < len(name_line) < 50:
                author_name = name_line
                break

    # Determine fit strength
    num_fit_keywords = len(fit_matches)

    if not is_article:
        fit_strength = "not_article"
        rationale = "Not an article — too short or not editorial content."
    elif mentions_synthesia:
        fit_strength = "already_mentioned"
        rationale = f"Synthesia is already mentioned in this article. {num_fit_keywords} fit keywords found."
    elif mentions_competitor and num_fit_keywords < 3:
        fit_strength = "competitor_focused"
        rationale = "Article mentions competitors and has limited fit for video translator link."
    elif num_fit_keywords >= 5:
        fit_strength = "strong"
        rationale = f"Strong fit — {num_fit_keywords} relevant keywords found: {', '.join(fit_matches[:5])}. Content discusses topics where a video translator link adds value."
    elif num_fit_keywords >= 3:
        fit_strength = "medium"
        rationale = f"Medium fit — {num_fit_keywords} relevant keywords found: {', '.join(fit_matches[:5])}."
    elif num_fit_keywords >= 1:
        fit_strength = "weak"
        rationale = f"Weak fit — only {num_fit_keywords} relevant keyword(s): {', '.join(fit_matches)}."
    else:
        fit_strength = "no_fit"
        rationale = "No relevant keywords found — article topic doesn't relate to video translation use cases."

    # Determine suggested anchor text based on content
    anchor = ""
    if fit_strength in ("strong", "medium"):
        if "translate video" in content_lower or "video translation" in content_lower:
            anchor = "AI video translator"
        elif "multilingual training" in content_lower or "translate training" in content_lower:
            anchor = "translate training videos into multiple languages"
        elif "localize video" in content_lower or "video localization" in content_lower:
            anchor = "AI video localization tool"
        elif "multilingual video" in content_lower:
            anchor = "multilingual video translation"
        elif "global audience" in content_lower or "international audience" in content_lower:
            anchor = "AI video translator for global audiences"
        elif "dubbing" in content_lower:
            anchor = "AI video dubbing and translation"
        else:
            anchor = "AI video translator"

    # Extract article topic from title or first heading
    topic = title if title else ""
    if not topic and markdown:
        first_line = markdown.strip().split("\n")[0]
        if first_line.startswith("#"):
            topic = first_line.lstrip("#").strip()

    return {
        "url": url,
        "domain": domain,
        "dr": dr,
        "is_article": is_article,
        "author_name": author_name,
        "author_title": author_title_text,
        "article_topic": topic[:200],
        "section_quote": section_quote,
        "link_placement_rationale": rationale,
        "suggested_anchor_text": anchor,
        "fit_strength": fit_strength,
        "fit_keyword_count": num_fit_keywords,
        "fit_keywords": fit_matches[:10],
        "word_count": word_count
    }


def main():
    print("=" * 60)
    print("LINK OUTREACH: Scrape & Analyze Pipeline")
    print("=" * 60)

    # Load data
    qualified = load_qualified()
    already_analyzed_urls = load_already_analyzed()
    scraped_raw = load_scraped_raw()

    prospects = qualified["prospects"]
    print(f"Total qualified prospects: {len(prospects)}")
    print(f"Already analyzed: {len(already_analyzed_urls)}")

    # Filter to only unanalyzed prospects
    to_process = [p for p in prospects if p["url"] not in already_analyzed_urls]
    print(f"To process: {len(to_process)}")

    if not to_process:
        print("Nothing to process. All prospects already analyzed.")
        return

    # Initialize Firecrawl
    app = init_firecrawl()

    # Process each prospect
    results = []
    errors = 0

    for i, prospect in enumerate(to_process):
        url = prospect["url"]
        domain = prospect["domain"]
        dr = prospect["dr"]
        title = prospect.get("title", "")

        print(f"\n[{i+1}/{len(to_process)}] DR {dr} | {domain}")
        print(f"  URL: {url[:80]}...")

        # Check if already scraped
        if url in scraped_raw:
            print(f"  Using cached scrape")
            markdown = scraped_raw[url]
        else:
            # Scrape
            markdown = scrape_page(app, url)
            if markdown:
                scraped_raw[url] = markdown
                print(f"  Scraped: {len(markdown)} chars")
            else:
                scraped_raw[url] = ""
                print(f"  Scrape FAILED")
                errors += 1

            # Save raw scrapes incrementally (every 10 pages)
            if (i + 1) % 10 == 0:
                save_scraped_raw(scraped_raw)
                print(f"  [Saved raw scrapes checkpoint]")

            # Rate limiting: small pause between scrapes
            time.sleep(0.5)

        # Analyze
        analysis = analyze_content(url, domain, dr, title, markdown)
        results.append(analysis)

        fit = analysis["fit_strength"]
        kw_count = analysis.get("fit_keyword_count", 0)
        author = analysis.get("author_name", "")[:20]
        print(f"  Fit: {fit} ({kw_count} keywords) | Author: {author or 'unknown'}")

        # Save results incrementally (every 20 pages)
        if (i + 1) % 20 == 0:
            save_results(results, already_analyzed_urls)
            print(f"\n  === CHECKPOINT: {i+1}/{len(to_process)} processed ===")

    # Final save
    save_scraped_raw(scraped_raw)
    save_results(results, already_analyzed_urls)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    strengths = {}
    for r in results:
        s = r["fit_strength"]
        strengths[s] = strengths.get(s, 0) + 1

    for s, count in sorted(strengths.items(), key=lambda x: -x[1]):
        print(f"  {s}: {count}")

    print(f"\nTotal processed: {len(results)}")
    print(f"Scrape errors: {errors}")
    print(f"\nStrong fits:")
    for r in results:
        if r["fit_strength"] == "strong":
            print(f"  DR {r['dr']} | {r['domain']} | {r['article_topic'][:60]}")


def save_results(new_results, already_analyzed_urls):
    """Merge new results with existing analyzed.json."""
    if os.path.exists(ANALYZED_PATH):
        with open(ANALYZED_PATH) as f:
            existing = json.load(f)
    else:
        existing = {"analyzed_count": 0, "prospects": []}

    # Add new results (avoid duplicates)
    existing_urls = {p["url"] for p in existing["prospects"]}
    for r in new_results:
        if r["url"] not in existing_urls:
            existing["prospects"].append(r)
            existing_urls.add(r["url"])

    existing["analyzed_count"] = len(existing["prospects"])

    with open(ANALYZED_PATH, "w") as f:
        json.dump(existing, f, indent=2)


if __name__ == "__main__":
    main()
