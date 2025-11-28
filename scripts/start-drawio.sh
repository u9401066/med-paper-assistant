#!/bin/bash
# Start Draw.io web app for diagram generation
# Run this before using drawio MCP tools in Copilot

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DRAWIO_DIR="$PROJECT_ROOT/integrations/next-ai-draw-io"

echo "🎨 Starting Draw.io web app..."
echo "   URL: http://localhost:3000"
echo "   Press Ctrl+C to stop"
echo ""

cd "$DRAWIO_DIR"

# Check if npm dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies first..."
    npm install
fi

npm run dev
