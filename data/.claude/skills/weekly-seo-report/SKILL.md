---
name: weekly-seo-report
description: Generate the weekly SEO meeting report from Omni data and post it to Notion as a new toggle dropdown.
---

# Weekly SEO Report Generator

You are generating the weekly SEO meeting report and posting it to the Notion page: `214c16d22bf1806ea205fc82085149a8`

The Omni model ID is `6a5202c7-3bf0-4daa-8a48-3aaa6cca1eea`. You do NOT need to call pickModel.

## Steps

Run each data pull in parallel where possible, then compose and post.

### Step 1: Pull all data from Omni

Pull the following datasets. Use the exact topic IDs, filters, and prompts specified.

#### 1A. Cohort LTV — Summary (Monthly Pipeline)
- **Topic:** `rep_marketing__return_on_organic`
- **Prompt:** `Show me the total cumulative V2 LTV Return in GBP by Cohort Month for the last 6 months including the current (partial) month. I want the running total as of today and also as of 1 week ago, so I can calculate the week-over-week change in the cumulative value for each cohort.`
- **Note:** ALWAYS include the current calendar month even if it's still in formation — it surfaces as the freshest cohort (typically labelled "(new)" in the text). Do not stop at the previous complete month.

#### 1B. Cohort LTV — Time Series (for chart)
- **Topic:** `rep_marketing__return_on_organic`
- **Prompt:** `Show me the sum of V2 LTV Return in GBP grouped by Cohort Month month and Number of Days After Last Day of Cohort, for cohort months in the last 8 months including the current (partial) month. Sort by cohort month and days ascending.`
- **Processing:** The query returns daily increments. Compute cumulative running totals per cohort month. Sample every 5 days to keep chart data manageable. ALWAYS include the current calendar month in the chart even though it's incomplete — it'll show as a small partial bar at the right edge, which is the point.

#### 1C. LTV by Page Group — Stacked Bar (for chart)
- **Topic:** `Contact & Account Intent`
- **Prompt:** `Show me sum of v2 Return LTV in GBP grouped by GA4 First Visit Timestamp month and GA4 First Visit Page Groups [2026]. Only include contacts where GA4 First Visit Medium is organic, GA4 First Visit Source is google or bing, Country Tier Adj is T1 - US or T1 - ex. US or T2. GA4 First Visit Timestamp from 9 months ago to now. Exclude GA4 First Visit Page Groups [2026] values Homepage, Pricing, Book Demo, Free AI Video Page, Other, Santa, Create Free AI Video. Show top 200 rows sorted by month ascending then LTV descending.`
- **Note:** Uses the `[2026]` field (Video Generation, Avatar singular, Translation, Voice, Features/Tools Other, Templates, Service Providers, PT-BR, etc.) — promoted to the shared model on 2026-04-28 by Chris Mee. If the field disappears or returns empty, fall back to legacy `GA4 First Visit Page URL Groups` and flag in the report.

#### 1D. Weekly Clicks by Page Group — Stacked Bar (for chart)
- **Topic:** `d_marketing__seo_page_performance`
- **Prompt:** `Show me the sum of clicks grouped by date week and Page Groups NEW. Only include Country Tier Tier 1 or Tier 2. Exclude Page Groups NEW values Homepage, Pricing, Book Demo, Other, Santa, Create Free AI Video. Show data for the last 24 weeks. Sort by week ascending.`
- **Note:** MUST include Country Tier = Tier 1, Tier 2 filter. Without it, numbers are ~4x higher.

#### 1E. Clicks — Top Pages Up/Down
- **Topic:** `d_marketing__seo_page_performance`
- **Prompt:** `For the last complete week, show me page URL, current week clicks, previous week clicks, and WoW click change. Only include Country Tier Tier 1 or Tier 2. Exclude Page Groups NEW Homepage, Pricing, Book Demo, Other, Santa, Create Free AI Video. Sort by clicks descending. Show top 20 with page URL.`
- **Note:** MUST include Country Tier = Tier 1, Tier 2 filter.

#### 1F. Total Clicks WoW (two metrics)
- **Metric 1 — All tiers, all pages:**
  - **Topic:** `d_marketing__seo_aggregated_performance`
  - **Prompt:** `Show me total clicks for the most recent complete week and the previous week, so I can see the overall WoW change in clicks.`
  - **Label:** "Total Clicks (all tiers, all pages)"
- **Metric 2 — All tiers, excl HP/Pricing/Book Demo/Other/Santa/Free AI Video:**
  - **Topic:** `d_marketing__seo_page_performance`
  - **Prompt:** `Show me the total sum of clicks for the most recent complete week and the total for the previous week. No grouping, just two totals. Exclude Page Groups NEW Homepage, Other, Book Demo, Pricing, Create Free AI Video, Santa. All country tiers.`
  - **Label:** "Total Clicks (all tiers, excl HP/Pricing/Book Demo/Other/Santa/Free AI Video)"

#### 1G. Weekly Contacts by Page Group — Stacked Bar (for chart)
- **Topic:** `d_salesforce__contacts` (NOT `Contact & Account Intent`)
- **Prompt:** `Show me total contact count grouped by GA4 First Visit Timestamp week and GA4 First Visit Page Groups [2026]. Filters: GA4 First Visit Medium equals "organic" exactly. GA4 First Visit Source equals "google" or "bing". Country Tier equals exactly "Tier 1" or "Tier 2" (the values are literally "Tier 1" and "Tier 2" with the word Tier and a space). Exclude GA4 First Visit Page Groups [2026] values "Homepage", "Pricing", "Book Demo", "Free AI Video Page", "Other", "Santa", "Create Free AI Video". GA4 First Visit Timestamp from 24 weeks ago to now. Sort by week ascending.`
- **Note:** Always say "Tier 1" and "Tier 2" verbatim with quotes — the MCP NL layer otherwise sometimes mistranslates to "T1"/"T2" (which doesn't match any value, returns empty). Do NOT pull URL-level here — that hits the 3,000-row limit which only covers ~6 weeks.

#### 1H. Contacts — Top Pages Up/Down
- **Topic:** `d_salesforce__contacts`
- **Prompt:** `Show me the GA4 First Visit Full Page URL and total contact count. Only include contacts where GA4 First Visit Medium is organic, GA4 First Visit Source is google or bing, Country Tier is Tier 1 or Tier 2, GA4 First Visit Timestamp is in the last complete week. Exclude GA4 First Visit Page Url Groups Homepage, Pricing, Book Demo, Other, Create Free AI Video, Santa. Sort by contact count descending. Show top 20. Also show the contact count for the previous week.`
- **Note:** Must use `GA4 First Visit Timestamp` for the date filter (not `Created At`). Must use `GA4 First Visit Medium = organic` + `Source = google/bing` (not `Ft Attribution Type = Organic`).

#### 1I. Weekly MQLs by Page Group — Stacked Bar (for chart)
- **Topic:** `d_salesforce__contacts` (NOT `Contact & Account Intent`)
- **Prompt:** `Show me Contact MQL Count grouped by GA4 First Visit Timestamp week and GA4 First Visit Page Groups [2026]. Filters: GA4 First Visit Medium equals "organic" exactly. GA4 First Visit Source equals "google" or "bing". Country Tier equals exactly "Tier 1" or "Tier 2". Is MQL is true. Exclude GA4 First Visit Page Groups [2026] values "Homepage", "Pricing", "Book Demo", "Free AI Video Page", "Other", "Santa", "Create Free AI Video". GA4 First Visit Timestamp from 24 weeks ago to now. Sort by week ascending.`
- **Note:** Same Tier 1/Tier 2 verbatim-quoting rule as 1G.

#### 1J. MQLs — Top Pages Up/Down
- **Topic:** `d_salesforce__contacts`
- **Prompt:** `Show me the GA4 First Visit Full Page URL and Contact MQL Count. Only include contacts where GA4 First Visit Medium is organic, GA4 First Visit Source is google or bing, Country Tier is Tier 1 or Tier 2, GA4 First Visit Timestamp is in the last complete week, and Is MQL is true. Exclude GA4 First Visit Page Url Groups Homepage, Pricing, Book Demo, Other, Create Free AI Video, Santa. Sort by Contact MQL Count descending. Show top 20. Also show the MQL count for the previous week.`
- **Note:** Same filters as 1H + Is MQL = true.

#### 1K. Weekly HI MQLs by Page Group — Stacked Bar (for chart)
- **Topic:** `d_salesforce__contacts`
- **Prompt:** `Show me Contact MQL Count grouped by GA4 First Visit Timestamp week and GA4 First Visit Page Groups [2026]. Filters: GA4 First Visit Medium equals "organic" exactly. GA4 First Visit Source equals "google" or "bing". Country Tier equals exactly "Tier 1" or "Tier 2". Is MQL is true. First Engagement Trigger equals "Booked Demo". Exclude GA4 First Visit Page Groups [2026] values "Homepage", "Pricing", "Book Demo", "Free AI Video Page", "Other", "Santa", "Create Free AI Video". GA4 First Visit Timestamp from 24 weeks ago to now. Sort by week ascending.`

#### 1L. High Intent MQLs — Top Pages Up/Down
- **Topic:** `d_salesforce__contacts`
- **Prompt:** `Show me the GA4 First Visit Full Page URL and Contact MQL Count. Only include contacts where GA4 First Visit Medium is organic, GA4 First Visit Source is google or bing, Country Tier is Tier 1 or Tier 2, GA4 First Visit Timestamp is in the last complete week, Is MQL is true, and First Engagement Trigger is Booked Demo. Exclude GA4 First Visit Page Url Groups Homepage, Pricing, Book Demo, Other, Create Free AI Video, Santa. Sort by Contact MQL Count descending. Show top 20. Also show the MQL count for the previous week.`
- **Note:** Same filters as 1J + First Engagement Trigger = Booked Demo.

#### 1M. AI Search Referral — 24 Week Weekly Table
- **Topic:** `fct_google_analytics_4_daily_web_report`
- **Prompt:** `Show me the sum of sessions grouped by date week and session source. Filters: Country Tier equals Tier 1 or Tier 2. Session Medium equals referral. Exclude Landing Page Path Groups 1 values equal to Homepage, Other, Book Demo, Pricing, Create Free AI Video, Santa. Session Source should CONTAIN any of: chatgpt, perplexity.ai, gemini.google.com, copilot.microsoft, copilot.cloud, claude.ai, grok.com. Date from 24 weeks ago to now. Sort by week ascending.`
- **CRITICAL — NON-BRAND filter:** Use the field `Landing Page Path Groups 1` (NOT `seo_page_groups` / "full landing page URL groups"). Excluding Homepage via `landing_page_path_groups_1` removes sessions landing on `/`, `/es`, `/fr`, `/de`, `/pt-br` — these are brand-search AI referrals. Without this fix, totals are 2–3× higher than the Omni dashboard. Verify after the first pull: Nov 10 week total should be ~1,100 (not ~3,400). If totals are still too high, the MCP fell back to the wrong field — re-prompt with explicit `landing_page_path_groups_1`.
- **Processing:** Group sources into: ChatGPT (contains "chatgpt"), Perplexity (perplexity.ai), Gemini (gemini.google.com), Claude (claude.ai), Copilot (copilot.microsoft or copilot.cloud), Grok (grok.com). Add Total column. Matches dashboard within ~1–2%.

#### 1N. Self-Reported Lead Source (AI Chatbot) — 24 Week Weekly Table + Chart
- **Topic:** `d_salesforce__contacts` (NOT `Contact & Account Intent` — the events-based topic undercounts by ~45%)
- **Prompt:** `Count contacts grouped by GA4 First Visit Timestamp week. Only include contacts where Self Reported Lead Source equals AI Chatbot and Country Tier equals Tier 1 or Tier 2. GA4 First Visit Timestamp from 24 weeks ago to now. Sort by week ascending.`
- **Chart:** Generate a simple (non-stacked) bar chart with single color (#F5A623). Title: "Weekly Self-Reported 'AI Chatbot' Contacts (T1-2)"

#### 1O. Mention Rate — AirOps AEO
- **Tool:** `mcp__airops__query_analytics`
- **Brand Kit ID:** `6851`
- **Query:** metrics=["mention_rate", "share_of_voice"], dimensions=["competitor"], grain="weekly", start_date=24 weeks ago, end_date=yesterday
- **Also query:** metrics=["mention_rate"], dimensions=["date", "competitor"], grain="weekly" for the trend chart
- **Note:** AirOps returns a `chart_image_url` field — use this directly as the chart image URL (no matplotlib needed). Show top ~10 competitors by mention rate in the text summary.

#### 1P. Share of Voice — AirOps AEO
- Same query as 1N — the share_of_voice metric is returned alongside mention_rate in the competitor dimension query. The chart_image_url from the SoV query can be used directly.

### Step 2: Generate Charts

#### Page Groups [2026] — now exposed in the model (since 2026-04-28)

`GA4 First Visit - Page Groups [2026]` was promoted to the shared model on 2026-04-28 by Chris Mee. Queries 1C, 1G, 1I, 1K all use it directly. Bucket values returned: Video Generation, Avatar (singular), Translation, Voice, Features/Tools Other, Use Cases, Blog, Templates, Service Providers, Alternatives, Case Studies, Glossary, Integrations, ES, FR, DE, PT-BR, plus the excluded Homepage / Pricing / Book Demo / Free AI Video Page / Other / Santa / Create Free AI Video.

**Hard rules (still apply):**
- Do NOT pull URL-level data and bucket in Python — it hits the 3,000-row limit (only ~6 weeks of coverage). The aggregated `[2026]` dimension is server-side and has no row-limit risk.
- Do NOT hardcode dashboard totals or scale segments to match a screenshot.
- Do NOT recreate `classify_2026.py` — the dimension lives in the model now, query it directly.
- DO write `Page Groups [2026]` exactly (with brackets) in prompts. Always quote `"Tier 1"` and `"Tier 2"` verbatim — without quotes, the MCP NL layer sometimes mistranslates to `"T1"`/`"T2"` which returns empty.

**If `[2026]` ever stops working** (rolled back, renamed, etc.): fall back to legacy `GA4 First Visit Page URL Groups` on the same topic. Totals will be ~5-15% under the dashboard. Flag the fallback in the report captions.

#### Chart generation

Generate eight charts using Python matplotlib. Upload each to Google Drive for hosting.

#### Chart 1: Return on Organic — Cohort Step-Line Chart

Using data from **1B**, generate a stepped-line chart:

```python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from collections import defaultdict
import json, urllib.request, ssl, base64

# 1. Parse the Omni data into {cohort_month: [(days, ltv_increment), ...]}
# 2. Sort by days per cohort and compute cumulative sums
# 3. Sample every 5 days for chart data

# Cohort colors (consistent order):
colors = ["#4A90D9", "#F5A623", "#D66B9E", "#50C1B8", "#E8884F", "#7AB648", "#8B5CF6"]

fig, ax = plt.subplots(figsize=(12, 5.5))

for i, (label, cum_points) in enumerate(cohorts.items()):
    x = [p[0] for p in cum_points]  # days
    y = [p[1] / 1000 for p in cum_points]  # £k
    ax.step(x, y, where='post', color=colors[i], linewidth=2, label=label)
    # End label with final value
    ax.annotate(f'£{y[-1]:.0f}K', xy=(x[-1], y[-1]), fontsize=8,
                color=colors[i], fontweight='bold',
                xytext=(5, 0), textcoords='offset points', va='center')

ax.set_title('Return on Organic', fontsize=16, fontweight='bold', loc='left')
ax.set_xlabel('Number of Days (After Last Day of Cohort)')
ax.set_ylabel('V2 LTV Return')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'£{x:,.0f}K'))
ax.set_xlim(-32, 100)
ax.set_ylim(0, 500)
ax.legend(loc='upper left', bbox_to_anchor=(0.75, 1), frameon=True, fontsize=9)
ax.grid(True, alpha=0.3)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig('/tmp/cohort_chart.png', dpi=150, bbox_inches='tight', facecolor='white')
```

#### Chart 2: LTV by Page Group — Stacked Bar Chart

Using data from **1C** (already aggregated server-side by `GA4 First Visit - Page Group`), generate a stacked bar chart:

```python
# Parse rows: keys are 'GA4 First Visit Timestamp Month', 'GA4 First Visit - Page Group', 'v2 Return LTV (£)'
# Build {month: {group: ltv}}; sort months chronologically with datetime.strptime(m, '%b %Y')
# Sort groups by total descending (legend order)

# Color map for legacy Page Groups (matches charts 3/4/5):
color_map = {
    "Features": "#FF8DB4",            # pink
    "Avatars": "#3B4A8F",             # dark blue
    "Tools": "#7AB648",               # green
    "Blog": "#F5D97A",                # yellow
    "Use Cases": "#6FA8DC",           # light blue
    "DE": "#4A9B4E",                  # dark green
    "FR": "#F5A96B",                  # orange
    "ES": "#E8C382",                  # beige
    "Alternatives": "#FF8FC9",        # pink light
    "Case Studies": "#F5A623",        # orange
    "Glossary": "#D14545",            # red
    "Service Providers": "#8B3F9E",   # purple
    "Templates / Examples": "#9B59B6",# purple
    "Integrations": "#3DB3A8",        # teal
}

fig, ax = plt.subplots(figsize=(13, 6.5))
# Plot stacked bars per month
# Add total labels on top of each bar (sum of segments — these are real, not scaled)
# Add red dashed target line at £1M (y=1000 since values in £K)
# Title: "Custom First Touch Attribution - Organic Only - T1-2\nExcluding HP, Pricing, Book Demo, Free AI Video Page, Other - LTV Return - MATURING\n(legacy Page URL Groups — totals ~5-15% under dashboard [2026] CASE; trends & proportions accurate)"
plt.savefig('/tmp/ltv_stacked_bar.png', dpi=150, bbox_inches='tight', facecolor='white')
```

#### Chart 3: Weekly Clicks by Page Group — Stacked Bar Chart

Using data from **1D**, generate a stacked bar chart of weekly clicks:

```python
# Parse Omni data into {week: {page_group: clicks}}
# Sort weeks chronologically using datetime.strptime(week, "%b %d, %Y")
# Exclude current incomplete week (if present)
# Same color_map as Chart 2
# figsize=(14, 6), width=0.7
# Add total labels on top of each bar (rotated 90°, fontsize=6)
# Week labels shortened to "Mon DD" format, rotated 45°
# Title: "Weekly Clicks by Page Group (T1-2, excl HP/Pricing/Book Demo/Other)"
# Y-axis: plain numbers with comma separator
plt.savefig('/tmp/weekly_clicks_chart.png', dpi=150, bbox_inches='tight', facecolor='white')
```

#### Chart 4: Weekly Contacts by Page Group (from 1G) — Stacked Bar Chart

Using data from **1G** (already aggregated server-side by `GA4 First Visit - Page Group`), generate a stacked bar chart:

```python
# Parse rows directly: keys are 'GA4 First Visit Timestamp Week', 'GA4 First Visit - Page Group', 'Total Contact Count'
# Build {week: {group: count}}; sort weeks chronologically
# Use the same legacy-groups color_map as Chart 2
# figsize=(14, 6), width=0.7
# Title: "Weekly Contacts by Page Group (T1-2, Organic, excl HP/Pricing/Book Demo/Other)"
# Verify: should show all 24 weeks (no row-limit truncation since we aggregate server-side)
plt.savefig('/tmp/weekly_contacts_chart.png', dpi=150, bbox_inches='tight', facecolor='white')
```

#### Chart 5: Weekly MQLs by Page Group — Stacked Bar Chart

Using data from **1I** (already aggregated server-side), generate a stacked bar chart:

```python
# Parse rows: keys are 'GA4 First Visit Timestamp Week', 'GA4 First Visit - Page Group', 'Contact MQL Count'
# Build {week: {group: count}}; same color_map and formatting as Chart 4.
# Title: "Weekly MQLs by Page Group (T1-2, Organic, excl HP/Pricing/Book Demo/Other)"
plt.savefig('/tmp/weekly_mqls_chart.png', dpi=150, bbox_inches='tight', facecolor='white')
```

#### Chart 6: Weekly HI MQLs by Page Group — Stacked Bar Chart

Using data from **1K**, generate a stacked bar chart of weekly High Intent MQLs (Booked Demo):

```python
# Same approach as Charts 4/5 but with HI MQL count (Booked Demo)
# Title: "Weekly High Intent MQLs by Page Group (T1-2, Organic, Booked Demo)"
plt.savefig('/tmp/weekly_hi_mqls_chart.png', dpi=150, bbox_inches='tight', facecolor='white')
```

#### Chart 7: Weekly AI Referral Sessions — Stacked Bar Chart

Using data from **1L**, generate a stacked bar chart:

```python
# Group sources: ChatGPT (contains "chatgpt"), Perplexity (perplexity.ai), Gemini (gemini.google.com),
# Claude (claude.ai), Copilot (copilot.microsoft/copilot.cloud), Grok (grok.com)
# Colors: ChatGPT=#F5A623, Perplexity=#9ACD32, Gemini=#4A90D9, Claude=#8B5CF6, Copilot=#E85454, Grok=#2E8B57
# Title: "Weekly AI Referral Sessions (T1-2, Referral Medium, excl HP/Pricing/Other)"
plt.savefig('/tmp/weekly_ai_referral_chart.png', dpi=150, bbox_inches='tight', facecolor='white')
```

#### Chart 8: Weekly Self-Reported AI Chatbot Contacts — Simple Bar Chart

Using data from **1M**, generate a simple (non-stacked) bar chart:

```python
# Single color bars: #F5A623
# Title: "Weekly Self-Reported 'AI Chatbot' Contacts (T1-2)"
plt.savefig('/tmp/weekly_self_reported_chart.png', dpi=150, bbox_inches='tight', facecolor='white')
```

#### Upload to Google Drive

For each chart, upload to the shared Google Drive folder:

```python
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

with open('/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gdrive-token.pickle', 'rb') as f:
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

gdrive_url = f"https://lh3.googleusercontent.com/d/{file.get('id')}"
```

**Note:** If the token expires, re-run the OAuth flow:
```python
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file(
    '/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gdrive-oauth-client.json',
    ['https://www.googleapis.com/auth/drive.file']
)
creds = flow.run_local_server(port=0)
import pickle
with open('/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gdrive-token.pickle', 'wb') as f:
    pickle.dump(creds, f)
```

### Step 3: Process the text data

For each dataset:

**Cohorts (1A):** Format as `{Month}: £{value}k ({change vs previous report})`. Round to nearest £k. To calculate the change: fetch the Notion page and read the PREVIOUS report's cohort values (the report just below the new one). Compare each month's current value to what it was in the previous report. If a month is new (wasn't in the previous report), show "(new)". If the value hasn't changed, show "(no changes)". Otherwise show +Xk or -Xk. Show the last 6 months INCLUDING the current calendar month even if it's still in formation — the freshest month gets the "(new)" label on its first appearance and "+Xk" thereafter. Never stop at the previous complete month.

**Clicks (1E + 1F):**
- Show total clicks with WoW change % at the top
- List the top 5-6 pages with the biggest positive WoW click change under "Up:"
- List the top 5-6 pages with the biggest negative WoW click change under "Down:"
- Format each as: `- [URL](URL) +/-N (current vs previous)`

**Contacts (1H):** Calculate WoW change (current - previous) for each page. Show top 5-7 pages with biggest positive change under "Up:" and top 5-7 with biggest negative change under "Down:". Format: `- [URL](URL) +/-N (current vs previous)`. Strip UTM params from URLs.

**MQLs (1J):** Same approach — calculate WoW change, sort by change. Show top 5 biggest gainers under "Up:" and top 5 biggest losers under "Down:". Format: `+/-N (current vs previous)`.

**High Intent MQLs (1L):** Same as MQLs. Top 5 each direction.

**AI Search Referral (1M):** Build a Notion table with columns: Week, ChatGPT, Gemini, Claude, Perplexity, Copilot, Grok, Total. Group sources using CONTAINS: "chatgpt" → ChatGPT, "perplexity.ai" → Perplexity, "gemini.google.com" → Gemini, "claude.ai" → Claude, "copilot.microsoft" or "copilot.cloud" → Copilot, "grok.com" → Grok. Also generate a stacked bar chart (Chart 6). Sort chronologically. Exclude current incomplete week. ~96% accuracy vs dashboard.

**Self-Reported (1N):** Build a Notion table with columns: Week, Contacts. Also generate a simple bar chart (Chart 7). Sort chronologically. Exclude current incomplete week.

### Step 4: Determine the report date

Use today's date for the report heading. Format as: `Dth/st/nd/rd Month YYYY` (e.g. "6th April 2026").

### Step 5: Compose the Notion content

Build the full report following this EXACT structure (using Notion-flavored markdown with tabs for indentation inside the toggle):

```
# {Date} {toggle="true"}
	![Return on Organic]({cohort_chart_imgur_url})
	![LTV Return by Page Group]({stacked_bar_imgur_url})
	{Cohort lines — one per month}
	## Weekly Results
	### Clicks
	![Weekly Clicks by Page Group]({weekly_clicks_chart_imgur_url})
	**Total Clicks (all tiers, all pages):** {current} (prev {previous}) — **{+/-X.X% WoW}**
	**Total Clicks (all tiers, excl HP/Pricing/Book Demo/Other/Santa/Free AI Video):** {current} (prev {previous}) — **{+/-X.X% WoW}**
	*Excluding HP, Pricing, Book Demo, Other — T1-2 only*
	Up:
	{bullet list of top pages up — format: - [URL](URL) +/-N (current vs previous)}
	Down:
	{bullet list of top pages down — format: - [URL](URL) +/-N (current vs previous)}
	<empty-block/>
	### Contacts
	![Weekly Contacts by Page Group]({weekly_contacts_chart_imgur_url})
	*Custom First Touch Attribution — Organic Traffic Only — Excluding HP, Pricing, Book Demo, Other*
	Up:
	{bullet list}
	Down:
	{bullet list}
	<empty-block/>
	### MQLs
	![Weekly MQLs by Page Group]({weekly_mqls_chart_imgur_url})
	*Custom First Touch Attribution — Organic Traffic Only — Excluding HP, Pricing, Book Demo, Other*
	Up:
	{bullet list with (current vs previous)}
	Down:
	{bullet list with (current vs previous)}
	<empty-block/>
	### High Intent MQLs
	![Weekly High Intent MQLs by Page Group]({weekly_hi_mqls_chart_gdrive_url})
	*Custom First Touch Attribution — Organic Traffic Only — Excluding HP, Pricing, Book Demo, Other — Booked Demo only*
	Up:
	{bullet list with (current vs previous)}
	Down:
	{bullet list with (current vs previous)}
	<empty-block/>
	## AI Search
	### Referral
	![Weekly AI Referral Sessions]({ai_referral_chart_imgur_url})
	*NON-BRAND weekly sessions from referral AI tools by source (T1-2, excl HP/Pricing/Book Demo/Other)*
	{Notion table — 24 weeks, columns: Week, ChatGPT, Gemini, Claude, Perplexity, Copilot, Grok, Total}
	<empty-block/>
	### Self-reported Lead Source
	![Weekly AI Chatbot Self-Reported Contacts]({self_reported_chart_imgur_url})
	*Self Reported Lead Source = AI Chatbot — T1-2 — weekly contacts*
	{Notion table — 24 weeks, columns: Week, Contacts}
	<empty-block/>
	## Mention Rate
	![Mention Rate Trend]({mention_rate_chart_url})
	*Weekly mention rate (%) across AI providers — US — category prompts*
	**Latest period averages:**
	{bullet list of top ~10 competitors by mention_rate, Synthesia bolded as own brand}
	<empty-block/>
	### Share of Voice
	![Share of Voice]({share_of_voice_chart_url})
	*Average share of voice (%) — US — category prompts*
	{bullet list of top ~10 competitors by share_of_voice, Synthesia bolded}
	<empty-block/>
	## Roadmap
	<mention-page url="https://www.notion.so/synthesia/21fc16d22bf18067b241f4d9fa02c309"/>
```

**IMPORTANT formatting rules:**
- ALL content inside the toggle heading MUST be indented with one tab
- Table rows inside the toggle need two tabs
- Table cells need three tabs
- Use `<table fit-page-width="true" header-row="true" header-column="true">` for all tables
- URLs in bullet lists should be formatted as `[URL](URL)` with the full https:// URL
- Strip UTM parameters from page URLs before displaying (everything after `?utm_` or `?gclid` or `?hsa_`)
- For pages that only appear in one week (current or previous but not both), the missing week count is 0
- Charts are embedded as `![caption](imgur_url)` and placed at the TOP of the toggle, before the cohort text lines

### Step 6: Post to Notion

Use `mcp__notion__notion-update-page` with:
- **page_id:** `214c16d22bf1806ea205fc82085149a8`
- **command:** `update_content`
- Find the first `# ` heading that starts a date toggle (e.g. `# 3rd April 2026 {toggle="true"}`) and insert the new report BEFORE it
- The `old_str` should match the first existing date toggle heading
- The `new_str` should be: new report content + newline + the matched old heading

### Step 7: Confirm

Tell the user the report has been posted and summarize:
- Report date
- Total clicks and WoW change
- Number of pages up/down for clicks and contacts
- AI referral trend (latest week total vs previous)
- Any notable movements

## Important Notes
- If the Omni MCP is not connected, ask the user to run `! /mcp` to reconnect
- The Notion page ID is always `214c16d22bf1806ea205fc82085149a8`
- The Roadmap section always links to `https://www.notion.so/synthesia/21fc16d22bf18067b241f4d9fa02c309`
- The Omni model ID is always `6a5202c7-3bf0-4daa-8a48-3aaa6cca1eea`
- Never include the current incomplete week in weekly tables
- For the AI referral table, the first week may be partial — include it anyway for context
- Chart images are uploaded to Google Drive folder `1Ay76vQA2rt0PFPZ0RLE5oTklW7Uv4ELe` using OAuth credentials at `.credentials/gdrive-token.pickle`. If token expires, re-run OAuth flow with `.credentials/gdrive-oauth-client.json`
- The cohort chart data comes from `rep_marketing__return_on_organic` — daily V2 LTV increments that must be cumulatively summed per cohort
- The stacked bar chart data comes from `Contact & Account Intent` topic — filters: GA4 First Visit Medium = organic, Source = google/bing, Country Tier = Tier 1 or Tier 2, excluding HP/Pricing/Book Demo/Free AI Video/Other/Santa page groups
- For Country Tier filtering: use `Country Tier Adj` with values `T1 - US`, `T1 - ex. US`, `T2` if `Country Tier` with `Tier 1`/`Tier 2` returns empty results

## Accuracy Notes

All queries now use `d_salesforce__contacts` topic for contacts/MQLs/HI MQLs (both charts and flat numbers).

**Page Groups [2026] (1C, 1G, 1I, 1K):** Promoted to the shared model on 2026-04-28 by Chris Mee. Use `GA4 First Visit - Page Groups [2026]` directly in prompts (with the brackets). Charts now match the dashboard's bucketing (Video Generation, Avatar singular, Translation, Voice, Features/Tools Other, etc.) instead of legacy buckets. Small ±5% total differences may still appear depending on exact filter combination (Country Tier vs Country Tier Adj, source filter applied or not) — those are filter-specific, not field-specific.

**AI Referral non-brand filter (1L):** Must use `Landing Page Path Groups 1` (not `seo_page_groups`). Excluding Homepage via `landing_page_path_groups_1` drops sessions landing on `/`, `/es`, `/fr`, `/de`, `/pt-br` — these are brand-intent AI referrals. Wrong field gives 2–3× inflated totals. Verify Nov 10 week total ≈ 1,100 (not 3,400) after every pull.
