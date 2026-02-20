#!/bin/bash
# Test script for MedPaper Assistant VS Code Extension

echo "🧪 MedPaper Assistant Extension Test Guide"
echo "==========================================="
echo ""

VSIX_PATH="/home/eric/workspace251125/vscode-extension/medpaper-assistant-0.2.0.vsix"

# Check if vsix exists
if [ ! -f "$VSIX_PATH" ]; then
    echo "❌ VSIX not found. Run build first:"
    echo "   cd /home/eric/workspace251125/vscode-extension && ./scripts/build.sh"
    exit 1
fi

echo "📦 VSIX Location: $VSIX_PATH"
echo "📏 Size: $(du -h "$VSIX_PATH" | cut -f1)"
echo ""

echo "📋 Installation Methods:"
echo ""
echo "Method 1: VS Code Command Line"
echo "  code --install-extension $VSIX_PATH"
echo ""
echo "Method 2: VS Code GUI"
echo "  1. Open VS Code"
echo "  2. Press Ctrl+Shift+P → 'Extensions: Install from VSIX...'"
echo "  3. Select: $VSIX_PATH"
echo ""
echo "Method 3: Copy to local machine"
echo "  scp eric@192.168.1.111:$VSIX_PATH ."
echo "  code --install-extension medpaper-assistant-0.2.0.vsix"
echo ""

echo "🔍 After Installation, Verify:"
echo "  1. Open VS Code Extensions (Ctrl+Shift+X)"
echo "  2. Search: 'MedPaper'"
echo "  3. Should see 'MedPaper Assistant' installed"
echo ""

echo "🧪 Test Checklist:"
echo "  [ ] Extension appears in Extensions list"
echo "  [ ] MCP Server listed in 'MCP: List Servers'"
echo "  [ ] @mdpaper chat participant available"
echo "  [ ] /search, /draft, /concept commands work"
echo "  [ ] /autopaper shows 9-Phase Pipeline"
echo "  [ ] /help shows all commands"
echo "  [ ] Agent mode can use mdpaper tools"
echo "  [ ] Command: 'MedPaper: Auto Paper' opens chat"
echo ""

echo "📊 Expected Output Channel:"
echo "  View → Output → Select 'MedPaper Assistant'"
echo "  Should show: 'MedPaper Assistant activated successfully!'"
