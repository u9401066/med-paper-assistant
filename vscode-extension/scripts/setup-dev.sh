#!/bin/bash
# Development setup script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔧 Setting up development environment..."

# Install Node.js dependencies
cd "$EXT_DIR"
npm install

# Create necessary directories
mkdir -p bundled/tool
mkdir -p bundled/libs
mkdir -p skills
mkdir -p prompts
mkdir -p media

# Create placeholder icon
if [ ! -f media/icon.png ]; then
    echo "📷 Creating placeholder icon..."
    # Create a simple 128x128 placeholder (requires ImageMagick)
    if command -v convert &> /dev/null; then
        convert -size 128x128 xc:#4a90d9 \
            -fill white -gravity center \
            -pointsize 48 -annotate 0 "MP" \
            media/icon.png
    else
        echo "⚠️ ImageMagick not found. Please add media/icon.png manually."
    fi
fi

echo "✅ Development setup complete!"
echo ""
echo "Next steps:"
echo "  1. Run 'npm run compile' to compile TypeScript"
echo "  2. Press F5 to launch Extension Development Host"
echo "  3. In the new VS Code window, test @mdpaper commands"
