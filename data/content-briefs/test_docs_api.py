#!/usr/bin/env python3
"""Verify Docs API access with current OAuth token."""
import pickle
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

TOKEN_PATH = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gdrive-token.pickle")
DOC_ID = "1pKrK_09XblER55HGZ2nEoKKiTxfYyvTMt2KGo9KKdC8"

with open(TOKEN_PATH, "rb") as f:
    creds = pickle.load(f)

print(f"Token scopes: {creds.scopes if hasattr(creds, 'scopes') else 'unknown'}")

try:
    docs = build("docs", "v1", credentials=creds)
    doc = docs.documents().get(documentId=DOC_ID, fields="title,documentId").execute()
    print(f"OK Docs API works. Title: {doc['title']}")
except HttpError as e:
    print(f"FAIL Docs API: {e}")
