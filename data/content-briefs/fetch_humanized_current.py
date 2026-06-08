#!/usr/bin/env python3
"""Pull current state of the humanized doc."""
import pickle
from pathlib import Path
from googleapiclient.discovery import build

TOKEN_PATH = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gdrive-token.pickle")
DOC_ID = "1pKrK_09XblER55HGZ2nEoKKiTxfYyvTMt2KGo9KKdC8"
OUT = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/content-briefs/article-humanized-current.md")

with open(TOKEN_PATH, "rb") as f:
    creds = pickle.load(f)

drive = build("drive", "v3", credentials=creds)
md = drive.files().export(fileId=DOC_ID, mimeType="text/markdown").execute()
OUT.write_bytes(md)
print(f"OK exported {len(md)} bytes to {OUT}")
