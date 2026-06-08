#!/usr/bin/env python3
"""Google Doc roundtrip helper: pull → snapshot → (optional) push.

The pattern that prevents overwriting the user's edits:
  1. pull doc into <slug>/current-from-doc.md
  2. snapshot it to <slug>/current-from-doc-baseline-<UTC>.md (a frozen copy)
  3. caller may edit current-from-doc.md
  4. push only when caller passes --push <path>

Commands:
  pull   <doc_id> <dest_dir>            # pull + snapshot baseline
  push   <doc_id> <src_md>              # upload markdown → Doc
  create <title> <src_md>               # create new Doc with markdown content
                                        # prints doc_id and webViewLink

Token at .credentials/gdrive-token.pickle (scopes: drive.file + spreadsheets).
"""
import argparse, io, pickle, sys
from datetime import datetime, timezone
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaInMemoryUpload

TOKEN = Path("/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gdrive-token.pickle")


def drive_client():
    with open(TOKEN, "rb") as f:
        creds = pickle.load(f)
    return build("drive", "v3", credentials=creds)


def pull(doc_id: str, dest_dir: Path) -> Path:
    drive = drive_client()
    dest_dir.mkdir(parents=True, exist_ok=True)
    req = drive.files().export_media(fileId=doc_id, mimeType="text/markdown")
    buf = io.BytesIO()
    dl = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    content = buf.getvalue().decode("utf-8")
    current = dest_dir / "current-from-doc.md"
    current.write_text(content)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    snapshot = dest_dir / f"current-from-doc-baseline-{stamp}.md"
    snapshot.write_text(content)
    meta = drive.files().get(fileId=doc_id, fields="name,modifiedTime").execute()
    print(f"Pulled: {meta['name']}")
    print(f"Modified: {meta['modifiedTime']}")
    print(f"Current:  {current}")
    print(f"Snapshot: {snapshot}")
    return current


def push(doc_id: str, src_md: Path):
    drive = drive_client()
    res = drive.files().update(
        fileId=doc_id,
        media_body=MediaFileUpload(str(src_md), mimetype="text/markdown"),
        fields="id,webViewLink,modifiedTime,name",
    ).execute()
    print(f"Pushed:   {res['name']}")
    print(f"URL:      {res['webViewLink']}")
    print(f"Modified: {res['modifiedTime']}")


def create(title: str, src_md: Path) -> str:
    drive = drive_client()
    content = src_md.read_bytes()
    res = drive.files().create(
        body={"name": title, "mimeType": "application/vnd.google-apps.document"},
        media_body=MediaInMemoryUpload(content, mimetype="text/markdown"),
        fields="id,webViewLink",
    ).execute()
    print(f"Created:  {res['id']}")
    print(f"URL:      {res['webViewLink']}")
    return res["id"]


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_pull = sub.add_parser("pull")
    p_pull.add_argument("doc_id")
    p_pull.add_argument("dest_dir", type=Path)
    p_push = sub.add_parser("push")
    p_push.add_argument("doc_id")
    p_push.add_argument("src_md", type=Path)
    p_create = sub.add_parser("create")
    p_create.add_argument("title")
    p_create.add_argument("src_md", type=Path)
    args = ap.parse_args()
    if args.cmd == "pull":
        pull(args.doc_id, args.dest_dir)
    elif args.cmd == "push":
        push(args.doc_id, args.src_md)
    elif args.cmd == "create":
        create(args.title, args.src_md)


if __name__ == "__main__":
    main()
