# Claude Code Setup

My complete Claude Code configuration — skills, MCP servers, plugins, tools, and settings.

## Skills

Custom skills located in `skills/`. Copy to `.claude/skills/` to use.

| Skill | Description |
|---|---|
| **keyword-research** | SEO keyword research — seed expansion, intent classification, clustering, prioritisation. Integrates with Ahrefs MCP. |
| **schema-markup** | Bespoke JSON-LD structured data for any page type. Based on Kelly Sheppard's methodology. |

## MCP Servers

MCP server configs located in `mcps/`. Copy to your project's `.mcp.json` to use.

| Server | Description |
|---|---|
| **Ahrefs** | SEO data — organic keywords, backlinks, domain ratings, SERP analysis, keyword research |
| **Firecrawl** | Web scraping, crawling, search, and AI extraction |

## Plugins

Installed from the official Claude Code marketplace:

| Plugin | Status | Description |
|---|---|---|
| **github** | Enabled | GitHub integration via MCP |
| **frontend-design** | Disabled | UI/frontend design assistance from Anthropic |

## Tools

Custom tools located in `tools/`.

### PageCopy (`tools/page-editor/`)

Clone any webpage locally with inline editing tools.

```bash
./pagecopy https://example.com/page        # default port 8000
./pagecopy https://example.com/page 3000   # custom port
```

**On-page tools:**
- **Edit Text** (Alt+E) — click any text to edit inline
- **Inspect** (Alt+I) — click any element to copy its CSS selector
- **Save** (Alt+S) — save changes to disk
- **Download** (Alt+D) — download clean HTML with embedded images

## Settings

Settings templates located in `config/`.

| File | Description |
|---|---|
| `settings.json` | Global Claude Code settings (`~/.claude/settings.json`) |
| `project-settings.json` | Project-level settings (`.claude/settings.local.json`) |

## Installation

```bash
# Clone the repo
git clone https://github.com/Gfako/claude-code.git

# Skills — copy to your project
cp -r claude-code/skills/keyword-research your-project/.claude/skills/
cp -r claude-code/skills/schema-markup your-project/.claude/skills/

# MCP servers — merge into your project's .mcp.json
cat claude-code/mcps/ahrefs.json

# PageCopy tool — copy anywhere on your PATH
cp claude-code/tools/page-editor/pagecopy /usr/local/bin/
cp claude-code/tools/page-editor/editor.js /usr/local/bin/

# Settings — copy to ~/.claude/
cp claude-code/config/settings.json ~/.claude/settings.json
```
