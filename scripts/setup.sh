#!/bin/bash
# Med Paper Assistant - Setup Script (Linux/macOS)
# Usage: ./scripts/setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Med Paper Assistant Setup..."

# Detect OS and architecture
OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS" in
    Linux*)     PLATFORM="linux";;
    Darwin*)    PLATFORM="darwin";;
    MINGW*|CYGWIN*|MSYS*) PLATFORM="win32";;
    *)          PLATFORM="unknown";;
esac
echo "📍 Detected platform: $PLATFORM ($ARCH)"

# ── macOS: Ensure Homebrew and common tool paths are in PATH ──
if [ "$PLATFORM" = "darwin" ]; then
    # Homebrew (Apple Silicon: /opt/homebrew, Intel: /usr/local)
    if [ -x /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -x /usr/local/bin/brew ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    # Common uv install locations (may not be in PATH in non-interactive shells)
    for _dir in "$HOME/.local/bin" "$HOME/.cargo/bin"; do
        if [ -d "$_dir" ]; then
            case ":$PATH:" in
                *":$_dir:"*) ;;  # already in PATH
                *) export PATH="$_dir:$PATH" ;;
            esac
        fi
    done
fi

# ── Linux: also check ~/.local/bin and ~/.cargo/bin ──
if [ "$PLATFORM" = "linux" ]; then
    for _dir in "$HOME/.local/bin" "$HOME/.cargo/bin"; do
        if [ -d "$_dir" ]; then
            case ":$PATH:" in
                *":$_dir:"*) ;;
                *) export PATH="$_dir:$PATH" ;;
            esac
        fi
    done
fi

# 1. Check uv is available (BEFORE using it)
if ! command -v uv &> /dev/null; then
    echo ""
    echo "❌ uv is not installed."
    echo ""
    echo "📦 Install uv (recommended):"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    if [ "$PLATFORM" = "darwin" ]; then
        echo "   Or via Homebrew:"
        echo "   brew install uv"
        echo ""
    fi
    echo "   After installing, restart your terminal and re-run this script."
    exit 1
fi

UV_VERSION="$(uv --version 2>/dev/null || echo 'unknown')"
echo "📦 Found uv: $UV_VERSION"

# 2. Create virtual environment
echo "📦 Creating Python virtual environment with uv..."
cd "$PROJECT_DIR"

if [ -d ".venv" ]; then
    echo "  Virtual environment already exists, skipping creation"
else
    uv venv
    echo "  ✅ Virtual environment created"
fi

# 3. Install dependencies
echo "🔄 Initializing pinned Git submodules..."
git submodule update --init --recursive
echo "📥 Installing dependencies with uv..."
uv sync --all-extras
echo "  ✅ Dependencies installed"

# 4. Create or migrate .vscode/mcp.json
mkdir -p .vscode
if [ -f .vscode/mcp.json ]; then
    echo "⚙️  .vscode/mcp.json exists — checking for missing servers..."
    uv run python "$SCRIPT_DIR/migrate_mcp_json.py" .vscode/mcp.json || true
else
    echo "⚙️  Creating .vscode/mcp.json (cross-platform)..."
    cat > .vscode/mcp.json << 'EOF'
{
  "inputs": [],
  "servers": {
    "mdpaper": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "${workspaceFolder}", "python", "-m", "med_paper_assistant.interfaces.mcp"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src",
        "MEDPAPER_TOOL_SURFACE": "compact"
      }
    },
    "pubmed-search": {
      "type": "stdio",
      "command": "uvx",
      "args": ["pubmed-search-mcp"],
      "env": {
        "ENTREZ_EMAIL": "medpaper@example.com"
      }
    },
    "cgu": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "${workspaceFolder}/integrations/cgu", "python", "-m", "cgu.server"],
      "env": {
        "CGU_THINKING_ENGINE": "simple"
      }
    },
    "zotero-keeper": {
      "type": "stdio",
      "command": "uvx",
      "args": ["zotero-keeper"]
    },
    "asset-aware": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "${workspaceFolder}/integrations/asset-aware-mcp", "asset-aware-mcp"]
    },
    "drawio": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@drawio/mcp"]
    }
  }
}
EOF
    echo "  ✅ mcp.json created (mdpaper + pubmed-search + cgu + zotero-keeper + asset-aware + drawio)"
fi

echo "✅ Verifying installation..."
uv run python -c "from med_paper_assistant.interfaces.mcp.server import create_server; server = create_server(); print('  MedPaper MCP server loaded')"
uv run --directory integrations/cgu python -c "import cgu; print('  CGU import OK')"
echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "📋 Next Steps:"
echo "  1. In VS Code, press Ctrl+Shift+P (or Cmd+Shift+P on macOS)"
echo "  2. Type 'Developer: Reload Window'"
echo "  3. In Copilot Chat, type / to see mdpaper commands"
echo ""
echo "🔧 Available Commands:"
echo "  /mdpaper.project  - Setup research project"
echo "  /mdpaper.concept  - Develop research concept"
echo "  /mdpaper.strategy - Configure search strategy"
echo "  /mdpaper.draft    - Write paper draft"
echo "  /mdpaper.analysis - Data analysis"
echo "  /mdpaper.clarify  - Improve content"
echo "  /mdpaper.format   - Export to Word"
echo ""
echo "📝 Notes:"
echo "  - Setup uses pinned submodule commits from this repository for reproducibility."
echo "  - To update submodules intentionally, run: git submodule update --remote --merge"
echo "  - Draw.io requires Node.js/npm for the npx fallback."
echo ""
