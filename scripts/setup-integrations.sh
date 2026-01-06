#!/bin/bash
# Setup script for med-paper-assistant integrations
# This script sets up the next-ai-draw-io integration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DRAWIO_DIR="$PROJECT_ROOT/integrations/next-ai-draw-io"

echo "🔧 Setting up med-paper-assistant integrations..."
echo ""

# Check if submodule is initialized
if [ ! -f "$DRAWIO_DIR/package.json" ]; then
    echo "📦 Initializing git submodules..."
    cd "$PROJECT_ROOT"
    git submodule update --init --recursive
fi

# Setup next-ai-draw-io
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Setting up next-ai-draw-io..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$DRAWIO_DIR"

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "⚠️  Node.js is not installed."
    echo "   The Draw.io web app requires Node.js 18+"
    echo "   Install from: https://nodejs.org/"
    echo ""
    echo "   Continuing with MCP server setup only..."
    SKIP_NEXTJS=true
else
    NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -lt 18 ]; then
        echo "⚠️  Node.js version 18+ required. Found: $(node -v)"
        echo "   Continuing with MCP server setup only..."
        SKIP_NEXTJS=true
    else
        echo "✅ Node.js $(node -v) detected"
        SKIP_NEXTJS=false
    fi
fi

# Install npm dependencies (if Node.js available)
if [ "$SKIP_NEXTJS" = false ]; then
    echo "📦 Installing npm dependencies..."
    npm install
    
    # Setup environment file
    if [ ! -f ".env.local" ]; then
        if [ -f "env.example" ]; then
            cp env.example .env.local
            echo "📝 Created .env.local from template"
            echo "   ⚠️  Please edit .env.local to configure your LLM provider"
        fi
    fi
fi

# Setup MCP server
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔌 Setting up Draw.io MCP Server..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$DRAWIO_DIR/mcp-server"

# Check for uv
if command -v uv &> /dev/null; then
    echo "✅ Using uv for Python package management"
    uv sync
    DRAWIO_PYTHON="$DRAWIO_DIR/mcp-server/.venv/bin/python"
else
    echo "⚠️  uv not found. Falling back to venv + pip..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e .
    DRAWIO_PYTHON="$DRAWIO_DIR/mcp-server/.venv/bin/python"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚙️  Updating VS Code MCP configuration..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Update mcp.json to include drawio server
MCP_JSON="$PROJECT_ROOT/.vscode/mcp.json"
MDPAPER_PYTHON="$PROJECT_ROOT/.venv/bin/python"

# Create updated mcp.json with both servers
cat > "$MCP_JSON" << EOF
{
  "servers": {
    "mdpaper": {
      "command": "$MDPAPER_PYTHON",
      "args": ["-m", "med_paper_assistant.interfaces.mcp.server"],
      "cwd": "$PROJECT_ROOT"
    },
    "drawio": {
      "command": "$DRAWIO_PYTHON",
      "args": ["-m", "drawio_mcp"],
      "cwd": "$DRAWIO_DIR/mcp-server",
      "env": {
        "DRAWIO_API_URL": "http://localhost:3000"
      }
    }
  }
}
EOF

echo "✅ Updated .vscode/mcp.json with both MCP servers"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Integration setup complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Configure LLM provider:"
echo "   Edit: $DRAWIO_DIR/.env.local"
echo ""
echo "2. Start Draw.io web app (Terminal 1):"
echo "   cd $DRAWIO_DIR && npm run dev"
echo ""
echo "3. Reload VS Code:"
echo "   Press Ctrl+Shift+P → 'Developer: Reload Window'"
echo ""
echo "4. Use in Copilot Chat:"
echo "   - mdpaper tools: Paper writing"
echo "   - drawio tools: Diagram generation"
echo ""
echo "💡 Example: 'Create a CONSORT flowchart for my RCT study'"
echo ""
