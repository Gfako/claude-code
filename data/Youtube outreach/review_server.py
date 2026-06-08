#!/usr/bin/env python3
"""
review_server.py — Local web-based video review interface.

Starts a local HTTP server with an HTML page showing embedded YouTube videos
for each channel. Approve/reject with one click, set custom time ranges for dubbing.

Usage:
    python3 review_server.py
    python3 review_server.py --port 8080
"""

import argparse
import json
import os
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from datetime import datetime

import db
from utils import log


def get_review_data():
    """Get all channels with website + pending dubbed videos."""
    with db.get_conn() as conn:
        channels = conn.execute('''
            SELECT c.channel_id, c.name, c.custom_url, c.subscriber_count,
                   ct.website_url, ct.website_dr, ct.website_traffic,
                   ct.email_from_desc, ct.email_from_about, ct.email_enriched
            FROM channels c
            JOIN contacts ct ON c.channel_id = ct.channel_id
            WHERE c.has_dubbing = 1
              AND ct.website_url IS NOT NULL AND ct.website_url != ''
              AND c.channel_id IN (
                  SELECT DISTINCT channel_id FROM videos
                  WHERE has_auto_dub = 1 AND review_status = 'pending'
              )
            ORDER BY ct.website_dr DESC NULLS LAST, c.subscriber_count DESC
        ''').fetchall()

        result = []
        for ch in channels:
            ch = dict(ch)
            videos = conn.execute('''
                SELECT video_id, title, duration_seconds, default_audio_language
                FROM videos
                WHERE channel_id = ? AND has_auto_dub = 1 AND review_status = 'pending'
                ORDER BY duration_seconds ASC
            ''', (ch['channel_id'],)).fetchall()
            ch['videos'] = [dict(v) for v in videos]
            result.append(ch)

    return result


def build_html(data):
    """Generate the review HTML page."""
    cards = ""
    for ch in data:
        dr = ch.get('website_dr') or 0
        traffic = ch.get('website_traffic') or 0
        email = ch.get('email_enriched') or ch.get('email_from_about') or ch.get('email_from_desc') or ''
        custom = ch.get('custom_url', '')
        ch_url = f"https://www.youtube.com/{custom}" if custom else f"https://www.youtube.com/channel/{ch['channel_id']}"

        video_options = ""
        for v in ch['videos']:
            d = v.get('duration_seconds') or 0
            mins = d // 60
            secs = d % 60
            lang = v.get('default_audio_language') or '?'
            video_options += f'<option value="{v["video_id"]}" data-duration="{d}" data-lang="{lang}">{v["title"][:70]} ({mins}:{secs:02d}) [{lang}]</option>\n'

        first_vid = ch['videos'][0]['video_id'] if ch['videos'] else ''
        first_dur = ch['videos'][0].get('duration_seconds', 0) if ch['videos'] else 0

        cards += f'''
        <div class="card" id="card-{ch['channel_id']}" data-channel="{ch['channel_id']}">
            <div class="card-header">
                <div class="channel-info">
                    <h2><a href="{ch_url}" target="_blank">{ch['name']}</a></h2>
                    <div class="meta">
                        <span class="badge subs">{ch['subscriber_count']:,} subs</span>
                        <span class="badge dr">DR {dr:.0f}</span>
                        <span class="badge traffic">{traffic:,}/mo</span>
                        <a href="{ch.get('website_url','')}" target="_blank" class="badge website">{ch.get('website_url','')[:40]}</a>
                        {'<span class="badge email">'+email+'</span>' if email else ''}
                    </div>
                </div>
            </div>
            <div class="card-body">
                <div class="video-select">
                    <label>Video:</label>
                    <select onchange="changeVideo(this, '{ch['channel_id']}')">{video_options}</select>
                </div>
                <div class="player-container">
                    <div id="player-{ch['channel_id']}" class="player"
                         data-video="{first_vid}">
                        <iframe src="https://www.youtube.com/embed/{first_vid}"
                                frameborder="0" allowfullscreen
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture">
                        </iframe>
                    </div>
                </div>
                <div class="trim-controls">
                    <label>Dub from</label>
                    <input type="text" class="time-input-mm-ss" id="start-{ch['channel_id']}" value="0:00">
                    <label>&nbsp;to&nbsp;</label>
                    <input type="text" class="time-input-mm-ss" id="end-{ch['channel_id']}" value="{min(30, first_dur) // 60}:{min(30, first_dur) % 60:02d}">
                    <span class="trim-hint" id="hint-{ch['channel_id']}">(video length: {first_dur // 60}:{first_dur % 60:02d})</span>
                </div>
                <div class="actions">
                    <button class="btn approve" onclick="approve('{ch['channel_id']}')">Approve Video</button>
                    <button class="btn reject-video" onclick="rejectVideo('{ch['channel_id']}')">Reject Video</button>
                    <button class="btn reject" onclick="rejectChannel('{ch['channel_id']}')">Reject Channel</button>
                </div>
            </div>
            <div class="status-msg" id="status-{ch['channel_id']}"></div>
        </div>
        '''

    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Video Review — YouTube Outreach</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f0f0f; color: #e0e0e0; padding: 20px; }}
    h1 {{ text-align: center; margin: 20px 0 10px; color: #fff; font-size: 24px; }}
    .subtitle {{ text-align: center; color: #888; margin-bottom: 30px; }}
    .counter {{ text-align: center; margin-bottom: 20px; padding: 10px; background: #1a1a2e; border-radius: 8px; font-size: 16px; }}
    .counter span {{ margin: 0 15px; }}
    .counter .approved {{ color: #4caf50; }}
    .counter .rejected {{ color: #f44336; }}
    .counter .pending {{ color: #ffc107; }}
    .card {{ background: #1a1a1a; border-radius: 12px; margin-bottom: 24px; overflow: hidden; border: 1px solid #333; transition: opacity 0.3s; }}
    .card.done {{ opacity: 0.3; pointer-events: none; }}
    .card-header {{ padding: 16px 20px; border-bottom: 1px solid #333; }}
    .channel-info h2 {{ font-size: 18px; margin-bottom: 8px; }}
    .channel-info h2 a {{ color: #fff; text-decoration: none; }}
    .channel-info h2 a:hover {{ color: #4fc3f7; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .badge {{ padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; }}
    .subs {{ background: #1a237e; color: #90caf9; }}
    .dr {{ background: #1b5e20; color: #a5d6a7; }}
    .traffic {{ background: #4a148c; color: #ce93d8; }}
    .website {{ background: #263238; color: #80cbc4; text-decoration: none; }}
    .website:hover {{ color: #fff; }}
    .email {{ background: #bf360c; color: #ffab91; }}
    .card-body {{ padding: 16px 20px; }}
    .video-select {{ margin-bottom: 12px; }}
    .video-select label {{ font-size: 13px; color: #aaa; margin-right: 8px; }}
    .video-select select {{ width: 80%; padding: 6px 10px; background: #2a2a2a; color: #fff; border: 1px solid #444; border-radius: 6px; font-size: 13px; }}
    .player-container {{ margin-bottom: 12px; }}
    .player iframe {{ width: 100%; height: 360px; border-radius: 8px; }}
    .trim-controls {{ display: flex; align-items: center; gap: 8px; margin-bottom: 16px; padding: 10px; background: #222; border-radius: 8px; }}
    .trim-controls label {{ font-size: 13px; color: #aaa; }}
    .time-input-mm-ss {{ width: 60px; padding: 6px; background: #333; color: #fff; border: 1px solid #555; border-radius: 4px; text-align: center; font-size: 14px; }}
    .trim-hint {{ font-size: 12px; color: #666; }}
    .actions {{ display: flex; gap: 12px; }}
    .btn {{ padding: 10px 32px; border: none; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; transition: all 0.2s; }}
    .btn.approve {{ background: #4caf50; color: #fff; }}
    .btn.approve:hover {{ background: #66bb6a; transform: scale(1.02); }}
    .btn.reject-video {{ background: #ff9800; color: #fff; }}
    .btn.reject-video:hover {{ background: #ffa726; transform: scale(1.02); }}
    .btn.reject {{ background: #f44336; color: #fff; }}
    .btn.reject:hover {{ background: #ef5350; transform: scale(1.02); }}
    .status-msg {{ padding: 8px 20px; font-size: 14px; font-weight: 600; display: none; }}
    .status-msg.show {{ display: block; }}
    .status-msg.approved {{ background: #1b5e20; color: #a5d6a7; }}
    .status-msg.rejected {{ background: #b71c1c; color: #ef9a9a; }}
</style>
</head>
<body>
<h1>Video Review</h1>
<p class="subtitle">{len(data)} channels with website + dubbed videos</p>
<div class="counter">
    <span class="approved" id="cnt-approved">Approved: 0</span>
    <span class="rejected" id="cnt-rejected">Rejected: 0</span>
    <span class="pending" id="cnt-pending">Pending: {len(data)}</span>
</div>

{cards}

<script>
let approved = 0, rejected = 0, pending = {len(data)};

function updateCounters() {{
    document.getElementById('cnt-approved').textContent = 'Approved: ' + approved;
    document.getElementById('cnt-rejected').textContent = 'Rejected: ' + rejected;
    document.getElementById('cnt-pending').textContent = 'Pending: ' + pending;
}}

function toMMSS(totalSec) {{
    return Math.floor(totalSec/60) + ':' + String(totalSec%60).padStart(2,'0');
}}
function parseMMSS(str) {{
    const parts = str.split(':');
    if (parts.length === 2) return parseInt(parts[0])*60 + parseInt(parts[1]);
    return parseInt(str) || 0;
}}
function changeVideo(sel, chId) {{
    const vid = sel.value;
    const opt = sel.options[sel.selectedIndex];
    const dur = parseInt(opt.dataset.duration) || 60;
    const iframe = document.querySelector('#player-' + chId + ' iframe');
    iframe.src = 'https://www.youtube.com/embed/' + vid;
    document.getElementById('start-' + chId).value = '0:00';
    document.getElementById('end-' + chId).value = toMMSS(Math.min(30, dur));
    document.getElementById('hint-' + chId).textContent = '(video length: ' + toMMSS(dur) + ')';
}}

function approve(chId) {{
    const card = document.getElementById('card-' + chId);
    const sel = card.querySelector('select');
    const videoId = sel.value;
    const start = parseMMSS(document.getElementById('start-' + chId).value);
    const end = parseMMSS(document.getElementById('end-' + chId).value);

    fetch('/api/approve', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{channel_id: chId, video_id: videoId, start: start, end: end}})
    }}).then(r => r.json()).then(data => {{
        const msg = document.getElementById('status-' + chId);
        msg.textContent = 'Approved: ' + videoId + ' (' + toMMSS(start) + ' - ' + toMMSS(end) + ')';
        msg.className = 'status-msg show approved';
        card.classList.add('done');
        approved++; pending--;
        updateCounters();
        // Scroll to next card
        const next = card.nextElementSibling;
        if (next && next.classList.contains('card')) next.scrollIntoView({{behavior: 'smooth', block: 'start'}});
    }});
}}

function rejectVideo(chId) {{
    const card = document.getElementById('card-' + chId);
    const sel = card.querySelector('select');
    const videoId = sel.value;

    fetch('/api/reject-video', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{channel_id: chId, video_id: videoId}})
    }}).then(r => r.json()).then(data => {{
        // Remove the rejected option from dropdown
        sel.remove(sel.selectedIndex);
        if (sel.options.length > 0) {{
            // Show next video
            sel.selectedIndex = 0;
            changeVideo(sel, chId);
        }} else {{
            // No more videos — grey out
            const msg = document.getElementById('status-' + chId);
            msg.textContent = 'All videos rejected';
            msg.className = 'status-msg show rejected';
            card.classList.add('done');
            rejected++; pending--;
            updateCounters();
            const next = card.nextElementSibling;
            if (next && next.classList.contains('card')) next.scrollIntoView({{behavior: 'smooth', block: 'start'}});
        }}
    }});
}}

function rejectChannel(chId) {{
    fetch('/api/reject', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{channel_id: chId}})
    }}).then(r => r.json()).then(data => {{
        const card = document.getElementById('card-' + chId);
        const msg = document.getElementById('status-' + chId);
        msg.textContent = 'Rejected — all videos removed';
        msg.className = 'status-msg show rejected';
        card.classList.add('done');
        rejected++; pending--;
        updateCounters();
        const next = card.nextElementSibling;
        if (next && next.classList.contains('card')) next.scrollIntoView({{behavior: 'smooth', block: 'start'}});
    }});
}}
</script>
</body>
</html>'''


class ReviewHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/review':
            data = get_review_data()
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

        if self.path == '/api/approve':
            channel_id = body.get('channel_id')
            video_id = body.get('video_id')
            start = body.get('start', 0)
            end = body.get('end', 30)

            # Approve the selected video with time range in review_note
            db.update_video_review(video_id, 'approved',
                                   review_note=json.dumps({'start': start, 'end': end}),
                                   selected=True)

            # Reject all other pending videos for this channel
            with db.get_conn() as conn:
                conn.execute('''
                    UPDATE videos SET review_status = 'rejected', reviewed_at = ?
                    WHERE channel_id = ? AND video_id != ? AND review_status = 'pending'
                ''', (datetime.now().isoformat(), channel_id, video_id))
                # Advance channel status
                conn.execute('''
                    UPDATE channels SET status = 'approved', updated_at = ?
                    WHERE channel_id = ?
                ''', (datetime.now().isoformat(), channel_id))

            log.info("Approved %s for channel %s (trim %d-%ds)", video_id, channel_id, start, end)
            self._json_response({'ok': True})

        elif self.path == '/api/reject-video':
            channel_id = body.get('channel_id')
            video_id = body.get('video_id')

            db.update_video_review(video_id, 'rejected')
            log.info("Rejected video %s for channel %s", video_id, channel_id)
            self._json_response({'ok': True})

        elif self.path == '/api/reject':
            channel_id = body.get('channel_id')

            # Reject all pending videos for this channel
            with db.get_conn() as conn:
                conn.execute('''
                    UPDATE videos SET review_status = 'rejected', reviewed_at = ?
                    WHERE channel_id = ? AND review_status = 'pending'
                ''', (datetime.now().isoformat(), channel_id))
                conn.execute('''
                    UPDATE channels SET status = 'rejected', updated_at = ?
                    WHERE channel_id = ?
                ''', (datetime.now().isoformat(), channel_id))

            log.info("Rejected all videos for channel %s", channel_id)
            self._json_response({'ok': True})

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
    parser = argparse.ArgumentParser(description="Video Review Web Interface")
    parser.add_argument("--port", type=int, default=8888)
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
