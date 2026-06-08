#!/usr/bin/env python3
"""
review_websites.py — Quick review of SaaS companies + their videos.

Shows the company website and video side by side. Approve or reject.
Approved companies are exported to a Lusha-ready CSV.

Usage:
    python3 review_websites.py
    python3 review_websites.py --port 8889
    python3 review_websites.py --min-dr 10
    python3 review_websites.py --export-approved
"""

import argparse
import csv
import json
import os
import sqlite3
import webbrowser
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "saas_outreach.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "saas_300_outreach_ready.csv")
PAGE_VIDEOS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "page_videos.json")


def _load_csv_data():
    """Load the 300 outreach-ready companies from CSV."""
    import csv
    data = {}
    with open(CSV_PATH, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            domain = r.get('Domain', '').strip()
            if domain:
                # Collect all video URLs from the CSV
                videos = []
                for i in range(1, 11):
                    url = r.get(f'Video {i} URL', '').strip()
                    vtype = r.get(f'Video {i} Type', '').strip()
                    title = r.get(f'Video {i} Title', '').strip()
                    if url:
                        videos.append({'video_url': url, 'video_type': vtype, 'title': title, 'id': f'{domain}_v{i}'})
                # Sort: website videos first (youtube_embed, unknown, vimeo), then youtube_channel last
                type_priority = {'youtube_embed': 0, 'unknown': 1, 'vimeo': 2, 'youtube_channel': 3, 'vidyard': 1}
                videos.sort(key=lambda v: type_priority.get(v['video_type'], 2))

                # Override with live-scraped videos from page if available
                if os.path.exists(PAGE_VIDEOS_PATH):
                    with open(PAGE_VIDEOS_PATH) as pf:
                        page_data = json.load(pf)
                    if domain in page_data and page_data[domain].get('videos'):
                        page_vids = page_data[domain]['videos']
                        live_videos = []
                        for pv in page_vids:
                            live_videos.append({
                                'video_url': pv.get('url', ''),
                                'video_type': pv.get('type', 'page_embed'),
                                'title': f"[LIVE from page] {pv.get('type','')}",
                                'id': f'{domain}_live_{pv.get("video_id","")}'
                            })
                        # Live videos first, then CSV fallbacks
                        videos = live_videos + videos

                data[domain] = {
                    'domain': domain,
                    'name': r.get('Company Name', ''),
                    'website_url': r.get('Website URL', ''),
                    'category': r.get('Category', ''),
                    'domain_rating': float(r['Domain Rating']) if r.get('Domain Rating') else None,
                    'org_traffic': int(r['Organic Traffic']) if r.get('Organic Traffic') else None,
                    'org_keywords': int(r['Organic Keywords']) if r.get('Organic Keywords') else None,
                    'youtube_channel_url': r.get('YouTube Channel URL', ''),
                    'youtube_subscriber_count': int(r['YouTube Subscribers']) if r.get('YouTube Subscribers') else 0,
                    'outreach_status': r.get('Outreach Status', ''),
                    'block_reason': r.get('Block Reason', ''),
                    'matched_customer': r.get('Matched Customer', ''),
                    'customer_lifecycle': r.get('Customer Lifecycle', ''),
                    'match_type': r.get('Match Type', ''),
                    'videos': videos,
                }
    return data


def _load_db_data():
    """Load companies with videos from the database (not already in CSV)."""
    csv_data = _load_csv_data()
    conn = get_conn()
    rows = conn.execute('''
        SELECT c.domain, c.name, c.website_url, c.category,
               c.domain_rating, c.org_traffic, c.org_keywords,
               c.has_youtube_channel, c.youtube_channel_url,
               c.youtube_subscriber_count
        FROM companies c
        WHERE (c.domain_rating IS NULL OR (c.domain_rating >= 20 AND c.domain_rating < 85))
          AND (c.org_traffic IS NULL OR c.org_traffic < 500000)
          AND c.has_youtube_channel = 1
          AND EXISTS (SELECT 1 FROM company_videos v WHERE v.domain = c.domain)
        ORDER BY c.domain_rating DESC
    ''').fetchall()

    data = {}
    for r in rows:
        domain = r['domain']
        if domain in csv_data:
            continue  # already in CSV
        # Get videos for this company
        vrows = conn.execute('''
            SELECT id, video_type, video_url, title, detection_method
            FROM company_videos WHERE domain = ?
            ORDER BY id
        ''', (domain,)).fetchall()
        videos = []
        for vi, v in enumerate(vrows):
            videos.append({
                'video_url': v['video_url'] or '',
                'video_type': v['video_type'] or 'unknown',
                'title': v['title'] or '',
                'id': f'{domain}_db_{vi}',
            })
        if not videos:
            continue
        data[domain] = {
            'domain': domain,
            'name': r['name'] or '',
            'website_url': r['website_url'] or f'https://{domain}',
            'category': r['category'] or '',
            'domain_rating': r['domain_rating'],
            'org_traffic': r['org_traffic'],
            'org_keywords': r['org_keywords'],
            'youtube_channel_url': r['youtube_channel_url'] or '',
            'youtube_subscriber_count': r['youtube_subscriber_count'] or 0,
            'outreach_status': 'SAFE',
            'block_reason': '',
            'matched_customer': '',
            'customer_lifecycle': '',
            'match_type': '',
            'videos': videos,
        }
    conn.close()
    return data


def get_review_data(min_dr=0, page=1, per_page=20):
    """Get companies from CSV + DB, excluding already reviewed, sorted by DR. Paginated."""
    csv_data = _load_csv_data()
    db_data = _load_db_data()
    # Merge: CSV takes priority, DB fills in the rest
    all_data = {**db_data, **csv_data}
    decisions = _load_review_decisions()
    result = []
    for domain, comp in all_data.items():
        if not comp['videos']:
            continue
        if domain in decisions:
            continue  # already reviewed
        dr = comp.get('domain_rating') or 0
        if dr < min_dr and comp.get('domain_rating') is not None:
            continue
        result.append(comp)

    result.sort(key=lambda c: (c.get('domain_rating') or 0), reverse=True)
    total = len(result)
    start = (page - 1) * per_page
    return result[start:start + per_page], total


def build_html(data, min_dr=0, page=1, per_page=20, total=0):
    cards = ""
    for idx, comp in enumerate(data):
        safe_id = f"c{idx}"
        domain = comp['domain']
        dr = comp.get('domain_rating') or 0
        traffic = comp.get('org_traffic') or 0
        keywords = comp.get('org_keywords') or 0
        yt_url = comp.get('youtube_channel_url') or ''
        yt_subs = comp.get('youtube_subscriber_count') or 0

        video_options = ""
        for vi, v in enumerate(comp['videos']):
            title = (v.get('title') or v.get('video_url', ''))[:70]
            vtype = v.get('video_type', '?')
            escaped_url = v.get('video_url', '').replace('"', '&quot;').replace("'", "&#39;")
            vid_id = v.get('id', f'{domain}_v{vi}')
            video_options += f'<option value="{vid_id}" data-url="{escaped_url}" data-type="{vtype}">{title} [{vtype}]</option>\n'

        first_vid = comp['videos'][0]
        first_url = first_vid.get('video_url', '')
        embed_html = _get_embed_html(first_url, first_vid.get('video_type', ''))

        # Escape domain for JS strings
        escaped_domain = domain.replace("'", "\\'")

        # CSV-specific fields
        outreach_status = comp.get('outreach_status', '')
        block_reason = comp.get('block_reason', '')
        matched_customer = comp.get('matched_customer', '')
        customer_lifecycle = comp.get('customer_lifecycle', '')
        match_type = comp.get('match_type', '')

        status_class = 'status-safe' if outreach_status == 'SAFE' else 'status-blocked'

        cards += f'''
        <div class="card" id="card-{safe_id}" data-domain="{domain}">
            <div class="card-header">
                <div class="channel-info">
                    <h2><a href="{comp.get('website_url','')}" target="_blank">{comp['name']}</a></h2>
                    <div class="meta">
                        <span class="badge {status_class}">{outreach_status}</span>
                        <span class="badge dr">DR {dr:.0f}</span>
                        <span class="badge traffic">{traffic:,}/mo</span>
                        <span class="badge kw">{keywords:,} kw</span>
                        <span class="badge cat">{comp.get('category','')}</span>
                        <a href="{comp.get('website_url','')}" target="_blank" class="badge website" id="domain-badge-{safe_id}">{domain}</a>
                        <button class="btn edit-domain-btn" onclick="editDomain('{safe_id}', '{escaped_domain}')">✎</button>
                        {f'<a href="{yt_url}" target="_blank" class="badge yt">YouTube ({yt_subs:,} subs)</a>' if yt_url else ''}
                    </div>
                    <div class="csv-info">
                        {f'<span class="csv-field"><b>Block Reason:</b> {block_reason}</span>' if block_reason else ''}
                        {f'<span class="csv-field"><b>Matched Customer:</b> {matched_customer}</span>' if matched_customer else ''}
                        {f'<span class="csv-field"><b>Customer Lifecycle:</b> {customer_lifecycle}</span>' if customer_lifecycle else ''}
                        {f'<span class="csv-field"><b>Match Type:</b> {match_type}</span>' if match_type else ''}
                    </div>
                </div>
                <div class="header-actions">
                    <a href="{comp.get('website_url','')}" target="_blank" class="btn visit">Visit Website</a>
                </div>
            </div>
            <div class="card-body">
                <div class="two-panel">
                    <div class="website-panel">
                        <div class="section-label">Website</div>
                        <div class="site-preview" id="site-preview-{safe_id}">
                            <iframe class="site-iframe" src="{comp.get('website_url','')}" sandbox="allow-scripts allow-same-origin" loading="lazy" onload="this.dataset.loaded='true'" onerror="showFallback('{safe_id}', '{comp.get('website_url','').replace(chr(39), '')}')"></iframe>
                            <div class="site-fallback" id="site-fallback-{safe_id}" style="display:none">
                                <a href="{comp.get('website_url','')}" target="_blank" class="fallback-link">
                                    <div class="fallback-icon">🌐</div>
                                    <div class="fallback-domain">{domain}</div>
                                    <div class="fallback-hint">Click to open website</div>
                                </a>
                            </div>
                        </div>
                    </div>
                    <div class="video-panel">
                        <div class="section-label">Video to Dub</div>
                        <div class="video-nav">
                            <span class="video-counter" id="vcounter-{safe_id}">Video 1 of {len(comp['videos'])}</span>
                            {'<button class="btn nav-btn" onclick="prevVideo(' + "'" + safe_id + "'" + ')">Prev</button>' if len(comp['videos']) > 1 else ''}
                            {'<button class="btn nav-btn" onclick="nextVideo(' + "'" + safe_id + "'" + ')">Next</button>' if len(comp['videos']) > 1 else ''}
                        </div>
                        <div class="player" id="player-{safe_id}">
                            {embed_html}
                        </div>
                        <div class="video-info-row">
                            <span class="video-title" id="vtitle-{safe_id}">{(comp['videos'][0].get('title') or '')[:80]}</span>
                            <span class="video-source" id="vsource-{safe_id}">[{comp['videos'][0].get('video_type', '?')}]</span>
                        </div>
                        <select class="hidden-select" id="vselect-{safe_id}" style="display:none">{video_options}</select>
                        <div class="custom-video-row">
                            <label>Or paste URL:</label>
                            <input type="text" class="custom-url-input" id="custom-url-{safe_id}" placeholder="https://www.youtube.com/watch?v=...">
                            <button class="btn nav-btn" onclick="loadCustomVideo('{safe_id}')">Load</button>
                        </div>
                        <div class="trim-controls">
                            <label>Dub from</label>
                            <input type="text" class="time-input" id="start-{safe_id}" value="0:00">
                            <label>to</label>
                            <input type="text" class="time-input" id="end-{safe_id}" value="0:30">
                        </div>
                    </div>
                </div>
                <div class="actions">
                    <button class="btn approve" onclick="approveCompany('{safe_id}', '{escaped_domain}')">Approve Company</button>
                    <button class="btn reject" onclick="rejectCompany('{safe_id}', '{escaped_domain}')">Reject Company</button>
                    <button class="btn scan" onclick="scanPage('{safe_id}', '{escaped_domain}', '{comp.get("website_url","").replace("'", "")}')">Scan Page</button>
                </div>
            </div>
            <div class="status-msg" id="status-{safe_id}"></div>
        </div>
        '''

    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>SaaS Video Review</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f0f0f; color: #e0e0e0; padding: 20px; }}
    h1 {{ text-align: center; margin: 20px 0 10px; color: #fff; }}
    .tabs {{ display: flex; justify-content: center; gap: 4px; margin-bottom: 10px; }}
    .tab {{ padding: 10px 28px; background: #222; color: #888; text-decoration: none; border-radius: 8px 8px 0 0; font-size: 15px; font-weight: 600; }}
    .tab:hover {{ color: #fff; background: #333; }}
    .tab.active {{ background: #1a1a2e; color: #4fc3f7; }}
    .subtitle {{ text-align: center; color: #888; margin-bottom: 10px; }}
    .filters {{ text-align: center; margin-bottom: 20px; }}
    .filters a {{ color: #4fc3f7; margin: 0 10px; text-decoration: none; }}
    .filters a:hover {{ text-decoration: underline; }}
    .counter {{ position: sticky; top: 0; z-index: 100; text-align: center; margin-bottom: 20px; padding: 12px 10px; background: #1a1a2e; border-radius: 8px; font-size: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }}
    .counter span {{ margin: 0 15px; }}
    .counter .approved {{ color: #4caf50; }}
    .counter .rejected {{ color: #f44336; }}
    .counter .pending {{ color: #ffc107; }}
    .card {{ background: #1a1a1a; border-radius: 12px; margin-bottom: 24px; overflow: hidden; border: 1px solid #333; transition: opacity 0.3s; }}
    .card.done {{ opacity: 0.25; pointer-events: none; }}
    .card-header {{ padding: 16px 20px; border-bottom: 1px solid #333; display: flex; justify-content: space-between; align-items: flex-start; }}
    .channel-info {{ flex: 1; }}
    .channel-info h2 {{ font-size: 18px; margin-bottom: 4px; }}
    .channel-info h2 a {{ color: #fff; text-decoration: none; }}
    .channel-info h2 a:hover {{ color: #4fc3f7; }}
    .desc {{ font-size: 12px; color: #888; margin-bottom: 8px; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .badge {{ padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; text-decoration: none; }}
    .dr {{ background: #1b5e20; color: #a5d6a7; }}
    .traffic {{ background: #4a148c; color: #ce93d8; }}
    .kw {{ background: #0d47a1; color: #90caf9; }}
    .cat {{ background: #37474f; color: #b0bec5; }}
    .website {{ background: #263238; color: #80cbc4; }}
    .yt {{ background: #b71c1c; color: #ef9a9a; }}
    .status-safe {{ background: #1b5e20; color: #a5d6a7; }}
    .status-blocked {{ background: #b71c1c; color: #ef9a9a; }}
    .csv-info {{ margin-top: 8px; display: flex; flex-wrap: wrap; gap: 12px; }}
    .csv-field {{ font-size: 12px; color: #aaa; }}
    .csv-field b {{ color: #ccc; }}
    .header-actions {{ margin-left: 16px; }}
    .card-body {{ padding: 16px 20px; }}
    .two-panel {{ display: flex; gap: 16px; margin-bottom: 16px; }}
    .website-panel {{ flex: 1; min-width: 0; }}
    .video-panel {{ flex: 1; min-width: 0; }}
    .section-label {{ font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }}
    .site-preview {{ position: relative; }}
    .site-iframe {{ width: 100%; height: 400px; border-radius: 8px; border: 1px solid #333; background: #fff; }}
    .site-fallback {{ width: 100%; height: 400px; border-radius: 8px; border: 1px solid #333; background: #1a1a2e; display: flex; align-items: center; justify-content: center; }}
    .fallback-link {{ text-decoration: none; text-align: center; color: #e0e0e0; }}
    .fallback-icon {{ font-size: 48px; margin-bottom: 12px; }}
    .fallback-domain {{ font-size: 20px; font-weight: 600; color: #4fc3f7; margin-bottom: 8px; }}
    .fallback-hint {{ font-size: 13px; color: #888; }}
    .custom-url-input {{ flex: 1; padding: 6px 10px; background: #222; color: #fff; border: 1px solid #555; border-radius: 4px; font-size: 13px; }}
    .custom-video-row {{ display: flex; align-items: center; gap: 6px; margin: 8px 0; padding: 8px; background: #1a2030; border-radius: 6px; border: 1px dashed #445; }}
    .custom-video-row label {{ font-size: 11px; color: #88a; white-space: nowrap; }}
    .video-section {{ margin-bottom: 16px; }}
    .video-select {{ margin-bottom: 12px; }}
    .video-select label {{ font-size: 13px; color: #aaa; margin-right: 8px; }}
    .video-select select {{ width: 75%; padding: 6px 10px; background: #2a2a2a; color: #fff; border: 1px solid #444; border-radius: 6px; font-size: 13px; }}
    .player {{ margin-bottom: 12px; }}
    .player iframe {{ width: 100%; height: 400px; border-radius: 8px; border: none; }}
    .player .no-embed {{ padding: 20px; background: #222; border-radius: 8px; text-align: center; }}
    .player .no-embed a {{ color: #4fc3f7; }}
    .actions {{ display: flex; gap: 12px; }}
    .btn {{ padding: 10px 24px; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; text-decoration: none; color: #fff; }}
    .btn.approve {{ background: #4caf50; }}
    .btn.approve:hover {{ background: #66bb6a; }}
    .btn.reject {{ background: #f44336; }}
    .btn.reject:hover {{ background: #ef5350; }}
    .btn.scan {{ background: #1565c0; }}
    .btn.edit-domain-btn {{ padding: 2px 8px; font-size: 11px; background: #444; border-radius: 8px; min-width: 0; }}
    .btn.scan:hover {{ background: #1976d2; }}
    .btn.scan.loading {{ background: #555; cursor: wait; }}
    .btn.visit {{ background: #1565c0; font-size: 12px; padding: 8px 16px; }}
    .btn.visit:hover {{ background: #1976d2; }}
    .status-msg {{ padding: 8px 20px; font-size: 14px; font-weight: 600; display: none; }}
    .status-msg.show {{ display: block; }}
    .status-msg.approved {{ background: #1b5e20; color: #a5d6a7; }}
    .status-msg.rejected {{ background: #b71c1c; color: #ef9a9a; }}
    .toast {{ position: fixed; top: 20px; right: 20px; padding: 14px 24px; border-radius: 8px; font-size: 15px; font-weight: 600; z-index: 1000; transition: opacity 0.5s; }}
    .toast.approve-toast {{ background: #4caf50; color: #fff; }}
    .toast.reject-toast {{ background: #f44336; color: #fff; }}
    .two-col {{ display: flex; gap: 20px; margin-bottom: 16px; }}
    .website-preview {{ flex: 1; }}
    .video-section {{ flex: 1; }}
    .section-label {{ font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }}
    .site-iframe {{ width: 100%; height: 420px; border-radius: 8px; border: 1px solid #333; background: #fff; }}
    .video-nav {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }}
    .video-counter {{ font-size: 13px; color: #aaa; }}
    .nav-btn {{ background: #37474f; padding: 6px 14px; font-size: 12px; font-weight: 500; }}
    .nav-btn:hover {{ background: #455a64; }}
    .video-info-row {{ display: flex; align-items: center; gap: 8px; margin-top: 6px; margin-bottom: 10px; }}
    .video-title {{ font-size: 12px; color: #999; }}
    .video-source {{ font-size: 11px; color: #666; background: #2a2a2a; padding: 2px 8px; border-radius: 4px; }}
    .trim-controls {{ display: flex; align-items: center; gap: 8px; margin-bottom: 12px; padding: 10px; background: #222; border-radius: 8px; }}
    .trim-controls label {{ font-size: 13px; color: #aaa; }}
    .time-input {{ width: 60px; padding: 6px; background: #333; color: #fff; border: 1px solid #555; border-radius: 4px; text-align: center; font-size: 14px; }}
    .pagination {{ text-align: center; margin: 20px 0; }}
    .pagination a {{ color: #4fc3f7; margin: 0 15px; text-decoration: none; font-size: 16px; }}
    .pagination a:hover {{ text-decoration: underline; }}
    .pagination span {{ color: #888; font-size: 14px; }}
</style>
</head>
<body>
<div class="tabs">
    <a href="/" class="tab active">Review</a>
    <a href="/dashboard" class="tab">Dashboard</a>
</div>
<h1>SaaS Video Review</h1>
<p class="subtitle">Showing {len(data)} of {total} remaining (page {page}, min DR: {min_dr})</p>
<div class="filters">
    <a href="/?min_dr=0">All</a>
    <a href="/?min_dr=10">DR 10+</a>
    <a href="/?min_dr=20">DR 20+</a>
    <a href="/?min_dr=30">DR 30+</a>
    <a href="/?min_dr=50">DR 50+</a>
</div>
<div class="counter">
    <span class="approved" id="cnt-approved">Approved: 0</span>
    <span class="rejected" id="cnt-rejected">Rejected: 0</span>
    <span class="pending" id="cnt-pending">Pending: {total}</span>
</div>
<div class="pagination">
    {f'<a href="/?min_dr={min_dr}&page={page-1}">← Previous</a>' if page > 1 else ''}
    <span>Page {page} of {max(1, (total + per_page - 1) // per_page)}</span>
    {f'<a href="/?min_dr={min_dr}&page={page+1}">Next →</a>' if page * per_page < total else ''}
</div>

{cards}

<div class="pagination">
    {f'<a href="/?min_dr={min_dr}&page={page-1}">← Previous</a>' if page > 1 else ''}
    <span>Page {page} of {max(1, (total + per_page - 1) // per_page)}</span>
    {f'<a href="/?min_dr={min_dr}&page={page+1}">Next →</a>' if page * per_page < total else ''}
</div>

<script>
let approved = 0, rejected = 0, pending = {len(data)};

// Load existing review counts on page load
fetch('/api/stats').then(r => r.json()).then(s => {{
    document.getElementById('cnt-approved').textContent = 'Approved: ' + s.approved;
    document.getElementById('cnt-rejected').textContent = 'Rejected: ' + s.rejected;
    approved = s.approved;
    rejected = s.rejected;
}});

function updateCounters() {{
    document.getElementById('cnt-approved').textContent = 'Approved: ' + approved;
    document.getElementById('cnt-rejected').textContent = 'Rejected: ' + rejected;
    document.getElementById('cnt-pending').textContent = 'Pending: ' + pending;
}}

function showToast(msg, type) {{
    const toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => {{ toast.style.opacity = '0'; }}, 1500);
    setTimeout(() => {{ toast.remove(); }}, 2000);
}}

function getEmbedUrl(videoUrl, videoType) {{
    if (!videoUrl) return null;
    // YouTube
    let m = videoUrl.match(/(?:youtube\\.com\\/watch\\?v=|youtu\\.be\\/)([\\w-]+)/);
    if (m) return 'https://www.youtube.com/embed/' + m[1];
    m = videoUrl.match(/youtube\\.com\\/embed\\/([\\w-]+)/);
    if (m) return 'https://www.youtube.com/embed/' + m[1];
    // Vimeo
    m = videoUrl.match(/vimeo\\.com\\/(\\d+)/);
    if (m) return 'https://player.vimeo.com/video/' + m[1];
    // Wistia
    m = videoUrl.match(/wistia\\.(?:com|net)\\/.*\\/([\\w]+)/);
    if (m) return 'https://fast.wistia.net/embed/iframe/' + m[1];
    return null;
}}

function nextVideo(safeId) {{
    const sel = document.getElementById('vselect-' + safeId);
    if (sel.selectedIndex < sel.options.length - 1) {{
        sel.selectedIndex++;
        changeVideo(sel, safeId);
    }}
}}

function prevVideo(safeId) {{
    const sel = document.getElementById('vselect-' + safeId);
    if (sel.selectedIndex > 0) {{
        sel.selectedIndex--;
        changeVideo(sel, safeId);
    }}
}}

function changeVideo(sel, safeId) {{
    const opt = sel.options[sel.selectedIndex];
    const url = opt.dataset.url;
    const type = opt.dataset.type;
    const player = document.getElementById('player-' + safeId);
    const embedUrl = getEmbedUrl(url, type);
    if (embedUrl) {{
        player.innerHTML = '<iframe src="' + embedUrl + '" allowfullscreen></iframe>';
    }} else {{
        player.innerHTML = '<div class="no-embed"><a href="' + url + '" target="_blank">Open video in new tab: ' + url.substring(0,80) + '</a></div>';
    }}
    // Update counter, title and source
    const counter = document.getElementById('vcounter-' + safeId);
    if (counter) counter.textContent = 'Video ' + (sel.selectedIndex + 1) + ' of ' + sel.options.length;
    const title = document.getElementById('vtitle-' + safeId);
    if (title) title.textContent = opt.textContent.replace(/\\s*\\[.*\\]\\s*$/, '').substring(0, 80);
    const source = document.getElementById('vsource-' + safeId);
    if (source) {{
        const typeMatch = opt.textContent.match(/\\[([^\\]]+)\\]$/);
        source.textContent = typeMatch ? '[' + typeMatch[1] + ']' : '';
    }}
}}

function loadCustomVideo(safeId) {{
    const url = document.getElementById('custom-url-' + safeId).value.trim();
    if (!url) return;
    const player = document.getElementById('player-' + safeId);
    const embedUrl = getEmbedUrl(url, '');
    if (embedUrl) {{
        player.innerHTML = '<iframe src="' + embedUrl + '" allowfullscreen></iframe>';
    }} else {{
        player.innerHTML = '<div class="no-embed"><a href="' + url + '" target="_blank">Open video: ' + url.substring(0,80) + '</a></div>';
    }}
    // Also add it to the hidden select so it gets saved on approve
    const sel = document.getElementById('vselect-' + safeId);
    const opt = document.createElement('option');
    opt.value = 'custom_' + Date.now();
    opt.dataset.url = url;
    opt.dataset.type = 'custom_paste';
    opt.textContent = '[CUSTOM] ' + url.substring(0, 60);
    sel.appendChild(opt);
    sel.selectedIndex = sel.options.length - 1;
    showToast('Custom video loaded', 'approve-toast');
}}

function scanPage(safeId, domain, url) {{
    const btn = event.target;
    btn.textContent = 'Scanning...';
    btn.classList.add('loading');
    fetch('/api/scan', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{domain: domain, url: url}})
    }}).then(r => r.json()).then(data => {{
        btn.classList.remove('loading');
        if (data.videos && data.videos.length > 0) {{
            btn.textContent = 'Found ' + data.videos.length + ' video(s)';
            // Rebuild the select dropdown with new videos
            const sel = document.getElementById('vselect-' + safeId);
            sel.innerHTML = '';
            data.videos.forEach((v, i) => {{
                const opt = document.createElement('option');
                opt.value = domain + '_scan_' + i;
                opt.dataset.url = v.url;
                opt.dataset.type = v.type;
                opt.textContent = '[SCANNED] ' + v.type + ' — ' + v.url.substring(0, 60);
                sel.appendChild(opt);
            }});
            sel.selectedIndex = 0;
            changeVideo(sel, safeId);
            showToast('Found ' + data.videos.length + ' video(s) on page', 'approve-toast');
        }} else {{
            btn.textContent = 'No videos found';
            showToast('No videos found on page', 'reject-toast');
        }}
    }}).catch(err => {{
        btn.classList.remove('loading');
        btn.textContent = 'Scan failed';
        showToast('Scan error: ' + err, 'reject-toast');
    }});
}}

function parseMMSS(str) {{
    const parts = str.split(':');
    if (parts.length === 2) return parseInt(parts[0]) * 60 + parseInt(parts[1]);
    return parseInt(str) || 0;
}}

function approveCompany(safeId, domain) {{
    const card = document.getElementById('card-' + safeId);
    const name = card.querySelector('h2 a').textContent;
    const sel = document.getElementById('vselect-' + safeId);
    const opt = sel.options[sel.selectedIndex];
    const videoUrl = opt ? opt.dataset.url : '';
    const videoType = opt ? opt.dataset.type : '';
    const videoLabel = opt ? opt.textContent : '';
    const isFromPage = videoLabel.includes('[LIVE from page]') || videoLabel.includes('[SCANNED]');
    const videoSource = isFromPage ? 'found_on_page' : (videoType === 'youtube_channel' ? 'youtube_channel' : 'pre_detected');
    const pageUrl = card.querySelector('.badge.website') ? card.querySelector('.badge.website').href : '';
    const startTime = document.getElementById('start-' + safeId).value;
    const endTime = document.getElementById('end-' + safeId).value;
    fetch('/api/approve', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{
            domain: domain,
            selected_video_url: videoUrl,
            selected_video_type: videoType,
            video_source: videoSource,
            page_url: pageUrl,
            trim_start: parseMMSS(startTime),
            trim_end: parseMMSS(endTime)
        }})
    }}).then(r => r.json()).then(data => {{
        const msg = document.getElementById('status-' + safeId);
        msg.textContent = '✓ APPROVED — saved to approved_for_lusha.csv';
        msg.className = 'status-msg show approved';
        card.classList.add('done');
        approved = data.approved; rejected = data.rejected; pending--;
        updateCounters();
        showToast('✓ Approved: ' + name, 'approve-toast');
        const next = card.nextElementSibling;
        if (next && next.classList.contains('card')) next.scrollIntoView({{behavior: 'smooth', block: 'start'}});
    }}).catch(err => {{
        showToast('Error: ' + err, 'reject-toast');
    }});
}}

// Check iframes after page load — if they're blank/blocked, show fallback
setTimeout(function() {{
    document.querySelectorAll('.site-iframe').forEach(function(iframe) {{
        const safeId = iframe.closest('.card').id.replace('card-', '');
        try {{
            // Try to access iframe content — will throw if blocked by CORS/X-Frame-Options
            const doc = iframe.contentDocument || iframe.contentWindow.document;
            if (!doc || !doc.body || doc.body.innerHTML.length < 50) {{
                showFallback(safeId);
            }}
        }} catch(e) {{
            // Cross-origin = likely loaded fine, keep iframe
        }}
    }});
}}, 3000);

function showFallback(safeId) {{
    const iframe = document.querySelector('#site-preview-' + safeId + ' .site-iframe');
    const fallback = document.getElementById('site-fallback-' + safeId);
    if (iframe) iframe.style.display = 'none';
    if (fallback) fallback.style.display = 'flex';
}}

function editDomain(safeId, oldDomain) {{
    const newDomain = prompt('Enter new domain for this company:', oldDomain);
    if (!newDomain || newDomain === oldDomain) return;
    fetch('/api/update-domain', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{old_domain: oldDomain, new_domain: newDomain}})
    }}).then(r => r.json()).then(data => {{
        if (data.ok) {{
            // Update the badge text and link
            const badge = document.getElementById('domain-badge-' + safeId);
            if (badge) {{
                badge.textContent = newDomain;
                badge.href = 'https://' + newDomain;
            }}
            // Update the iframe
            const card = document.getElementById('card-' + safeId);
            const iframe = card.querySelector('.site-iframe');
            if (iframe) iframe.src = 'https://' + newDomain;
            // Update the card's data-domain
            card.dataset.domain = newDomain;
            // Update the Visit Website link
            const visitBtn = card.querySelector('.btn.visit');
            if (visitBtn) visitBtn.href = 'https://' + newDomain;
            // Update the company name link
            const nameLink = card.querySelector('h2 a');
            if (nameLink) nameLink.href = 'https://' + newDomain;
            showToast('Domain updated to ' + newDomain, 'approve-toast');
        }} else {{
            showToast('Error: ' + (data.error || 'unknown'), 'reject-toast');
        }}
    }}).catch(err => showToast('Error: ' + err, 'reject-toast'));
}}

function rejectCompany(safeId, domain) {{
    const card = document.getElementById('card-' + safeId);
    const name = card.querySelector('h2 a').textContent;
    fetch('/api/reject', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{domain: domain}})
    }}).then(r => r.json()).then(data => {{
        const msg = document.getElementById('status-' + safeId);
        msg.textContent = '✗ REJECTED';
        msg.className = 'status-msg show rejected';
        card.classList.add('done');
        approved = data.approved; rejected = data.rejected; pending--;
        updateCounters();
        showToast('✗ Rejected: ' + name, 'reject-toast');
        const next = card.nextElementSibling;
        if (next && next.classList.contains('card')) next.scrollIntoView({{behavior: 'smooth', block: 'start'}});
    }}).catch(err => {{
        showToast('Error: ' + err, 'reject-toast');
    }});
}}
</script>
</body>
</html>'''


def _get_embed_html(video_url, video_type):
    """Generate embed HTML for a video URL."""
    if not video_url:
        return '<div class="no-embed">No video URL</div>'

    import re
    # YouTube
    m = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)', video_url)
    if m:
        return f'<iframe src="https://www.youtube.com/embed/{m.group(1)}" allowfullscreen></iframe>'
    m = re.search(r'youtube\.com/embed/([\w-]+)', video_url)
    if m:
        return f'<iframe src="https://www.youtube.com/embed/{m.group(1)}" allowfullscreen></iframe>'
    # Vimeo
    m = re.search(r'vimeo\.com/(\d+)', video_url)
    if m:
        return f'<iframe src="https://player.vimeo.com/video/{m.group(1)}" allowfullscreen></iframe>'

    return f'<div class="no-embed"><a href="{video_url}" target="_blank">Open video: {video_url[:80]}</a></div>'


REVIEW_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "review_decisions.json")


def _scan_with_headless(url):
    """Use playwright headless browser to find videos on a page."""
    from playwright.sync_api import sync_playwright
    from scrape_page_videos import extract_videos_from_html

    videos = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(15000)
        try:
            page.goto(url, wait_until='networkidle', timeout=20000)
            # Wait a bit for lazy-loaded content
            page.wait_for_timeout(3000)
            html = page.content()
            videos = extract_videos_from_html(html)

            # Also check for iframes with video sources
            frames = page.frames
            for frame in frames:
                try:
                    frame_url = frame.url
                    if 'youtube.com/embed' in frame_url:
                        import re
                        m = re.search(r'youtube\.com/embed/([\w-]+)', frame_url)
                        if m:
                            vid_id = m.group(1)
                            found_ids = {v.get('video_id') for v in videos}
                            if vid_id not in found_ids:
                                videos.insert(0, {
                                    'url': f'https://www.youtube.com/watch?v={vid_id}',
                                    'type': 'youtube_embed',
                                    'video_id': vid_id,
                                })
                    elif 'vimeo.com' in frame_url:
                        import re
                        m = re.search(r'vimeo\.com/(?:video/)?(\d+)', frame_url)
                        if m:
                            vid_id = m.group(1)
                            found_ids = {v.get('video_id') for v in videos}
                            if vid_id not in found_ids:
                                videos.insert(0, {
                                    'url': f'https://vimeo.com/{vid_id}',
                                    'type': 'vimeo',
                                    'video_id': vid_id,
                                })
                except Exception:
                    pass
        except Exception as e:
            print(f"Headless scan error for {url}: {e}")
        finally:
            browser.close()

    return videos


def _load_review_decisions():
    if os.path.exists(REVIEW_FILE):
        with open(REVIEW_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_review_decision(domain, status, extra=None):
    decisions = _load_review_decisions()
    csv_data = _load_csv_data()
    db_data = _load_db_data()
    comp = csv_data.get(domain) or db_data.get(domain) or {}
    entry = {
        'status': status,
        'at': datetime.now().isoformat(),
        'name': comp.get('name', ''),
        'website_url': comp.get('website_url', ''),
        'category': comp.get('category', ''),
        'domain_rating': comp.get('domain_rating'),
        'org_traffic': comp.get('org_traffic'),
        'org_keywords': comp.get('org_keywords'),
        'youtube_channel_url': comp.get('youtube_channel_url', ''),
        'outreach_status': comp.get('outreach_status', ''),
        'block_reason': comp.get('block_reason', ''),
        'matched_customer': comp.get('matched_customer', ''),
        'customer_lifecycle': comp.get('customer_lifecycle', ''),
        'match_type': comp.get('match_type', ''),
        'videos': [{'url': v.get('video_url',''), 'type': v.get('video_type',''), 'title': v.get('title','')} for v in comp.get('videos', [])],
    }
    if extra:
        entry['selected_video_url'] = extra.get('selected_video_url', '')
        entry['selected_video_type'] = extra.get('selected_video_type', '')
        entry['video_source'] = extra.get('video_source', 'unknown')
        entry['page_url'] = extra.get('page_url', '')
        entry['trim_start'] = extra.get('trim_start', 0)
        entry['trim_end'] = extra.get('trim_end', 30)
    decisions[domain] = entry
    with open(REVIEW_FILE, 'w') as f:
        json.dump(decisions, f, indent=2)
    _auto_export_approved(decisions, csv_data)


def _auto_export_approved(decisions, csv_data):
    """Auto-export approved companies to CSV after each decision."""
    approved = [d for d in decisions.values() if d['status'] == 'approved']
    if not approved:
        return
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "approved_for_lusha.csv")
    fieldnames = ["Company Name", "Domain", "Website", "Category", "Domain Rating",
                   "Organic Traffic", "Organic Keywords", "YouTube Channel",
                   "Selected Video URL", "Video Source", "Page URL", "Trim Start", "Trim End",
                   "Outreach Status", "Matched Customer", "Customer Lifecycle", "Match Type"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for d in sorted(approved, key=lambda x: x.get('domain_rating') or 0, reverse=True):
            start = d.get('trim_start', 0)
            end = d.get('trim_end', 30)
            writer.writerow({
                "Company Name": d.get('name', ''),
                "Domain": next((dom for dom, v in decisions.items() if v is d), ''),
                "Website": d.get('website_url', ''),
                "Category": d.get('category', ''),
                "Domain Rating": d.get('domain_rating', ''),
                "Organic Traffic": d.get('org_traffic', ''),
                "Organic Keywords": d.get('org_keywords', ''),
                "YouTube Channel": d.get('youtube_channel_url', ''),
                "Selected Video URL": d.get('selected_video_url', ''),
                "Video Source": d.get('video_source', 'unknown'),
                "Page URL": d.get('page_url', ''),
                "Trim Start": f"{start // 60}:{start % 60:02d}" if isinstance(start, int) else start,
                "Trim End": f"{end // 60}:{end % 60:02d}" if isinstance(end, int) else end,
                "Outreach Status": d.get('outreach_status', ''),
                "Matched Customer": d.get('matched_customer', ''),
                "Customer Lifecycle": d.get('customer_lifecycle', ''),
                "Match Type": d.get('match_type', ''),
            })


def build_dashboard_html():
    """Build dashboard showing all approved companies with full details."""
    decisions = _load_review_decisions()
    approved = {k: v for k, v in decisions.items() if v.get('status') == 'approved'}

    rows_html = ""
    row_num = 0
    for domain, d in sorted(approved.items(), key=lambda x: x[1].get('domain_rating') or 0, reverse=True):
        row_num += 1
        hunter = d.get('hunter_contact', {})
        contact_name = f"{hunter.get('first_name','')} {hunter.get('last_name','')}".strip() if hunter.get('email') else ''
        contact_email = hunter.get('email', '')
        contact_title = hunter.get('position', '') or hunter.get('job_title', '')
        share_link = d.get('synthesia_share_link', '')
        asset_id = share_link.replace('https://share.synthesia.io/', '') if share_link else ''
        gif_url = f"https://synthesia-ttv-data.s3.amazonaws.com/video_data/{asset_id}/transfers/rendered_video.gif" if asset_id else ''
        video_source = d.get('video_source', '')
        dr = d.get('domain_rating') or 0
        traffic = d.get('org_traffic') or 0
        dubbed_to = d.get('dubbed_to', '')
        start = d.get('trim_start', 0)
        end = d.get('trim_end', 30)
        trim_str = f"{start // 60}:{start % 60:02d} - {end // 60}:{end % 60:02d}" if isinstance(start, int) else ''

        has_video_url = bool(d.get('selected_video_url'))
        rows_html += f'''<tr data-domain="{domain}">
            <td><input type="checkbox" class="select-cb" data-domain="{domain}" {'checked' if has_video_url and not share_link else ''}></td>
            <td class="row-num">{row_num}</td>
            <td><a href="{d.get('website_url','')}" target="_blank">{d.get('name','')}</a></td>
            <td>{domain}</td>
            <td>{dr:.0f}</td>
            <td>{traffic:,}</td>
            <td>{contact_name}</td>
            <td>{contact_email}</td>
            <td>{contact_title}</td>
            <td>{video_source}</td>
            <td>{dubbed_to}</td>
            <td>{trim_str}</td>
            <td>{'<a href="' + share_link + '" target="_blank">Link</a>' if share_link else ''}</td>
            <td>{'<img src="' + gif_url + '" width="120" style="border-radius:4px;" />' if gif_url else ''}</td>
            <td>{d.get('category','')}</td>
            <td>{d.get('outreach_status','')}</td>
            <td>{d.get('matched_customer','')}</td>
            <td><input type="checkbox" class="outreach-cb" data-domain="{domain}" {'checked' if d.get('outreached') or contact_email else ''} onchange="toggleOutreached(this)"></td>
        </tr>'''

    with_contact = sum(1 for v in approved.values() if (v.get('hunter_contact') or dict()).get('email'))
    with_video = sum(1 for v in approved.values() if v.get('synthesia_share_link'))

    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Dashboard — SaaS Video Outreach</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #fff; color: #333; padding: 20px; }}
    .tabs {{ display: flex; justify-content: center; gap: 4px; margin-bottom: 10px; }}
    .tab {{ padding: 10px 28px; background: #eee; color: #666; text-decoration: none; border-radius: 8px 8px 0 0; font-size: 15px; font-weight: 600; }}
    .tab:hover {{ color: #333; background: #ddd; }}
    .tab.active {{ background: #1a73e8; color: #fff; }}
    h1 {{ text-align: center; margin: 10px 0; color: #222; }}
    .subtitle {{ text-align: center; color: #888; margin-bottom: 15px; }}
    .stats {{ text-align: center; margin-bottom: 15px; }}
    .stats span {{ margin: 0 15px; font-size: 14px; font-weight: 600; }}
    .stats .s-approved {{ color: #2e7d32; }}
    .stats .s-contact {{ color: #1565c0; }}
    .stats .s-video {{ color: #7b1fa2; }}
    .search-bar {{ display: flex; justify-content: center; margin-bottom: 15px; }}
    .search-bar input {{ width: 400px; padding: 8px 14px; font-size: 14px; border: 1px solid #ccc; border-radius: 8px; }}
    .col-filter {{ width: 100%; padding: 3px 4px; font-size: 10px; border: 1px solid #ddd; border-radius: 3px; background: #fff; color: #333; }}
    .filter-header td {{ padding: 4px 6px; background: #fafafa; border-bottom: 2px solid #ddd; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; table-layout: auto; }}
    thead {{ position: sticky; top: 0; z-index: 10; }}
    th {{ background: #f5f5f5; color: #555; padding: 8px 6px; text-align: left; cursor: pointer; white-space: nowrap; border-bottom: 2px solid #ddd; user-select: none; }}
    th:hover {{ background: #e8e8e8; color: #222; }}
    th .sort-arrow {{ font-size: 10px; margin-left: 3px; color: #aaa; }}
    .row-num {{ color: #aaa; font-size: 11px; text-align: center; width: 30px; }}
    td {{ padding: 6px; border-bottom: 1px solid #eee; vertical-align: middle; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    tr:hover {{ background: #f8f8ff; }}
    td a {{ color: #1a73e8; text-decoration: none; }}
    td a:hover {{ text-decoration: underline; }}
    td img {{ display: block; border-radius: 4px; }}
    .export-btn {{ display: block; margin: 20px auto; padding: 10px 24px; background: #1a73e8; color: #fff; border: none; border-radius: 8px; font-size: 14px; cursor: pointer; }}
    .export-btn:hover {{ background: #1565c0; }}
</style></head><body>
<div class="tabs">
    <a href="/" class="tab">Review</a>
    <a href="/dashboard" class="tab active">Dashboard</a>
</div>
<h1>Outreach Dashboard</h1>
<p class="subtitle">{len(approved)} approved companies</p>
<div class="stats">
    <span class="s-approved">Approved: {len(approved)}</span>
    <span class="s-contact">With contact: {with_contact}</span>
    <span class="s-video">With dubbed video: {with_video}</span>
</div>
<div class="search-bar">
    <input type="text" id="searchBox" placeholder="Search across all columns..." onkeyup="filterTable()">
</div>
<table id="dashTable">
    <thead>
        <tr>
            <th><input type="checkbox" id="selectAll" onchange="toggleSelectAll(this)"></th>
            <th>#</th>
            <th onclick="sortTable(2)">Company <span class="sort-arrow">⇅</span></th>
            <th onclick="sortTable(3)">Domain <span class="sort-arrow">⇅</span></th>
            <th onclick="sortTable(4)">DR <span class="sort-arrow">⇅</span></th>
            <th onclick="sortTable(5)">Traffic <span class="sort-arrow">⇅</span></th>
            <th onclick="sortTable(6)">Contact <span class="sort-arrow">⇅</span></th>
            <th onclick="sortTable(7)">Email <span class="sort-arrow">⇅</span></th>
            <th onclick="sortTable(8)">Title <span class="sort-arrow">⇅</span></th>
            <th onclick="sortTable(9)">Video Source <span class="sort-arrow">⇅</span></th>
            <th onclick="sortTable(10)">Dubbed To <span class="sort-arrow">⇅</span></th>
            <th onclick="sortTable(11)">Trim <span class="sort-arrow">⇅</span></th>
            <th>Synthesia</th>
            <th>GIF</th>
            <th onclick="sortTable(14)">Category <span class="sort-arrow">⇅</span></th>
            <th onclick="sortTable(15)">Status <span class="sort-arrow">⇅</span></th>
            <th onclick="sortTable(16)">Matched Customer <span class="sort-arrow">⇅</span></th>
            <th onclick="sortTable(17)">Outreached <span class="sort-arrow">⇅</span></th>
        </tr>
        <tr class="filter-header">
            <td></td>
            <td></td>
            <td><input class="col-filter" data-col="2" onkeyup="applyFilters()" placeholder="Filter"></td>
            <td><input class="col-filter" data-col="3" onkeyup="applyFilters()" placeholder="Filter"></td>
            <td><input class="col-filter" data-col="4" onkeyup="applyFilters()" placeholder="Filter"></td>
            <td><input class="col-filter" data-col="5" onkeyup="applyFilters()" placeholder="Filter"></td>
            <td><select class="col-filter" data-col="6" onchange="applyFilters()"><option value="">All</option><option value="__nonempty__">Has contact</option><option value="__empty__">No contact</option></select></td>
            <td><select class="col-filter" data-col="7" onchange="applyFilters()"><option value="">All</option><option value="__nonempty__">Has email</option><option value="__empty__">No email</option></select></td>
            <td><input class="col-filter" data-col="8" onkeyup="applyFilters()" placeholder="Filter"></td>
            <td><input class="col-filter" data-col="9" onkeyup="applyFilters()" placeholder="Filter"></td>
            <td><select class="col-filter" data-col="10" onchange="applyFilters()"><option value="">All</option><option value="es">es</option><option value="en">en</option></select></td>
            <td></td>
            <td><select class="col-filter" data-col="12" onchange="applyFilters()"><option value="">All</option><option value="__nonempty__">Has link</option><option value="__empty__">No link</option></select></td>
            <td></td>
            <td><input class="col-filter" data-col="14" onkeyup="applyFilters()" placeholder="Filter"></td>
            <td><input class="col-filter" data-col="15" onkeyup="applyFilters()" placeholder="Filter"></td>
            <td><input class="col-filter" data-col="16" onkeyup="applyFilters()" placeholder="Filter"></td>
            <td><select class="col-filter" data-col="17" onchange="applyFilters()"><option value="">All</option><option value="__checked__">Outreached</option><option value="__unchecked__">Not outreached</option></select></td>
        </tr>
    </thead>
    <tbody>{rows_html}</tbody>
</table>
<div style="display:flex; justify-content:center; gap:12px; margin:20px 0;">
    <button class="export-btn" onclick="window.location.href='/export'">Export CSV</button>
    <button class="export-btn" style="background:#7b1fa2;" onclick="dubSelected()">Dub Selected Videos</button>
    <span id="dub-status" style="align-self:center; font-size:14px; color:#555;"></span>
</div>

<script>
let sortCol = -1, sortAsc = true;

function sortTable(col) {{
    const table = document.getElementById('dashTable');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));

    if (sortCol === col) {{ sortAsc = !sortAsc; }} else {{ sortCol = col; sortAsc = true; }}

    const numericCols = [4, 5];
    rows.sort((a, b) => {{
        let aVal = a.cells[col].textContent.trim();
        let bVal = b.cells[col].textContent.trim();
        if (numericCols.includes(col)) {{
            aVal = parseFloat(aVal.replace(/,/g, '')) || 0;
            bVal = parseFloat(bVal.replace(/,/g, '')) || 0;
            return sortAsc ? aVal - bVal : bVal - aVal;
        }}
        return sortAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    }});

    rows.forEach(r => tbody.appendChild(r));
}}

function filterTable() {{
    const query = document.getElementById('searchBox').value.toLowerCase();
    applyFilters(query);
}}

function applyFilters(searchOverride) {{
    const searchQuery = (searchOverride !== undefined ? searchOverride : document.getElementById('searchBox').value).toLowerCase();
    const filters = document.querySelectorAll('.col-filter');
    const rows = document.getElementById('dashTable').querySelector('tbody').querySelectorAll('tr');

    rows.forEach(row => {{
        let show = true;

        // Global search
        if (searchQuery && !row.textContent.toLowerCase().includes(searchQuery)) {{
            show = false;
        }}

        // Per-column filters
        if (show) {{
            filters.forEach(f => {{
                const col = parseInt(f.dataset.col);
                const val = f.value;
                if (!val) return;
                const cell = row.cells[col];
                if (!cell) return;
                const cellText = cell.textContent.trim().toLowerCase();

                if (val === '__nonempty__') {{
                    if (!cellText) show = false;
                }} else if (val === '__empty__') {{
                    if (cellText) show = false;
                }} else if (val === '__checked__') {{
                    const cb = cell.querySelector('input[type=checkbox]');
                    if (!cb || !cb.checked) show = false;
                }} else if (val === '__unchecked__') {{
                    const cb = cell.querySelector('input[type=checkbox]');
                    if (!cb || cb.checked) show = false;
                }} else {{
                    if (!cellText.includes(val.toLowerCase())) show = false;
                }}
            }});
        }}

        row.style.display = show ? '' : 'none';
    }});
}}

function toggleOutreached(cb) {{
    const domain = cb.dataset.domain;
    const checked = cb.checked;
    fetch('/api/outreached', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{domain: domain, outreached: checked}})
    }});
}}

function toggleSelectAll(cb) {{
    document.querySelectorAll('.select-cb').forEach(c => c.checked = cb.checked);
}}

function dubSelected() {{
    const selected = Array.from(document.querySelectorAll('.select-cb:checked')).map(cb => cb.dataset.domain);
    if (selected.length === 0) {{
        alert('No rows selected');
        return;
    }}
    if (!confirm('Dub ' + selected.length + ' videos with Synthesia?')) return;
    const status = document.getElementById('dub-status');
    status.textContent = 'Starting dubbing for ' + selected.length + ' videos...';
    fetch('/api/dub-batch', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{domains: selected}})
    }}).then(r => r.json()).then(data => {{
        if (data.ok) {{
            status.textContent = 'Dubbing started for ' + data.count + ' videos. This will take 15-30 min. Refresh page to see results.';
        }} else {{
            status.textContent = 'Error: ' + (data.error || 'unknown');
        }}
    }}).catch(err => {{
        status.textContent = 'Error: ' + err;
    }});
}}
</script>
</body></html>'''


class ReviewHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        min_dr = int(params.get('min_dr', [0])[0])

        if parsed.path == '/' or parsed.path == '/review':
            page = int(params.get('page', [1])[0])
            per_page = 20
            data, total = get_review_data(min_dr=min_dr, page=page, per_page=per_page)
            html = build_html(data, min_dr=min_dr, page=page, per_page=per_page, total=total)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode())
        elif parsed.path == '/dashboard':
            html = build_dashboard_html()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode())
        elif parsed.path == '/export':
            self._export_approved()
        elif parsed.path == '/api/stats':
            decisions = _load_review_decisions()
            approved = [d for d, v in decisions.items() if v['status'] == 'approved']
            rejected = [d for d, v in decisions.items() if v['status'] == 'rejected']
            self._json_response({
                'approved': len(approved),
                'rejected': len(rejected),
                'approved_companies': [{'domain': d, 'name': decisions[d].get('name','')} for d in approved],
            })
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(content_length)) if content_length else {}

        if self.path == '/api/approve':
            domain = body.get('domain')
            _save_review_decision(domain, 'approved', extra={
                'selected_video_url': body.get('selected_video_url', ''),
                'selected_video_type': body.get('selected_video_type', ''),
                'video_source': body.get('video_source', 'unknown'),
                'trim_start': body.get('trim_start', 0),
                'trim_end': body.get('trim_end', 30),
            })
            decisions = _load_review_decisions()
            approved_count = sum(1 for v in decisions.values() if v['status'] == 'approved')
            rejected_count = sum(1 for v in decisions.values() if v['status'] == 'rejected')
            self._json_response({'ok': True, 'approved': approved_count, 'rejected': rejected_count})

        elif self.path == '/api/scan':
            domain = body.get('domain', '')
            url = body.get('url', '')
            try:
                videos = _scan_with_headless(url)
                # Save to page_videos.json
                page_data = {}
                if os.path.exists(PAGE_VIDEOS_PATH):
                    with open(PAGE_VIDEOS_PATH) as pf:
                        page_data = json.load(pf)
                page_data[domain] = {'page_url': url, 'videos': videos, 'method': 'headless'}
                with open(PAGE_VIDEOS_PATH, 'w') as pf:
                    json.dump(page_data, pf, indent=2)
                self._json_response({'ok': True, 'videos': videos})
            except Exception as e:
                self._json_response({'ok': False, 'error': str(e), 'videos': []})

        elif self.path == '/api/dub-batch':
            domains = body.get('domains', [])
            if not domains:
                self._json_response({'ok': False, 'error': 'No domains'})
            else:
                # Launch dubbing in background thread
                import threading
                def run_dub():
                    import subprocess
                    subprocess.Popen(
                        ['/usr/local/bin/python3.12', 'batch_dub.py', '--domains', ','.join(domains)],
                        cwd=os.path.dirname(os.path.abspath(__file__)),
                        env={**os.environ, 'PATH': os.path.expanduser('~/bin') + ':' + os.environ.get('PATH', '')},
                    )
                t = threading.Thread(target=run_dub)
                t.start()
                self._json_response({'ok': True, 'count': len(domains)})

        elif self.path == '/api/outreached':
            domain = body.get('domain')
            outreached = body.get('outreached', False)
            decisions = _load_review_decisions()
            if domain in decisions:
                decisions[domain]['outreached'] = outreached
                with open(REVIEW_FILE, 'w') as f:
                    json.dump(decisions, f, indent=2)
            self._json_response({'ok': True})

        elif self.path == '/api/update-domain':
            old_domain = body.get('old_domain', '').strip()
            new_domain = body.get('new_domain', '').strip()
            if not old_domain or not new_domain:
                self._json_response({'ok': False, 'error': 'missing domain'})
                return
            try:
                # Update DB
                conn = get_conn()
                conn.execute('PRAGMA foreign_keys=OFF')
                conn.execute('UPDATE companies SET domain = ?, website_url = ? WHERE domain = ?',
                             (new_domain, f'https://{new_domain}', old_domain))
                conn.execute('UPDATE company_videos SET domain = ? WHERE domain = ?', (new_domain, old_domain))
                conn.execute('UPDATE discovery_sources SET domain = ? WHERE domain = ?', (new_domain, old_domain))
                conn.execute('UPDATE contacts SET domain = ? WHERE domain = ?', (new_domain, old_domain))
                conn.commit()
                conn.close()
                # Update CSV
                import csv as csv_mod
                if os.path.exists(CSV_PATH):
                    with open(CSV_PATH, encoding='utf-8') as f:
                        reader = csv_mod.DictReader(f)
                        csv_rows = list(reader)
                        fnames = reader.fieldnames
                    for row in csv_rows:
                        if row.get('Domain') == old_domain:
                            row['Domain'] = new_domain
                            row['Website URL'] = f'https://{new_domain}'
                    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
                        writer = csv_mod.DictWriter(f, fieldnames=fnames)
                        writer.writeheader()
                        writer.writerows(csv_rows)
                # Update review decisions (rename key if exists)
                decisions = _load_review_decisions()
                if old_domain in decisions:
                    decisions[new_domain] = decisions.pop(old_domain)
                    decisions[new_domain]['website_url'] = f'https://{new_domain}'
                    with open(REVIEW_FILE, 'w') as f:
                        json.dump(decisions, f, indent=2)
                # Also update page_videos.json if present
                if os.path.exists(PAGE_VIDEOS_PATH):
                    with open(PAGE_VIDEOS_PATH) as f:
                        pv = json.load(f)
                    if old_domain in pv:
                        pv[new_domain] = pv.pop(old_domain)
                        with open(PAGE_VIDEOS_PATH, 'w') as f:
                            json.dump(pv, f, indent=2)
                self._json_response({'ok': True})
            except Exception as e:
                self._json_response({'ok': False, 'error': str(e)})

        elif self.path == '/api/reject':
            domain = body.get('domain')
            _save_review_decision(domain, 'rejected')
            decisions = _load_review_decisions()
            approved_count = sum(1 for v in decisions.values() if v['status'] == 'approved')
            rejected_count = sum(1 for v in decisions.values() if v['status'] == 'rejected')
            self._json_response({'ok': True, 'approved': approved_count, 'rejected': rejected_count})

        else:
            self.send_response(404)
            self.end_headers()

    def _export_approved(self):
        """Export approved companies as CSV for Lusha."""
        conn = get_conn()
        rows = conn.execute('''
            SELECT DISTINCT c.domain, c.name, c.website_url, c.category,
                   c.domain_rating, c.org_traffic, c.org_keywords,
                   c.youtube_channel_url
            FROM companies c
            JOIN company_videos cv ON c.domain = cv.domain
            WHERE cv.review_status = 'approved'
            ORDER BY c.domain_rating DESC NULLS LAST
        ''').fetchall()
        conn.close()

        output = "Company Name,Domain,Website,Category,Domain Rating,Organic Traffic,YouTube Channel\n"
        for r in rows:
            r = dict(r)
            output += f"\"{r['name']}\",{r['domain']},{r.get('website_url','')},{r.get('category','')},{r.get('domain_rating') or ''},{r.get('org_traffic') or ''},{r.get('youtube_channel_url','')}\n"

        self.send_response(200)
        self.send_header('Content-Type', 'text/csv')
        self.send_header('Content-Disposition', 'attachment; filename="approved_for_lusha.csv"')
        self.end_headers()
        self.wfile.write(output.encode())

    def _json_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass


def export_approved_csv():
    """Export approved companies to CSV for Lusha enrichment."""
    csv_data = _load_csv_data()
    decisions = _load_review_decisions()

    approved = [csv_data[d] for d in decisions if decisions[d]['status'] == 'approved' and d in csv_data]
    approved.sort(key=lambda c: (c.get('domain_rating') or 0), reverse=True)

    if not approved:
        print("No approved companies yet.")
        return

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "approved_for_lusha.csv")
    fieldnames = ["Company Name", "Domain", "Website", "Category", "Domain Rating", "Organic Traffic", "Organic Keywords", "YouTube Channel"]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for comp in approved:
            writer.writerow({
                "Company Name": comp['name'],
                "Domain": comp['domain'],
                "Website": comp.get('website_url', ''),
                "Category": comp.get('category', ''),
                "Domain Rating": comp.get('domain_rating', ''),
                "Organic Traffic": comp.get('org_traffic', ''),
                "Organic Keywords": comp.get('org_keywords', ''),
                "YouTube Channel": comp.get('youtube_channel_url', ''),
            })

    print(f"Exported {len(approved)} approved companies to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="SaaS Video Review")
    parser.add_argument("--port", type=int, default=8889)
    parser.add_argument("--min-dr", type=int, default=0)
    parser.add_argument("--export-approved", action="store_true", help="Export approved companies to CSV")
    args = parser.parse_args()

    if args.export_approved:
        export_approved_csv()
        return

    server = HTTPServer(('localhost', args.port), ReviewHandler)
    url = f"http://localhost:{args.port}?min_dr={args.min_dr}"
    print(f"\n  Review server at {url}")
    print(f"  Export approved: http://localhost:{args.port}/export")
    print(f"  Press Ctrl+C to stop\n")
    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
