---
name: Google Drive Chart Hosting
description: How to upload chart images to Google Drive for Notion embedding — uses OAuth credentials, not service account
type: reference
---

## Google Drive Chart Upload

Charts for the weekly SEO report are uploaded to Google Drive instead of imgur.

**Folder:** `Weekly Report Charts` — ID: `1Ay76vQA2rt0PFPZ0RLE5oTklW7Uv4ELe`
**OAuth credentials:** `.credentials/gdrive-oauth-client.json`
**Token:** `.credentials/gdrive-token.pickle`
**Image URL format:** `https://drive.google.com/uc?id={file_id}&export=view`

**Upload code:**
```python
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

with open('.credentials/gdrive-token.pickle', 'rb') as f:
    creds = pickle.load(f)

service = build('drive', 'v3', credentials=creds)
folder_id = '1Ay76vQA2rt0PFPZ0RLE5oTklW7Uv4ELe'

media = MediaFileUpload('/tmp/chart.png', mimetype='image/png')
file = service.files().create(
    body={'name': 'chart_name.png', 'parents': [folder_id]},
    media_body=media, fields='id'
).execute()

# Make publicly viewable for Notion embedding
service.permissions().create(
    fileId=file.get('id'),
    body={'type': 'anyone', 'role': 'reader'}
).execute()

url = f"https://drive.google.com/uc?id={file.get('id')}&export=view"
```

**Note:** If token expires, re-run the OAuth flow using gdrive-oauth-client.json.
