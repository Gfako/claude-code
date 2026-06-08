#!/usr/bin/env python3
"""
review_server.py — Local web-based video review interface for SaaS companies.

Shows companies with discovered videos. Embed YouTube videos inline,
link to non-YouTube videos. Approve/reject per video.

Usage:
    python3 review_server.py
    python3 review_server.py --port 8080
"""

import argparse
import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

import db
from utils import log


def get_review_data(filter_status="pending"):
    """Get companies with videos for review."""
    with db.get_conn() as conn:
        status_filter = ""
        if filter_status and filter_status != "all":
            status_filter = f"AND v.review_status = '{filter_status}'"

        rows = conn.execute(f"""
            SELECT c.domain, c.name, c.website_url, c.category,
                   c.domain_rating, c.org_traffic, c.org_keywords,
                   c.has_youtube_channel, c.youtube_channel_url,
                   c.youtube_subscriber_count,
                   v.id as video_id, v.video_type, v.video_url,
                   v.title as video_title, v.detection_method,
                   v.review_status
            FROM companies c
            JOIN company_videos v ON c.domain = v.domain
            WHERE 1=1 {status_filter}
            ORDER BY c.domain_rating DESC NULLS LAST,
                     c.org_traffic DESC NULLS LAST,
                     c.domain, v.id
        """).fetchall()

        # Group by company
        companies = {}
        for row in rows:
            r = dict(row)
            domain = r["domain"]
            if domain not in companies:
                companies[domain] = {
                    "domain": domain,
                    "name": r["name"],
                    "website_url": r["website_url"],
                    "category": r["category"],
                    "domain_rating": r["domain_rating"],
                    "org_traffic": r["org_traffic"],
                    "org_keywords": r["org_keywords"],
                    "has_youtube_channel": r["has_youtube_channel"],
                    "youtube_channel_url": r["youtube_channel_url"],
                    "youtube_subscriber_count": r["youtube_subscriber_count"],
                    "videos": [],
                }
            companies[domain]["videos"].append({
                "video_id": r["video_id"],
                "video_type": r["video_type"],
                "video_url": r["video_url"],
                "title": r["video_title"],
                "detection_method": r["detection_method"],
                "review_status": r["review_status"],
            })

    return list(companies.values())


def _youtube_embed_url(video_url):
    """Convert a YouTube URL to an embed URL."""
    if not video_url:
        return None
    if "youtube.com/watch?v=" in video_url:
        vid_id = video_url.split("v=")[1].split("&")[0]
        return f"https://www.youtube.com/embed/{vid_id}"
    if "youtu.be/" in video_url:
        vid_id = video_url.split("youtu.be/")[1].split("?")[0]
        return f"https://www.youtube.com/embed/{vid_id}"
    return None


def build_html(data):
    """Generate the review HTML page."""
    cards = ""
    total_pending = sum(1 for c in data for v in c["videos"] if v["review_status"] == "pending")

    for comp in data:
        dr = comp.get("domain_rating") or 0
        traffic = comp.get("org_traffic") or 0
        keywords = comp.get("org_keywords") or 0
        yt_subs = comp.get("youtube_subscriber_count") or 0

        video_items = ""
        for v in comp["videos"]:
            embed_url = _youtube_embed_url(v["video_url"])
            is_youtube = v["video_type"] in ("youtube_channel", "youtube_embed") and embed_url
            status_class = v["review_status"]

            player_html = ""
            if is_youtube:
                player_html = f'''<iframe src="{embed_url}" frameborder="0" allowfullscreen
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    style="width:100%;height:300px;border-radius:8px;"></iframe>'''
            else:
                player_html = f'''<a href="{v['video_url']}" target="_blank" class="video-link">
                    Open video: {v['video_url'][:80]}</a>'''

            video_items += f'''
            <div class="video-item {status_class}" id="video-{v['video_id']}">
                <div class="video-meta">
                    <span class="video-title">{(v['title'] or 'Untitled')[:80]}</span>
                    <span class="badge method">{v['detection_method']}</span>
                    <span class="badge type">{v['video_type']}</span>
                    <span class="badge status-{v['review_status']}">{v['review_status']}</span>
                </div>
                <div class="video-player">{player_html}</div>
                <div class="video-actions">
                    <button class="btn approve" onclick="reviewVideo({v['video_id']}, 'approved')">Approve</button>
                    <button class="btn reject" onclick="reviewVideo({v['video_id']}, 'rejected')">Reject</button>
                </div>
            </div>'''

        cards += f'''
        <div class="card" id="card-{comp['domain']}">
            <div class="card-header">
                <div class="company-info">
                    <h2><a href="{comp.get('website_url','')}" target="_blank">{comp['name']}</a></h2>
                    <div class="meta">
                        <span class="badge domain">{comp['domain']}</span>
                        <span class="badge cat">{comp.get('category','')}</span>
                        <span class="badge dr">DR {dr:.0f}</span>
                        <span class="badge traffic">{traffic:,}/mo</span>
                        <span class="badge kw">{keywords:,} kw</span>
                        {'<span class="badge yt">' + f"{yt_subs:,} subs" + '</span>' if yt_subs else ''}
                        {'<a href="' + (comp.get("youtube_channel_url") or "") + '" target="_blank" class="badge yt-link">YouTube</a>' if comp.get("youtube_channel_url") else ''}
                    </div>
                </div>
            </div>
            <div class="card-body">
                {video_items}
            </div>
        </div>'''

    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Video Review — SaaS Outreach</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f0f0f; color: #e0e0e0; padding: 20px; }}
    h1 {{ text-align: center; margin: 20px 0 10px; color: #fff; font-size: 24px; }}
    .subtitle {{ text-align: center; color: #888; margin-bottom: 20px; }}
    .filters {{ text-align: center; margin-bottom: 20px; }}
    .filters a {{ color: #4fc3f7; margin: 0 10px; text-decoration: none; font-size: 14px; }}
    .filters a:hover {{ color: #fff; }}
    .filters a.active {{ color: #fff; font-weight: bold; border-bottom: 2px solid #4fc3f7; }}
    .counter {{ text-align: center; margin-bottom: 20px; padding: 10px; background: #1a1a2e; border-radius: 8px; font-size: 16px; }}
    .counter span {{ margin: 0 15px; }}
    .counter .approved {{ color: #4caf50; }}
    .counter .rejected {{ color: #f44336; }}
    .counter .pending {{ color: #ffc107; }}
    .card {{ background: #1a1a1a; border-radius: 12px; margin-bottom: 24px; overflow: hidden; border: 1px solid #333; }}
    .card-header {{ padding: 16px 20px; border-bottom: 1px solid #333; }}
    .company-info h2 {{ font-size: 18px; margin-bottom: 8px; }}
    .company-info h2 a {{ color: #fff; text-decoration: none; }}
    .company-info h2 a:hover {{ color: #4fc3f7; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .badge {{ padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; }}
    .domain {{ background: #263238; color: #80cbc4; }}
    .cat {{ background: #1a237e; color: #90caf9; }}
    .dr {{ background: #1b5e20; color: #a5d6a7; }}
    .traffic {{ background: #4a148c; color: #ce93d8; }}
    .kw {{ background: #e65100; color: #ffcc80; }}
    .yt {{ background: #b71c1c; color: #ef9a9a; }}
    .yt-link {{ background: #b71c1c; color: #ef9a9a; text-decoration: none; }}
    .method {{ background: #37474f; color: #b0bec5; }}
    .type {{ background: #424242; color: #e0e0e0; }}
    .status-pending {{ background: #f57f17; color: #fff; }}
    .status-approved {{ background: #2e7d32; color: #fff; }}
    .status-rejected {{ background: #c62828; color: #fff; }}
    .card-body {{ padding: 16px 20px; }}
    .video-item {{ margin-bottom: 16px; padding: 12px; background: #222; border-radius: 8px; border: 1px solid #333; transition: opacity 0.3s; }}
    .video-item.approved {{ opacity: 0.4; }}
    .video-item.rejected {{ opacity: 0.3; }}
    .video-meta {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 10px; }}
    .video-title {{ font-weight: 600; font-size: 14px; flex: 1; }}
    .video-player {{ margin-bottom: 10px; }}
    .video-link {{ color: #4fc3f7; text-decoration: none; font-size: 13px; }}
    .video-link:hover {{ color: #fff; }}
    .video-actions {{ display: flex; gap: 10px; }}
    .btn {{ padding: 8px 24px; border: none; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; }}
    .btn.approve {{ background: #4caf50; color: #fff; }}
    .btn.approve:hover {{ background: #66bb6a; }}
    .btn.reject {{ background: #f44336; color: #fff; }}
    .btn.reject:hover {{ background: #ef5350; }}
</style>
</head>
<body>
<h1>SaaS Video Review</h1>
<p class="subtitle">{len(data)} companies with videos</p>

<div class="filters">
    <a href="/?filter=pending" class="active">Pending</a>
    <a href="/?filter=approved">Approved</a>
    <a href="/?filter=rejected">Rejected</a>
    <a href="/?filter=all">All</a>
</div>

<div class="counter">
    <span class="pending" id="cnt-pending">Pending: {total_pending}</span>
    <span class="approved" id="cnt-approved">Approved: 0</span>
    <span class="rejected" id="cnt-rejected">Rejected: 0</span>
</div>

{cards}

<script>
let approved = 0, rejected = 0, pending = {total_pending};

function updateCounters() {{
    document.getElementById('cnt-approved').textContent = 'Approved: ' + approved;
    document.getElementById('cnt-rejected').textContent = 'Rejected: ' + rejected;
    document.getElementById('cnt-pending').textContent = 'Pending: ' + pending;
}}

function reviewVideo(videoId, status) {{
    fetch('/api/review', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{video_id: videoId, status: status}})
    }}).then(r => r.json()).then(data => {{
        const el = document.getElementById('video-' + videoId);
        if (el) {{
            el.classList.add(status);
            // Update badge
            const badges = el.querySelectorAll('.badge');
            badges.forEach(b => {{
                if (b.classList.contains('status-pending')) {{
                    b.classList.remove('status-pending');
                    b.classList.add('status-' + status);
                    b.textContent = status;
                }}
            }});
            // Disable buttons
            el.querySelectorAll('.btn').forEach(b => b.disabled = true);
        }}
        if (status === 'approved') {{ approved++; pending--; }}
        if (status === 'rejected') {{ rejected++; pending--; }}
        updateCounters();
    }});
}}
</script>
</body>
</html>'''


class ReviewHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/'):
            # Parse filter param
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            filter_status = params.get("filter", ["pending"])[0]

            data = get_review_data(filter_status=filter_status)
            html = build_html(data)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(content_length)) if content_length else {}

        if self.path == '/api/review':
            video_id = body.get('video_id')
            status = body.get('status', 'pending')

            if video_id and status in ('approved', 'rejected', 'pending'):
                db.update_video_review(video_id, status)
                log.info("Video %s: %s", video_id, status)
                self._json_response({'ok': True})
            else:
                self._json_response({'ok': False, 'error': 'invalid params'})
        else:
            self.send_response(404)
            self.end_headers()

    def _json_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass  # Suppress default access logs


def main():
    parser = argparse.ArgumentParser(description="SaaS Video Review Web Interface")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    server = HTTPServer(('localhost', args.port), ReviewHandler)
    url = f"http://localhost:{args.port}"
    print(f"\n  Review server running at {url}")
    print(f"  Press Ctrl+C to stop\n")
    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
