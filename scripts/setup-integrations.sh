#!/bin/bash
# Setup script for med-paper-assistant integrations
# Draw.io MCP now uses the official npm package @drawio/mcp.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DRAWIO_FORK_DIR="$PROJECT_ROOT/integrations/next-ai-draw-io/mcp-server"
DRAWIO_WORKSPACE_DIR="$PROJECT_ROOT/integrations/drawio-mcp"

echo "🔧 Setting up med-paper-assistant integrations..."
echo ""

# ── Ensure common tool paths are in PATH (macOS + Linux) ──
if [ "$(uname -s)" = "Darwin" ]; then
    if [ -x /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -x /usr/local/bin/brew ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
fi
for _dir in "$HOME/.local/bin" "$HOME/.cargo/bin"; do
    if [ -d "$_dir" ]; then
        case ":$PATH:" in
            *":$_dir:"*) ;;
            *) export PATH="$_dir:$PATH" ;;
        esac
    fi
done

# Check for uv/uvx
if ! command -v uvx &> /dev/null; then
    echo "❌ uvx is not available. Please install uv first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    if [ "$(uname -s)" = "Darwin" ]; then
        echo "   Or: brew install uv"
    fi
    exit 1
fi

echo "✅ uvx is available"

if [ -d "$DRAWIO_FORK_DIR/src/drawio_mcp_server" ]; then
    echo "✅ forked Draw.io MCP detected at integrations/next-ai-draw-io/mcp-server"
elif [ -f "$DRAWIO_WORKSPACE_DIR/src/index.js" ]; then
    echo "✅ workspace Draw.io MCP detected at integrations/drawio-mcp"
elif command -v drawio-mcp > /dev/null 2>&1; then
    echo "✅ drawio-mcp binary is available"
elif command -v npx > /dev/null 2>&1; then
    echo "✅ npx is available for official Draw.io MCP startup"
else
    echo "⚠️  Draw.io MCP requires either a drawio-mcp binary or npx (Node.js/npm)."
fi

# Verify drawio-mcp can be resolved
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Verifying Draw.io MCP Server..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "  Draw.io MCP prefers your forked submodule at integrations/next-ai-draw-io/mcp-server when present."
echo "  Otherwise it falls back to an official checkout, installed drawio-mcp binary, or npm package @drawio/mcp."
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
echo "  🎨 drawio     — CONSORT/PRISMA flowcharts (forked submodule → official checkout → package fallback)"
echo "  📖 zotero     — Zotero reference import (via uvx)"
echo ""
echo "💡 Verify Draw.io MCP availability:"
echo "   ./scripts/start-drawio.sh"
echo ""
