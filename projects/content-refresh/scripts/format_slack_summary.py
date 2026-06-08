#!/usr/bin/env python3
"""
Format a daily run summary for posting to #light-content-refreshes.

Input (stdin JSON):
{
  "run_date": "2026-04-24",
  "urls_checked": 15,
  "pages_with_findings": 9,
  "total_findings": 27,
  "notion_database_url": "https://www.notion.so/...",
  "results": [
    {"url": "...", "title": "...", "score": 61, "severity": "Critical",
     "findings_count": 4, "types": ["pricing", "link"],
     "notion_page_url": "https://www.notion.so/..."},
    ...
  ]
}

Output: a Slack message text string. Skill passes this to slack_send_message.
"""

import json
import sys

SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Clean": 4}
SEVERITY_EMOJI = {
    "Critical": "🔴",
    "High": "🟠",
    "Medium": "🟡",
    "Low": "🟢",
    "Clean": "⚪",
}


def format_message(summary: dict) -> str:
    lines = []
    lines.append(f"*Light content refresh — {summary['run_date']}*")
    lines.append(
        f"Checked {summary['urls_checked']} pages · "
        f"{summary['pages_with_findings']} flagged · "
        f"{summary['total_findings']} findings total"
    )
    lines.append("")

    results = sorted(
        summary.get("results", []),
        key=lambda r: (SEVERITY_ORDER.get(r["severity"], 99), -r.get("score", 0)),
    )

    flagged = [r for r in results if r["severity"] != "Clean"]
    if not flagged:
        lines.append("_No flagged pages in this batch._")
    else:
        lines.append("*Pages needing review (sorted by severity):*")
        for r in flagged:
            emoji = SEVERITY_EMOJI.get(r["severity"], "•")
            types_str = ", ".join(r.get("types", []))
            title = r.get("title") or r["url"]
            page_url = r.get("notion_page_url") or r["url"]
            lines.append(
                f"{emoji} <{page_url}|{title}> — score {r['score']} "
                f"({r['findings_count']} findings: {types_str})"
            )

    lines.append("")
    db_url = summary.get("notion_database_url")
    if db_url:
        lines.append(f"<{db_url}|Open the full database>")
    return "\n".join(lines)


def main():
    summary = json.loads(sys.stdin.read())
    print(format_message(summary))


if __name__ == "__main__":
    main()
