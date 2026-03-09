#!/bin/bash
# Verify Draw.io MCP availability for diagram generation.
# Official Draw.io MCP is distributed as the npm package @drawio/mcp.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DRAWIO_FORK_DIR="$PROJECT_ROOT/integrations/next-ai-draw-io/mcp-server"
DRAWIO_FORK_ENTRY="$DRAWIO_FORK_DIR/src/drawio_mcp_server"
DRAWIO_WORKSPACE_DIR="$PROJECT_ROOT/integrations/drawio-mcp"
DRAWIO_WORKSPACE_ENTRY="$DRAWIO_WORKSPACE_DIR/src/index.js"

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

echo "🎨 Verifying Draw.io MCP..."
echo ""

if [ -d "$DRAWIO_FORK_ENTRY" ]; then
    if ! command -v uv > /dev/null 2>&1; then
        echo "❌ Found forked Draw.io MCP at $DRAWIO_FORK_DIR, but uv is not available."
        exit 1
    fi

    uv run --directory "$DRAWIO_FORK_DIR" python -m drawio_mcp_server --help > /dev/null 2>&1 &
    DRAWIO_PID=$!
    sleep 8

    if kill -0 "$DRAWIO_PID" > /dev/null 2>&1; then
        kill "$DRAWIO_PID" > /dev/null 2>&1 || true
        wait "$DRAWIO_PID" 2>/dev/null || true
        echo "✅ Forked workspace Draw.io MCP is reachable"
        echo "   MCP command: uv run --directory integrations/next-ai-draw-io/mcp-server python -m drawio_mcp_server"
        exit 0
    fi

    wait "$DRAWIO_PID"
    STATUS=$?
    if [ "$STATUS" -eq 0 ]; then
        echo "✅ Forked workspace Draw.io MCP is available"
        echo "   MCP command: uv run --directory integrations/next-ai-draw-io/mcp-server python -m drawio_mcp_server"
        exit 0
    fi

    echo "❌ Failed to launch forked workspace Draw.io MCP from $DRAWIO_FORK_DIR"
    exit 1
fi

if [ -f "$DRAWIO_WORKSPACE_ENTRY" ]; then
    if ! command -v node > /dev/null 2>&1; then
        echo "❌ Found workspace Draw.io MCP at $DRAWIO_WORKSPACE_DIR, but node is not available."
        exit 1
    fi

    node "$DRAWIO_WORKSPACE_ENTRY" --help > /dev/null 2>&1 &
    DRAWIO_PID=$!
    sleep 8

    if kill -0 "$DRAWIO_PID" > /dev/null 2>&1; then
        kill "$DRAWIO_PID" > /dev/null 2>&1 || true
        wait "$DRAWIO_PID" 2>/dev/null || true
        echo "✅ Workspace Draw.io MCP is reachable"
        echo "   MCP command: node integrations/drawio-mcp/src/index.js"
        exit 0
    fi

    wait "$DRAWIO_PID"
    STATUS=$?
    if [ "$STATUS" -eq 0 ]; then
        echo "✅ Workspace Draw.io MCP is available"
        echo "   MCP command: node integrations/drawio-mcp/src/index.js"
        exit 0
    fi

    echo "❌ Failed to launch workspace Draw.io MCP from $DRAWIO_WORKSPACE_DIR"
    exit 1
fi

if command -v drawio-mcp > /dev/null 2>&1; then
    echo "✅ drawio-mcp binary is already installed"
    echo "   MCP command: drawio-mcp"
    exit 0
fi

if ! command -v npx > /dev/null 2>&1; then
    echo "❌ npx is not available. Install Node.js/npm first, or install drawio-mcp globally."
    echo "   Ubuntu/Debian: sudo apt install nodejs npm"
    echo "   macOS: brew install node"
    exit 1
fi

npx -y @drawio/mcp --help > /dev/null 2>&1 &
NPX_PID=$!
sleep 8

if kill -0 "$NPX_PID" > /dev/null 2>&1; then
    kill "$NPX_PID" > /dev/null 2>&1 || true
    wait "$NPX_PID" 2>/dev/null || true
    echo "✅ Official Draw.io MCP is reachable via npx"
    echo "   MCP command: npx -y @drawio/mcp"
    echo "   You can now use Draw.io MCP tools directly in Copilot Agent mode."
else
    wait "$NPX_PID"
    STATUS=$?
    if [ "$STATUS" -eq 0 ]; then
        echo "✅ Official Draw.io MCP is available via npx"
        echo "   MCP command: npx -y @drawio/mcp"
        echo "   You can now use Draw.io MCP tools directly in Copilot Agent mode."
    else
        echo "❌ Failed to launch @drawio/mcp via npx"
        echo "   Try: npm install -g @drawio/mcp"
        exit 1
    fi
fi
