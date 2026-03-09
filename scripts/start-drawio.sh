#!/bin/bash
# Start Draw.io web app for diagram generation
# Run this before using drawio MCP tools in Copilot

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DRAWIO_DIR="$PROJECT_ROOT/integrations/next-ai-draw-io"

# ── Ensure common tool paths are in PATH (macOS + Linux) ──
if [ "$(uname -s)" = "Darwin" ]; then
    if [ -x /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -x /usr/local/bin/brew ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
fi

echo "🎨 Starting Draw.io web app..."
echo "   URL: http://localhost:3000"
echo "   Press Ctrl+C to stop"
echo ""

if [ ! -d "$DRAWIO_DIR" ]; then
    echo "❌ Draw.io directory not found: $DRAWIO_DIR"
    echo "   Draw.io MCP is now managed via uvx (configured in .vscode/mcp.json)."
    echo "   You don't need this script unless you have the next-ai-draw-io submodule."
    exit 1
fi

cd "$DRAWIO_DIR"

# Check if npm dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies first..."
    npm install
fi

npm run dev
