# Content Brief Toolkit — Setup Guide

Automated SEO content briefs using Claude Code + Ahrefs + AirOps + GSC + Notion.

**To get started, open Claude Code and paste this:**

```
Please read the file at ~/Desktop/content-brief-toolkit/SETUP-GUIDE.md and set everything up for me step by step
```

(Change the path if you unzipped it somewhere else.)

**What Claude Code will do:**
- Install the skills into the right directories
- Install Python dependencies
- Ask you where your GSC service account JSON is (or help you set one up)
- Guide you through adding any missing MCP servers
- Verify everything works
- You don't need to understand the technical details — just answer Claude's questions.

---

## Step 1: Run the setup script

Open your terminal and run:

```bash
cd ~/Desktop/SEO-Projects    # or wherever your project folder is
./path/to/content-brief-toolkit/setup.sh
```

This automatically:
- Installs both skills into `.claude/skills/` in your project
- Creates `.credentials/` and `content-briefs/` directories
- Installs Python dependencies
- Updates all file paths to match your machine

---

## Step 2: Set up GSC service account

The skills pull Google Search Console data automatically. You need a service account JSON file with read access to `sc-domain:synthesia.io`.

**Claude Code: Ask the user the following:**

1. "Do you already have a GSC service account JSON file? If yes, what's the file path?"
2. If they have one:
   - Copy it to `<project-dir>/.credentials/gsc-service-account.json`
   - Update the path in both SKILL.md files to point to the correct location
3. If they don't have one:
   - Tell them to ask George Fakorellis or check the SEO team's shared credentials
   - The file should look like a JSON with `"type": "service_account"`, `"project_id"`, `"private_key"`, `"client_email"` etc.
   - Once they have it, copy it to `<project-dir>/.credentials/gsc-service-account.json`
4. After placing the file, update the GSC path in both skill files:
   - `.claude/skills/content-brief/SKILL.md` — find the line with `KEY_PATH = '...'` and update it
   - `.claude/skills/content-brief-simplified/SKILL.md` — same thing

**The skills reference the GSC path in two places:**
- The `KEY_PATH` variable in the Python script inside the skill
- The `**Service account JSON:**` line at the top of Phase 2

Both need to match wherever the user's JSON file ends up.

---

## Step 3: Connect MCP servers

The skills need 2 required + 1 optional MCP servers. The toolkit includes a config template (`mcp-config-template.json`) for reference.

### Quick setup

Open Claude Code, type `/mcp`, and add each server:

**Ahrefs (required — needs MCP token)**
1. Type `/mcp` → Add new server
2. Name: `ahrefs`
3. Type: HTTP
4. URL: `https://api.ahrefs.com/mcp/mcp`
5. You need a Bearer token — get it from [ahrefs.com/api/mcp](https://ahrefs.com/api/mcp) or ask George

**AirOps (required — browser auth)**
1. Type `/mcp` → Add new server
2. Name: `airops`
3. Type: HTTP
4. URL: `https://app.airops.com/mcp`
5. No API key needed — authenticates via your browser
6. Make sure you have access to the Synthesia workspace in AirOps

**Notion (optional — browser auth)**
1. Type `/mcp` → Add new server
2. Name: `notion`
3. Type: HTTP
4. URL: `https://mcp.notion.com/mcp`
5. No API key needed — authenticates via browser
6. Briefs auto-publish to Notion if connected. If skipped, briefs save locally only.

### Verify servers are connected

Type `/mcp` in Claude Code. You should see:
- ✅ `ahrefs` — connected
- ✅ `airops` — connected
- ✅ `notion` — connected (optional)

---

## Step 4: Verify it works

1. Open terminal
2. `cd` to your project folder
3. Run `claude`
4. Type `/content-brief-simplified`
5. It should ask you for a target keyword — you're good to go

---

## How to use

### Quick brief (recommended):
Type `/content-brief-simplified` — concise, skimmable, designed for a writer to read in under 1 minute.

### Full brief:
Type `/content-brief` — comprehensive with full SERP analysis, competitor heading structures, off-page data.

### Both will ask you for:
1. **Target keyword** — the primary keyword
2. **Existing page URL** — if refreshing (skip for new content)
3. **Secondary keywords** — provide your own or auto-discover
4. **Target audience** — define it or let it infer from SERP
5. **Brand/country** — defaults to synthesia.io / US

### Output:
- Auto-published to **Notion > Synthesia Blog Content Briefs > Claude Briefs**
- Saved locally to `content-briefs/` in your project folder

---

## The one manual step: AirOps Firecrawl scraping

During a brief, Claude scrapes competitor pages via an AirOps grid. Claude can add URLs and read results, but **can't trigger the workflow** — you do that.

### What happens:

1. Claude adds competitor URLs and says: *"URLs added — please trigger the Firecrawl workflow"*
2. You trigger it in AirOps
3. You tell Claude "ready"

### How to trigger:

1. Go to [AirOps](https://app.airops.com) and log in
2. Open the grid **"Content Brief Automation w Claude / Firecrawl Scrape"** (Grid ID: 61652)
3. You'll see new rows with URLs and empty "Markdown" columns
4. Select all new rows → click **"Run"** on the "Firecrawl Page Scrape" column
5. Wait ~30 seconds for Markdown to populate
6. Tell Claude **"ready"**

```
Grid layout:
┌────────────────────────────┬─────────────────────┬──────────┐
│ URL                        │ Firecrawl Page Scrape│ Markdown │
├────────────────────────────┼─────────────────────┼──────────┤
│ https://competitor.com/... │ ← Click "Run" here  │ (empty)  │
│ https://competitor.com/... │                     │ (empty)  │
└────────────────────────────┴─────────────────────┴──────────┘

After running → Markdown column fills with scraped content
```

This happens once per brief and takes about 1 minute.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Skills don't show when typing `/` | Launch `claude` from the project root, not a subdirectory |
| GSC data empty | Check `.credentials/gsc-service-account.json` exists and has access |
| Ahrefs/AirOps tools not found | Type `/mcp` and check servers are connected |
| Competitor scraping empty | Trigger the AirOps workflow manually (see above) |
| Notion publishing fails | Connect Notion MCP, or skip — briefs save locally |

---

## Questions?

Ask George Fakorellis or the SEO team Slack channel.

---

## Instructions for Claude Code (read this if you are Claude)

When a user asks you to set up this toolkit, follow these steps in order. **Ask for confirmation after each step.**

### Step A: Determine project directory
Ask: "What folder do you want to use as your project directory? This is where briefs will be saved."

### Step B: Install skills
```bash
mkdir -p "$PROJECT_DIR/.claude/skills/content-brief"
mkdir -p "$PROJECT_DIR/.claude/skills/content-brief-simplified"
```
Copy the SKILL.md files from this toolkit into those directories.
Find-and-replace `/Users/george.fakorellis/Desktop/SEO Custom Projects` with `$PROJECT_DIR` in both SKILL.md files.

### Step C: Install Python dependencies
```bash
pip3 install google-auth google-auth-httplib2 google-api-python-client python-docx matplotlib
```

### Step D: Set up GSC
Ask: "Do you have a Google Search Console service account JSON file? If yes, what's the full path to it?"
- If yes: copy it to `$PROJECT_DIR/.credentials/gsc-service-account.json` and update `KEY_PATH` in `.claude/skills/content-brief/SKILL.md`
- If no: tell them to ask George Fakorellis for one

### Step E: Check MCP servers
Ask: "Can you type /mcp and tell me which servers you see?"
For any missing:
- **ahrefs:** /mcp → Add → HTTP → `https://api.ahrefs.com/mcp/mcp` → needs Bearer token from ahrefs.com/api/mcp
- **airops:** /mcp → Add → HTTP → `https://app.airops.com/mcp` → browser auth
- **notion:** /mcp → Add → HTTP → `https://mcp.notion.com/mcp` → browser auth, optional

### Step F: Create output directory
```bash
mkdir -p "$PROJECT_DIR/content-briefs"
```

### Step G: Verify
Tell them: "Setup complete. Start a fresh Claude Code session from your project folder and type /content-brief-simplified to test."
List what's ready (✅) and what needs attention (⚠️).
