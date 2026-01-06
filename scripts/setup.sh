#!/bin/bash
# Med Paper Assistant - Setup Script (Linux/macOS)
# Usage: ./scripts/setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Med Paper Assistant Setup..."

# Detect OS
OS="$(uname -s)"
case "$OS" in
    Linux*)     PLATFORM="linux";;
    Darwin*)    PLATFORM="darwin";;
    MINGW*|CYGWIN*|MSYS*) PLATFORM="win32";;
    *)          PLATFORM="unknown";;
esac
echo "📍 Detected platform: $PLATFORM"

# 1. Create virtual environment
echo "📦 Creating Python virtual environment with uv..."
cd "$PROJECT_DIR"

if [ -d ".venv" ]; then
    echo "  Virtual environment already exists, skipping creation"
else
    uv venv
    echo "  ✅ Virtual environment created"
fi

source .venv/bin/activate

# 2. Install dependenciesecho "🔄 Updating Git submodules..."
git submodule update --init --recursive --remote
echo "📥 Installing dependencies with uv..."
uv sync --all-extras
echo "  ✅ Dependencies installed"

# 3. Create .vscode/mcp.json (cross-platform)
echo "⚙️  Configuring VS Code MCP (cross-platform)..."
mkdir -p .vscode

cat > .vscode/mcp.json << 'EOF'
{
  "inputs": [],
  "servers": {
    "mdpaper": {
      "type": "stdio",
      "command": "${workspaceFolder}/.venv/bin/python",
      "args": ["-m", "med_paper_assistant.interfaces.mcp"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src"
      },
      "platforms": {
        "win32": {
          "command": "${workspaceFolder}/.venv/Scripts/python.exe"
        },
        "linux": {
          "command": "${workspaceFolder}/.venv/bin/python"
        },
        "darwin": {
          "command": "${workspaceFolder}/.venv/bin/python"
        }
      }
    }
  }
}
EOF
echo "  ✅ mcp.json created (cross-platform)"

# 4. Verify installation
echo "✅ Verifying installation..."
python -c "from med_paper_assistant.interfaces.mcp.server import mcp; print(f'  MCP Server loaded: {len(mcp._tool_manager._tools)} tools')"

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
