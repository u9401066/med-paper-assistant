#!/bin/bash
# Build script for MedPaper Assistant VS Code Extension
# Syncs skills/prompts from source, compiles, tests, validates, and packages.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXT_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$EXT_DIR")"

echo "🔨 Building MedPaper Assistant VS Code Extension..."

# 0. Initialize pinned submodules for reproducible builds
echo "🔄 Initializing pinned Git submodules..."
cd "$ROOT_DIR"
git submodule update --init --recursive 2>/dev/null || echo "  ⚠️ Submodule init skipped"
cd "$EXT_DIR"

# ──────────────────────────────────────────────────────
# 1. Sync bundled assets from shared manifest
# ──────────────────────────────────────────────────────
echo "📦 Syncing bundled assets from manifest..."
npm run bundle:sync

# ──────────────────────────────────────────────────────
# 2. Copy Python MCP source (for development)
# ──────────────────────────────────────────────────────
echo "🐍 Copying Python MCP source from manifest..."
npm run bundle:sync-python

# ──────────────────────────────────────────────────────
# 3. Install deps & compile TypeScript
# ──────────────────────────────────────────────────────
echo "📦 Installing dependencies..."
cd "$EXT_DIR"
npm install --silent 2>/dev/null || npm install

echo "📦 Compiling TypeScript..."
npm run compile

# ──────────────────────────────────────────────────────
# 4. Run unit tests
# ──────────────────────────────────────────────────────
echo "🧪 Running tests..."
if npx vitest run --reporter=verbose 2>&1; then
    echo "  → Tests passed ✅"
else
    echo "  ❌ Tests failed! Fix issues before packaging."
    exit 1
fi

# ──────────────────────────────────────────────────────
# 5. Package extension
# ──────────────────────────────────────────────────────
echo "📦 Packaging extension..."
npm run package

# ──────────────────────────────────────────────────────
# 6. Run build validation
# ──────────────────────────────────────────────────────
echo ""
npm run validate -- --skip-tests

echo ""
echo "✅ Build complete! Extension package: $EXT_DIR/*.vsix"
