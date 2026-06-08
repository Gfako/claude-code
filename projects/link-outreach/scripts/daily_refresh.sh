#!/bin/bash
# Daily refresh for the Link Building Master Tracker.
# Pulls latest Reply.io status, repairs _Data formulas, refreshes dashboard.
#
# Run manually:   bash link-outreach/scripts/daily_refresh.sh
# Run via launchd: see com.synthesia.link-outreach.daily.plist (set up separately).

set -u  # do not use set -e — we want to keep going if one campaign sync fails

PROJECT_ROOT="/Users/george.fakorellis/Desktop/SEO Custom Projects"
SCRIPTS="$PROJECT_ROOT/link-outreach/scripts"
LOG="/tmp/link-outreach-daily.log"

cd "$PROJECT_ROOT"

echo "===== daily_refresh start: $(date) =====" >> "$LOG"

CAMPAIGNS=(
  "rephrase-defunct"
  "competitor-affiliates"
  "guest-posts-video-translation"
  "guest-posts-automation"
  "aeo-listicle-gap"
)

for c in "${CAMPAIGNS[@]}"; do
  echo "--- sync_replyio: $c ---" >> "$LOG"
  python3 "$SCRIPTS/sync_replyio.py" "$c" >> "$LOG" 2>&1 || echo "WARN: sync failed for $c" >> "$LOG"
done

echo "--- repair _Data formulas ---" >> "$LOG"
python3 "$SCRIPTS/repair_data_formulas.py" >> "$LOG" 2>&1

echo "--- refresh dashboard ---" >> "$LOG"
python3 "$SCRIPTS/setup_dashboard.py" refresh >> "$LOG" 2>&1

echo "--- build/refresh monthly link tabs ---" >> "$LOG"
python3 "$SCRIPTS/build_monthly_link_tabs.py" >> "$LOG" 2>&1

echo "===== daily_refresh done: $(date) =====" >> "$LOG"
