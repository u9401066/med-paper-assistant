#!/bin/bash
# Setup script for med-paper-assistant integrations
# Draw.io MCP is now installed via uvx (no submodule needed)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🔧 Setting up med-paper-assistant integrations..."
echo ""

# Check for uv/uvx
if ! command -v uvx &> /dev/null; then
    echo "❌ uvx is not available. Please install uv first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ uvx is available"

# Verify drawio-mcp-server can be resolved
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Verifying Draw.io MCP Server..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "  Draw.io MCP runs via uvx (configured in .vscode/mcp.json)"
echo "  No local installation needed — uvx resolves it on demand."
echo ""

# Check that mcp.json has drawio configured
MCP_JSON="$PROJECT_ROOT/.vscode/mcp.json"
if [ -f "$MCP_JSON" ] && grep -q '"drawio"' "$MCP_JSON"; then
    echo "✅ drawio server already configured in .vscode/mcp.json"
else
    echo "⚠️  drawio server not found in .vscode/mcp.json"
    echo "   Add it manually or check the project documentation."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Integration check complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Available integrations:"
echo "  🎨 drawio     — CONSORT/PRISMA flowcharts (via uvx)"
echo "  📖 zotero     — Zotero reference import (via uvx)"
echo ""
echo "💡 Start Draw.io web app:"
echo "   ./scripts/start-drawio.sh"
echo ""
