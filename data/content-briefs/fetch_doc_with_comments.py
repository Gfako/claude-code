#!/usr/bin/env python3
"""Export the current Google Doc as markdown and pull all comments + their anchored text."""
import pickle
from pathlib import Path
from googleapiclient.discovery import build

TOKEN_PATH = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gdrive-token.pickle")
DOC_ID = "1uppeatklBhXB5TRvpZgFcet09QToaSYlwJXguA6C7ro"
OUT_DOC = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/content-briefs/article-current-from-gdoc.md")
OUT_COMMENTS = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/content-briefs/article-gdoc-comments.txt")

with open(TOKEN_PATH, "rb") as f:
    creds = pickle.load(f)

drive = build("drive", "v3", credentials=creds)

md = drive.files().export(fileId=DOC_ID, mimeType="text/markdown").execute()
OUT_DOC.write_bytes(md)
print(f"Doc exported: {OUT_DOC} ({len(md)} bytes)")

comments = drive.comments().list(
    fileId=DOC_ID,
    fields="comments(id,author/displayName,content,quotedFileContent/value,resolved,createdTime,replies(content,author/displayName,createdTime))",
    includeDeleted=False,
).execute().get("comments", [])

lines = [f"Total comments: {len(comments)}\n"]
for i, c in enumerate(comments, 1):
    lines.append(f"\n--- Comment #{i} ---")
    lines.append(f"Author: {c.get('author', {}).get('displayName', '?')}")
    lines.append(f"Resolved: {c.get('resolved', False)}")
    lines.append(f"Created: {c.get('createdTime', '?')}")
    q = c.get("quotedFileContent", {}).get("value", "")
    if q:
        lines.append(f"Anchored to: \"{q}\"")
    lines.append(f"Comment: {c.get('content', '')}")
    for r in c.get("replies", []):
        lines.append(f"  Reply by {r.get('author', {}).get('displayName', '?')}: {r.get('content', '')}")

OUT_COMMENTS.write_text("\n".join(lines))
print(f"Comments saved: {OUT_COMMENTS}")
print(f"Total comments found: {len(comments)}")
