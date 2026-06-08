#!/bin/bash
# Content Brief Toolkit — Setup Script
# Run: cd /path/to/your/project && /path/to/content-brief-toolkit/setup.sh

set -e

TOOLKIT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR=$(pwd)

echo ""
echo "=== Content Brief Toolkit Setup ==="
echo ""
echo "Project directory: $PROJECT_DIR"
echo ""

# 1. Install skills
if [ -f "$PROJECT_DIR/.claude/skills/content-brief-simplified/SKILL.md" ] && [ -f "$PROJECT_DIR/.claude/skills/content-brief/SKILL.md" ]; then
    echo "✅ Skills already installed — skipping"
else
    echo "Installing skills..."
    mkdir -p "$PROJECT_DIR/.claude/skills/content-brief"
    mkdir -p "$PROJECT_DIR/.claude/skills/content-brief-simplified"
    cp "$TOOLKIT_DIR/skills/content-brief/SKILL.md" "$PROJECT_DIR/.claude/skills/content-brief/SKILL.md"
    cp "$TOOLKIT_DIR/skills/content-brief-simplified/SKILL.md" "$PROJECT_DIR/.claude/skills/content-brief-simplified/SKILL.md"
    sed -i '' "s|/Users/george.fakorellis/Desktop/SEO Custom Projects|$PROJECT_DIR|g" "$PROJECT_DIR/.claude/skills/content-brief/SKILL.md" 2>/dev/null || sed -i "s|/Users/george.fakorellis/Desktop/SEO Custom Projects|$PROJECT_DIR|g" "$PROJECT_DIR/.claude/skills/content-brief/SKILL.md"
    sed -i '' "s|/Users/george.fakorellis/Desktop/SEO Custom Projects|$PROJECT_DIR|g" "$PROJECT_DIR/.claude/skills/content-brief-simplified/SKILL.md" 2>/dev/null || sed -i "s|/Users/george.fakorellis/Desktop/SEO Custom Projects|$PROJECT_DIR|g" "$PROJECT_DIR/.claude/skills/content-brief-simplified/SKILL.md"
    echo "✅ Skills installed"
fi

# 2. Create directories
mkdir -p "$PROJECT_DIR/.credentials"
mkdir -p "$PROJECT_DIR/content-briefs"
echo "✅ Directories ready"

# 3. Check Python dependencies
echo ""
MISSING=""
python3 -c "import google.oauth2" 2>/dev/null || MISSING="$MISSING google-auth"
python3 -c "import googleapiclient" 2>/dev/null || MISSING="$MISSING google-api-python-client"
python3 -c "import docx" 2>/dev/null || MISSING="$MISSING python-docx"
python3 -c "import matplotlib" 2>/dev/null || MISSING="$MISSING matplotlib"

if [ -z "$MISSING" ]; then
    echo "✅ Python dependencies already installed"
else
    echo "Installing Python dependencies:$MISSING"
    pip3 install $MISSING 2>&1 | tail -3
    echo "✅ Python dependencies installed"
fi

# 4. Check GSC service account
echo ""
if [ -f "$PROJECT_DIR/.credentials/gsc-service-account.json" ]; then
    echo "✅ GSC service account found"
else
    echo "⚠️  GSC service account not found"
    echo "   Place your JSON file at: $PROJECT_DIR/.credentials/gsc-service-account.json"
fi

# 5. MCP reference
echo ""
cp "$TOOLKIT_DIR/mcp-config-template.json" "$PROJECT_DIR/mcp-config-template.json" 2>/dev/null
echo "MCP servers needed (check via /mcp in Claude Code):"
echo "  - ahrefs  → HTTP → https://api.ahrefs.com/mcp/mcp"
echo "  - airops  → HTTP → https://app.airops.com/mcp"
echo "  - notion  → HTTP → https://mcp.notion.com/mcp (optional)"

# 6. Summary
echo ""
echo "=== Setup Complete ==="
echo ""
[ -f "$PROJECT_DIR/.claude/skills/content-brief-simplified/SKILL.md" ] && echo "  ✅ /content-brief-simplified skill"
[ -f "$PROJECT_DIR/.claude/skills/content-brief/SKILL.md" ] && echo "  ✅ /content-brief skill"
[ -f "$PROJECT_DIR/.credentials/gsc-service-account.json" ] && echo "  ✅ GSC service account" || echo "  ⚠️  GSC service account — needs setup"
echo ""
echo "To start: cd $PROJECT_DIR && claude"
echo "Then type: /content-brief-simplified"
echo ""
