import sys
sys.path.insert(0, '/Users/george.fakorellis/Desktop/SEO Custom Projects/link-outreach/scripts')
from sheets_helper import ensure_master_sheet, _sheets_service, COLUMNS, _col_letter, DATA_TAB

sid = ensure_master_sheet()
svc = _sheets_service()

existing = svc.spreadsheets().values().get(spreadsheetId=sid, range=f'{DATA_TAB}!A2:A').execute().get('values', [])
campaigns = [r[0] for r in existing if r]
print(f"campaigns in _Data: {campaigns}")

def cidx(col):
    return _col_letter(COLUMNS.index(col))

sp = cidx("source_page"); dr = cidx("dr"); emails = cidx("emails")
sent = cidx("added_to_sequence"); reply = cidx("reply_status")  # Contacted = added-to-sequence
placed = cidx("link_placed_at"); placed_url = cidx("link_placed_url")
last_act = cidx("last_activity_at")

rows_out = []
for c in campaigns:
    safe = c.replace("'", "''")
    ref = "'" + safe + "'"
    rows_out.append([
        c,
        f"=COUNTA({ref}!{sp}2:{sp})",
        f'=COUNTIFS({ref}!{dr}2:{dr},">=30")',
        f'=COUNTIFS({ref}!{emails}2:{emails},"<>")',
        f"=COUNTIFS({ref}!{sent}2:{sent},TRUE)",
        f'=COUNTIFS({ref}!{reply}2:{reply},"replied")',
        f'=IFERROR(VLOOKUP("{safe}",_LinksData!A:B,2,FALSE),0)',  # placed reads from monthly-tabs aggregate
        f'=IFERROR(IF(COUNTA({ref}!{last_act}2:{last_act})=0,"",MAX({ref}!{last_act}2:{last_act})),"")',
    ])

last_col = chr(ord('A') + len(rows_out[0]) - 1)
end_row = 1 + len(rows_out)
svc.spreadsheets().values().update(
    spreadsheetId=sid,
    range=f"{DATA_TAB}!A2:{last_col}{end_row}",
    valueInputOption="USER_ENTERED",
    body={"values": rows_out},
).execute()
print(f"rewrote {len(rows_out)} campaign rows")

v = svc.spreadsheets().values().get(spreadsheetId=sid, range=f'{DATA_TAB}!A1:H10').execute()
print()
for row in v.get('values', []):
    print(" | ".join(f"{c:<28}" for c in row))
