#!/usr/bin/env python3
"""Upload the formatted humanized article as a brand-new Google Doc."""
import pickle
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

TOKEN_PATH = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gdrive-token.pickle")
ARTICLE_PATH = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/content-briefs/article-humanized-formatted.md")
DOC_TITLE = "How to Write a YouTube Video Script — Humanized + Formatted"

with open(TOKEN_PATH, "rb") as f:
    creds = pickle.load(f)

drive = build("drive", "v3", credentials=creds)

file_metadata = {
    "name": DOC_TITLE,
    "mimeType": "application/vnd.google-apps.document",
}
media = MediaFileUpload(str(ARTICLE_PATH), mimetype="text/markdown", resumable=False)

created = drive.files().create(
    body=file_metadata,
    media_body=media,
    fields="id,webViewLink,name",
).execute()

drive.permissions().create(
    fileId=created["id"],
    body={"type": "anyone", "role": "writer"},
    fields="id",
).execute()

print(f"Doc created: {created['name']}")
print(f"ID: {created['id']}")
print(f"URL: {created['webViewLink']}")
