#!/usr/bin/env python3
"""Apply targeted edits to humanized doc with green coloring (Option A workflow).

Pipeline:
1. Read the freshly-pulled markdown (article-humanized-current.md)
2. Apply targeted edits, wrapping new/changed text with [[G]]...[[/G]] sentinels
3. Convert to HTML with pandoc
4. Replace sentinels with green color spans
5. Upload as text/html so Drive preserves the green coloring
"""
import pickle
import subprocess
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

TOKEN_PATH = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gdrive-token.pickle")
SOURCE_MD = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/content-briefs/article-humanized-current.md")
EDITED_MD = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/content-briefs/article-with-edits.md")
HTML_OUT = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/content-briefs/article-with-edits.html")
DOC_ID = "1pKrK_09XblER55HGZ2nEoKKiTxfYyvTMt2KGo9KKdC8"
GREEN = "#0b8043"

text = SOURCE_MD.read_text()

# === Edits ===
edits = [
    # Comment #5: rewrite Step 1 "writing without a title" sentence
    (
        "I have learned that if I start writing without a title I end up writing three different videos that share a topic.",
        "[[G]]I have learned that without a working title, I end up writing three different videos that share a topic.[[/G]]",
    ),
    # Step 8 outro: 2012 URL → YouTube Help URL
    (
        "[the algorithm registers the watch as complete](https://www.searchenginewatch.com/2012/10/22/youtube-algorithm-change-time-watched-key-to-higher-video-search-rankings/)",
        "[[G]][the algorithm registers the watch as complete](https://support.google.com/youtube/answer/141805)[[/G]]",
    ),
    # Comment #4: Step 8 Takeaway rewrite (matches user's current text)
    (
        "**Takeaway:** One ask, tied to a problem the body already delivered in under 30 seconds. Outro under 10\\.",
        "**Takeaway:** [[G]]One ask, tied to a problem the body already raised. Deliver it in under 30 seconds, and keep the outro under 10.[[/G]]",
    ),
    # Comment #3: Step 9 wpm — add link (none exists currently)
    (
        "At a pace one minute of finished video runs to roughly 160 to 180 words.",
        "At a pace [[G]][one minute of finished video runs to roughly 160 to 180 words](https://www.voiceovers.com/blog/how-many-words-per-minute-voice-over)[[/G]].",
    ),
    # Same fix in "How long" section
    (
        "[speaking pace of around 160 to 180 words per minute](https://www.isca-archive.org/interspeech_2006/yuan06_interspeech.html)",
        "[[G]][speaking pace of around 160 to 180 words per minute](https://www.voiceovers.com/blog/how-many-words-per-minute-voice-over)[[/G]]",
    ),
    # Comments #1+#2: Add a Takeaway at the end of Step 9
    (
        "The main thing I learned is to read my work loud. I time myself to see how long it takes. If I stumble on any part I cut it out. The final version should be shorter and better than the version I wrote.",
        "The main thing I learned is to read my work loud. I time myself to see how long it takes. If I stumble on any part I cut it out. The final version should be shorter and better than the version I wrote.\n\n[[G]]**Takeaway:** Read the script aloud, time it, and cut anything that makes you stumble. The version that ships should be tighter than the first draft.[[/G]]",
    ),
]

applied = []
missing = []
for old, new in edits:
    if old in text:
        text = text.replace(old, new, 1)
        applied.append(old[:80])
    else:
        missing.append(old[:80])

print(f"Applied: {len(applied)} edits")
for a in applied:
    print(f"  OK -> {a}...")
if missing:
    print(f"MISSED: {len(missing)}")
    for m in missing:
        print(f"  -> {m}...")
    raise SystemExit("Aborting: some edits did not find their anchor text")

EDITED_MD.write_text(text)
print(f"Wrote edited markdown to {EDITED_MD}")

# === Convert to HTML via pandoc ===
subprocess.run(
    ["pandoc", "-f", "markdown", "-t", "html", str(EDITED_MD), "-o", str(HTML_OUT)],
    check=True,
)
html = HTML_OUT.read_text()

# Replace sentinels with green spans
html = html.replace("[[G]]", f'<span style="color:{GREEN}">')
html = html.replace("[[/G]]", "</span>")
HTML_OUT.write_text(html)
print(f"HTML written with green spans to {HTML_OUT}")

# === Upload as HTML ===
with open(TOKEN_PATH, "rb") as f:
    creds = pickle.load(f)

drive = build("drive", "v3", credentials=creds)
media = MediaFileUpload(str(HTML_OUT), mimetype="text/html", resumable=False)
updated = drive.files().update(
    fileId=DOC_ID,
    media_body=media,
    fields="id,webViewLink,name,modifiedTime",
).execute()

print(f"Doc updated: {updated['name']}")
print(f"URL: {updated['webViewLink']}")
print(f"Modified: {updated['modifiedTime']}")
