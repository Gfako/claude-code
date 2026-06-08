---
name: reference-gdrive-sheets
description: "Google Drive + Sheets API access via OAuth token at .credentials/gdrive-token.pickle, scopes drive.file + spreadsheets"
metadata: 
  node_type: memory
  type: reference
  originSessionId: e808c110-db38-4d6e-91aa-f08e48c43a9d
---

OAuth token at `/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gdrive-token.pickle` grants **both** Drive and Sheets API access:
- `https://www.googleapis.com/auth/drive.file` — create/manage files this app created (used by weekly report charts)
- `https://www.googleapis.com/auth/spreadsheets` — create and edit Google Sheets

Google Cloud project: `upheld-magpie-492610-c2`. OAuth client: `.credentials/gdrive-oauth-client.json`. Re-auth script: `.credentials/reauth_gdrive_sheets.py` (re-runs the OAuth flow if token expires or scopes need changing).

**Why:** The original token only had `drive.file`, sufficient for uploading chart images but not for creating/editing Sheets. Scope expanded 2026-05-19 to enable writing audit punch-lists and other tabular data into native Google Sheets.

**How to apply:** Use this token whenever the user asks for a "spreadsheet" or "Google Sheet" output. Load with `pickle.load`, then `build("sheets", "v4", credentials=creds)` for Sheets API or `build("drive", "v3", credentials=creds)` for Drive. The `drive.file` scope means we can only edit Sheets we created via the app — pre-existing user-made sheets are out of reach.
