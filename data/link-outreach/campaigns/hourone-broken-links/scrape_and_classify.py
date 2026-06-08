#!/usr/bin/env python3
"""
Scrape all HourOne broken link prospects to:
1. Check if the page mentions/links to Synthesia (exclude from outreach)
2. Classify page type: Listicle, Article, Marketplace/Directory, Other
"""

import json
import csv
import time
import re
import sys
from firecrawl import FirecrawlApp

FIRECRAWL_API_KEY = open("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/firecrawl-api-key.txt").read().strip()
PROJECT_ROOT = "/Users/george.fakorellis/Desktop/SEO Custom Projects/link-outreach"
CAMPAIGN_DIR = f"{PROJECT_ROOT}/campaigns/hourone-broken-links"
PROSPECTS_CSV = f"{CAMPAIGN_DIR}/outreach-prospects.csv"
OUTPUT_PATH = f"{CAMPAIGN_DIR}/scraped-classifications.json"
PROGRESS_PATH = f"{CAMPAIGN_DIR}/scrape-progress.json"

# Synthesia detection patterns
SYNTHESIA_PATTERNS = [
    r'synthesia\.io',
    r'synthesia\b',
]

# Listicle signals
LISTICLE_SIGNALS = [
    r'\d+\s+best\b', r'top\s+\d+', r'\d+\s+alternatives',
    r'best\s+\w+\s+tools', r'best\s+\w+\s+software', r'best\s+\w+\s+generators',
    r'vs\b.*vs\b', r'compared', r'comparison',
    r'alternatives to', r'tools for', r'software for',
]

# Directory/marketplace signals
DIRECTORY_SIGNALS = [
    r'pricing|features|rating|reviews|free trial|sign up',
    r'visit website|official site|go to',
    r'category.*tool|tool.*category',
    r'similar (tools|apps|software)',
]

def init_firecrawl():
    return FirecrawlApp(api_key=FIRECRAWL_API_KEY)

def load_prospects():
    prospects = []
    with open(PROSPECTS_CSV) as f:
        reader = csv.DictReader(f)
        for row in reader:
            prospects.append({
                'domain': row['Domain'],
                'url': row['Best Page URL'],
                'dr': row['DR'],
                'total_links': int(row['Total Links']),
                'track': row['Outreach Track'],
                'title': row['Best Page Title'],
            })
    return prospects

def load_progress():
    try:
        with open(PROGRESS_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_progress(progress):
    with open(PROGRESS_PATH, 'w') as f:
        json.dump(progress, f)

def check_synthesia(markdown):
    """Check if content mentions or links to Synthesia"""
    if not markdown:
        return False, []

    mentions = []
    text_lower = markdown.lower()

    for pattern in SYNTHESIA_PATTERNS:
        matches = re.findall(pattern, text_lower)
        if matches:
            mentions.extend(matches)

    # Check for actual links to synthesia.io
    has_link = bool(re.search(r'https?://[^\s\)]*synthesia\.io', text_lower))

    return bool(mentions), {
        'has_mention': bool(mentions),
        'has_link': has_link,
        'mention_count': len(mentions),
    }

def classify_page(markdown, url, title):
    """Classify page as Listicle, Article, Marketplace/Directory, or Other"""
    if not markdown:
        return 'Unknown (scrape failed)'

    text_lower = markdown.lower()
    title_lower = title.lower() if title else ''
    url_lower = url.lower()

    # Count headings (h2/h3) — listicles tend to have many
    h2_count = len(re.findall(r'^##\s', markdown, re.MULTILINE))
    h3_count = len(re.findall(r'^###\s', markdown, re.MULTILINE))

    # Count numbered items
    numbered_items = len(re.findall(r'^\d+[\.\)]\s', markdown, re.MULTILINE))

    # Word count
    word_count = len(markdown.split())

    # Marketplace/Directory signals
    directory_score = 0
    if any(x in url_lower for x in ['/tool/', '/tools/', '/app/', '/apps/', '/software/', '/alternative', '/product/']):
        directory_score += 3
    for pattern in DIRECTORY_SIGNALS:
        if re.search(pattern, text_lower):
            directory_score += 1
    if h2_count >= 5 and word_count < 1000:
        directory_score += 2  # Short pages with many headings = directory listings

    # Listicle signals
    listicle_score = 0
    for pattern in LISTICLE_SIGNALS:
        if re.search(pattern, title_lower) or re.search(pattern, text_lower[:500]):
            listicle_score += 2
    if h2_count >= 5 and word_count > 1000:
        listicle_score += 2
    if numbered_items >= 5:
        listicle_score += 2
    if any(x in title_lower for x in ['best', 'top', 'alternative', 'vs', 'compared', 'review']):
        listicle_score += 3

    # Article signals
    article_score = 0
    if word_count > 800 and h2_count < 10:
        article_score += 2
    if any(x in url_lower for x in ['/blog/', '/article/', '/post/', '/news/', '/insights/']):
        article_score += 2
    if any(x in title_lower for x in ['how to', 'guide', 'what is', 'why', 'the future of']):
        article_score += 2

    # Classify
    if directory_score >= 4:
        return 'Marketplace/Directory'
    elif listicle_score >= 4:
        return 'Listicle/Review'
    elif article_score >= 3:
        return 'Article'
    elif listicle_score >= 2:
        return 'Listicle/Review'
    elif word_count > 500:
        return 'Article'
    elif word_count < 200:
        return 'Thin/Stub Page'
    else:
        return 'Other'

def main():
    app = init_firecrawl()
    prospects = load_prospects()
    progress = load_progress()

    results = []
    scraped = 0
    failed = 0
    synthesia_found = 0

    print(f"Loaded {len(prospects)} prospects")
    print(f"Already scraped: {len(progress)}")

    for i, p in enumerate(prospects):
        domain = p['domain']
        url = p['url']

        # Skip if already scraped
        if domain in progress:
            results.append(progress[domain])
            if progress[domain].get('synthesia', {}).get('has_mention'):
                synthesia_found += 1
            continue

        try:
            response = app.scrape(url, formats=["markdown"], only_main_content=True)
            markdown = response.markdown or '' if hasattr(response, 'markdown') else ''

            has_synthesia, synthesia_info = check_synthesia(markdown)
            page_type = classify_page(markdown, url, p['title'])

            result = {
                'domain': domain,
                'url': url,
                'dr': p['dr'],
                'total_links': p['total_links'],
                'track': p['track'],
                'title': p['title'],
                'page_type': page_type,
                'synthesia': synthesia_info,
                'word_count': len(markdown.split()),
                'scraped': True,
            }

            results.append(result)
            progress[domain] = result
            scraped += 1

            if has_synthesia:
                synthesia_found += 1
                print(f"  [{i+1}/{len(prospects)}] SYNTHESIA FOUND: {domain} ({page_type})")
            else:
                print(f"  [{i+1}/{len(prospects)}] OK: {domain} — {page_type}")

            # Save progress every 10 scrapes
            if scraped % 10 == 0:
                save_progress(progress)
                print(f"  --- Progress saved. Scraped: {scraped}, Failed: {failed}, Synthesia: {synthesia_found} ---")

            time.sleep(0.3)

        except Exception as e:
            failed += 1
            result = {
                'domain': domain,
                'url': url,
                'dr': p['dr'],
                'total_links': p['total_links'],
                'track': p['track'],
                'title': p['title'],
                'page_type': 'Unknown (scrape failed)',
                'synthesia': {'has_mention': False, 'has_link': False, 'mention_count': 0},
                'word_count': 0,
                'scraped': False,
                'error': str(e),
            }
            results.append(result)
            progress[domain] = result
            print(f"  [{i+1}/{len(prospects)}] FAILED: {domain} — {e}")
            time.sleep(0.5)

    # Final save
    save_progress(progress)

    with open(OUTPUT_PATH, 'w') as f:
        json.dump(results, f, indent=2)

    # Stats
    print(f"\n{'='*60}")
    print(f"SCRAPING COMPLETE")
    print(f"{'='*60}")
    print(f"Total prospects: {len(prospects)}")
    print(f"Scraped this run: {scraped}")
    print(f"Failed: {failed}")
    print(f"Synthesia mentions found: {synthesia_found}")

    # Page type breakdown
    from collections import Counter
    type_counts = Counter(r['page_type'] for r in results)
    print(f"\n=== PAGE TYPE BREAKDOWN ===")
    for pt, count in type_counts.most_common():
        print(f"  {pt:<30} {count:>4} ({count/len(results)*100:.0f}%)")

    # Synthesia mentions
    synth_domains = [r['domain'] for r in results if r['synthesia'].get('has_mention')]
    synth_linked = [r['domain'] for r in results if r['synthesia'].get('has_link')]
    print(f"\n=== SYNTHESIA DETECTION ===")
    print(f"Pages mentioning Synthesia: {len(synth_domains)}")
    print(f"Pages linking to synthesia.io: {len(synth_linked)}")
    if synth_domains:
        print(f"\nDomains to EXCLUDE:")
        for d in synth_domains:
            r = next(x for x in results if x['domain'] == d)
            link_flag = " (has link!)" if r['synthesia'].get('has_link') else ""
            print(f"  {d}{link_flag}")

if __name__ == '__main__':
    main()
