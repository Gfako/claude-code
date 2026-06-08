#!/usr/bin/env python3
"""Try to export the humanized doc via Drive API."""
import pickle
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

TOKEN_PATH = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gdrive-token.pickle")
DOC_ID = "1yW6MSSLgEtNw4wtAfek9eiBnCWxBkJ1LuenbXO8fkNk"
OUT = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/content-briefs/article-humanized-from-gdoc.md")

with open(TOKEN_PATH, "rb") as f:
    creds = pickle.load(f)

drive = build("drive", "v3", credentials=creds)

try:
    md = drive.files().export(fileId=DOC_ID, mimeType="text/markdown").execute()
    OUT.write_bytes(md)
    print(f"OK exported {len(md)} bytes to {OUT}")
except HttpError as e:
    print(f"FAILED export: {e}")
    print("Likely cause: drive.file scope only sees files this app created.")
