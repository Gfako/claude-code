#!/usr/bin/env python3
"""Update existing Google Doc with rewritten article (preserves URL/sharing)."""
import pickle
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

TOKEN_PATH = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gdrive-token.pickle")
ARTICLE_PATH = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/content-briefs/article-how-to-write-a-youtube-video-script.md")
DOC_ID = "1uppeatklBhXB5TRvpZgFcet09QToaSYlwJXguA6C7ro"

with open(TOKEN_PATH, "rb") as f:
    creds = pickle.load(f)

drive = build("drive", "v3", credentials=creds)
media = MediaFileUpload(str(ARTICLE_PATH), mimetype="text/markdown", resumable=False)

updated = drive.files().update(
    fileId=DOC_ID,
    media_body=media,
    fields="id,webViewLink,name,modifiedTime",
).execute()

print(f"Doc updated: {updated['name']}")
print(f"URL: {updated['webViewLink']}")
print(f"Modified: {updated['modifiedTime']}")
