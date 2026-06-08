#!/usr/bin/env python3
"""Recover from the bad HTML upload: re-apply the 6 edits in plain markdown.

Uses the locally-cached clean markdown (article-humanized-current.md from rev 187)
and uploads via markdown mimetype to restore proper Doc formatting.
"""
import pickle
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

TOKEN_PATH = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gdrive-token.pickle")
SOURCE_MD = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/content-briefs/article-humanized-current.md")
RECOVERED_MD = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/content-briefs/article-recovered.md")
DOC_ID = "1pKrK_09XblER55HGZ2nEoKKiTxfYyvTMt2KGo9KKdC8"

text = SOURCE_MD.read_text()

edits = [
    # Step 1 sentence
    (
        "I have learned that if I start writing without a title I end up writing three different videos that share a topic.",
        "I have learned that without a working title, I end up writing three different videos that share a topic.",
    ),
    # Step 8 outro: 2012 URL → YouTube Help URL
    (
        "[the algorithm registers the watch as complete](https://www.searchenginewatch.com/2012/10/22/youtube-algorithm-change-time-watched-key-to-higher-video-search-rankings/)",
        "[the algorithm registers the watch as complete](https://support.google.com/youtube/answer/141805)",
    ),
    # Step 8 Takeaway rewrite (current state has "delivered" not "raised delivered")
    (
        "**Takeaway:** One ask, tied to a problem the body already delivered in under 30 seconds. Outro under 10\\.",
        "**Takeaway:** One ask, tied to a problem the body already raised. Deliver it in under 30 seconds, and keep the outro under 10.",
    ),
    # Step 9 wpm: add Voiceovers.com link (none exists currently)
    (
        "At a pace one minute of finished video runs to roughly 160 to 180 words.",
        "At a pace [one minute of finished video runs to roughly 160 to 180 words](https://www.voiceovers.com/blog/how-many-words-per-minute-voice-over).",
    ),
    # How long section: swap Yuan link for Voiceovers.com link
    (
        "[speaking pace of around 160 to 180 words per minute](https://www.isca-archive.org/interspeech_2006/yuan06_interspeech.html)",
        "[speaking pace of around 160 to 180 words per minute](https://www.voiceovers.com/blog/how-many-words-per-minute-voice-over)",
    ),
    # Step 9 Takeaway added at end
    (
        "The main thing I learned is to read my work loud. I time myself to see how long it takes. If I stumble on any part I cut it out. The final version should be shorter and better than the version I wrote.",
        "The main thing I learned is to read my work loud. I time myself to see how long it takes. If I stumble on any part I cut it out. The final version should be shorter and better than the version I wrote.\n\n**Takeaway:** Read the script aloud, time it, and cut anything that makes you stumble. The version that ships should be tighter than the first draft.",
    ),
]

applied, missing = [], []
for old, new in edits:
    if old in text:
        text = text.replace(old, new, 1)
        applied.append(old[:80])
    else:
        missing.append(old[:80])

print(f"Applied: {len(applied)}/{len(edits)}")
for a in applied:
    print(f"  OK -> {a}...")
if missing:
    print(f"MISSED: {len(missing)}")
    for m in missing:
        print(f"  -> {m}...")

RECOVERED_MD.write_text(text)
print(f"Wrote recovered markdown to {RECOVERED_MD}")

# Upload as markdown to restore proper Doc formatting
with open(TOKEN_PATH, "rb") as f:
    creds = pickle.load(f)
drive = build("drive", "v3", credentials=creds)
media = MediaFileUpload(str(RECOVERED_MD), mimetype="text/markdown", resumable=False)
updated = drive.files().update(
    fileId=DOC_ID,
    media_body=media,
    fields="id,webViewLink,name,modifiedTime",
).execute()

print(f"Doc updated: {updated['name']}")
print(f"URL: {updated['webViewLink']}")
print(f"Modified: {updated['modifiedTime']}")
