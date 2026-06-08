#!/usr/bin/env python3
"""Update the humanized + formatted Google Doc in-place."""
import pickle
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

TOKEN_PATH = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gdrive-token.pickle")
ARTICLE_PATH = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/content-briefs/article-humanized-current.md")
DOC_ID = "1pKrK_09XblER55HGZ2nEoKKiTxfYyvTMt2KGo9KKdC8"

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
