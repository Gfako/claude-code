#!/usr/bin/env python3
"""
Fix missing data in AirOps grid by reading from analyzed.json and pushing updates.
Uses AirOps MCP HTTP endpoint directly.
"""

import json
import urllib.request
import urllib.error
import time

GRID_ID = 63328
TABLE_ID = 81833
AIROPS_MCP_URL = "https://app.airops.com/mcp"
ANALYZED_PATH = "/Users/george.fakorellis/Desktop/SEO Custom Projects/link-outreach/campaigns/niche-edits/2026-04-08-video-translator/analyzed.json"
UPDATE_ROWS_PATH = "/Users/george.fakorellis/Desktop/SEO Custom Projects/link-outreach/campaigns/niche-edits/2026-04-08-video-translator/airops-update-rows.json"

def main():
    # Load full update data
    with open(UPDATE_ROWS_PATH) as f:
        all_rows = json.load(f)

    print(f"Total rows to update: {len(all_rows)}")

    # Process in chunks of 30 (safe size for the API)
    chunk_size = 30
    total_updated = 0

    for i in range(0, len(all_rows), chunk_size):
        chunk = all_rows[i:i+chunk_size]

        # Build the MCP tool call
        request_body = {
            "jsonrpc": "2.0",
            "id": f"update-{i}",
            "method": "tools/call",
            "params": {
                "name": "write_grid",
                "arguments": {
                    "grid_id": GRID_ID,
                    "grid_table_id": TABLE_ID,
                    "mode": "update",
                    "rows": chunk
                }
            }
        }

        data = json.dumps(request_body).encode('utf-8')
        req = urllib.request.Request(
            AIROPS_MCP_URL,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                total_updated += len(chunk)
                print(f"  Chunk {i//chunk_size + 1}: Updated {len(chunk)} rows (total: {total_updated}/{len(all_rows)})")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else 'no body'
            print(f"  ERROR on chunk {i//chunk_size + 1}: HTTP {e.code} - {error_body[:200]}")
        except Exception as e:
            print(f"  ERROR on chunk {i//chunk_size + 1}: {e}")

        time.sleep(0.5)  # Rate limiting

    print(f"\nDone. Updated {total_updated} rows.")

if __name__ == "__main__":
    main()
