#!/bin/bash
# Verify Draw.io MCP availability for diagram generation.
# The fallback is an immutable Python MCP SDK2 package snapshot.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DRAWIO_FORK_DIR="$PROJECT_ROOT/integrations/next-ai-draw-io/mcp-server"
DRAWIO_FORK_ENTRY="$DRAWIO_FORK_DIR/src/drawio_mcp_server"
DRAWIO_PACKAGE_SOURCE="https://github.com/u9401066/next-ai-draw-io/archive/9bde25bac9ec160b912ddfebcb5ac037ce565e2f.tar.gz#subdirectory=mcp-server"

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

if ! command -v uvx > /dev/null 2>&1; then
    echo "❌ uvx is not available. Install uv to run the pinned Draw.io SDK2 snapshot."
    exit 1
fi

uvx --python 3.12 --from "$DRAWIO_PACKAGE_SOURCE" drawio-mcp-server --help > /dev/null 2>&1 &
DRAWIO_PID=$!
sleep 8

if kill -0 "$DRAWIO_PID" > /dev/null 2>&1; then
    kill "$DRAWIO_PID" > /dev/null 2>&1 || true
    wait "$DRAWIO_PID" 2>/dev/null || true
    echo "✅ Pinned Draw.io MCP 2.0.0 / SDK2 is reachable via uvx"
    echo "   Commit: 9bde25bac9ec160b912ddfebcb5ac037ce565e2f"
    echo "   You can now use Draw.io MCP tools directly in Copilot Agent mode."
else
    wait "$DRAWIO_PID"
    STATUS=$?
    if [ "$STATUS" -eq 0 ]; then
        echo "✅ Pinned Draw.io MCP 2.0.0 / SDK2 is available via uvx"
        echo "   Commit: 9bde25bac9ec160b912ddfebcb5ac037ce565e2f"
        echo "   You can now use Draw.io MCP tools directly in Copilot Agent mode."
    else
        echo "❌ Failed to launch the pinned Draw.io SDK2 snapshot"
        exit 1
    fi
fi
