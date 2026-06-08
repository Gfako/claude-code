#!/usr/bin/env python3
"""Check revision history + comments on the humanized doc."""
import pickle
from pathlib import Path
from googleapiclient.discovery import build

TOKEN_PATH = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gdrive-token.pickle")
DOC_ID = "1pKrK_09XblER55HGZ2nEoKKiTxfYyvTMt2KGo9KKdC8"

with open(TOKEN_PATH, "rb") as f:
    creds = pickle.load(f)

drive = build("drive", "v3", credentials=creds)

# Revision history
print("=" * 60)
print("REVISION HISTORY")
print("=" * 60)
revs = drive.revisions().list(
    fileId=DOC_ID,
    fields="revisions(id,modifiedTime,lastModifyingUser/displayName,size)",
).execute().get("revisions", [])
for r in revs:
    print(f"- {r.get('modifiedTime', '?')} | by {r.get('lastModifyingUser', {}).get('displayName', '?')} | rev {r.get('id', '?')} | size {r.get('size', '?')}")

# Comments
print()
print("=" * 60)
print("COMMENTS (including resolved + deleted)")
print("=" * 60)
comments = drive.comments().list(
    fileId=DOC_ID,
    fields="comments(id,author/displayName,content,quotedFileContent/value,resolved,deleted,createdTime,replies(content,author/displayName,createdTime))",
    includeDeleted=True,
).execute().get("comments", [])
print(f"Total comments: {len(comments)}")
for i, c in enumerate(comments, 1):
    print(f"\n--- Comment #{i} ---")
    print(f"Author: {c.get('author', {}).get('displayName', '?')}")
    print(f"Created: {c.get('createdTime', '?')}")
    print(f"Resolved: {c.get('resolved', False)}")
    print(f"Deleted: {c.get('deleted', False)}")
    q = c.get("quotedFileContent", {}).get("value", "")
    if q:
        print(f"Anchored to: \"{q[:200]}\"")
    else:
        print("Anchored to: [no anchor / orphaned]")
    print(f"Comment: {c.get('content', '')[:500]}")
