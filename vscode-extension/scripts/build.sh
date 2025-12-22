#!/bin/bash
# Build script for MedPaper Assistant VS Code Extension

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXT_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$EXT_DIR")"

echo "🔨 Building MedPaper Assistant VS Code Extension..."

# 1. Copy Skills from .claude/skills/
echo "📖 Copying Skills..."
SKILLS_SRC="$ROOT_DIR/.claude/skills"
SKILLS_DST="$EXT_DIR/skills"

if [ -d "$SKILLS_SRC" ]; then
    # Copy mdpaper-related skills
    for skill in literature-review concept-development parallel-search \
                 project-management draft-writing reference-management \
                 word-export concept-validation; do
        if [ -d "$SKILLS_SRC/$skill" ]; then
            mkdir -p "$SKILLS_DST/$skill"
            cp "$SKILLS_SRC/$skill/SKILL.md" "$SKILLS_DST/$skill/" 2>/dev/null || true
        fi
    done
fi

# 2. Copy Prompts from .github/prompts/
echo "📋 Copying Prompts..."
PROMPTS_SRC="$ROOT_DIR/.github/prompts"
PROMPTS_DST="$EXT_DIR/prompts"

if [ -d "$PROMPTS_SRC" ]; then
    # Copy mdpaper-related prompts
    for prompt in mdpaper.write-paper mdpaper.literature-survey mdpaper.manuscript-revision; do
        if [ -f "$PROMPTS_SRC/$prompt.prompt.md" ]; then
            cp "$PROMPTS_SRC/$prompt.prompt.md" "$PROMPTS_DST/" 2>/dev/null || true
        fi
    done
fi

# 3. Build Python wheel
echo "🐍 Building Python wheel..."
cd "$ROOT_DIR"
if command -v uv &> /dev/null; then
    uv build --wheel --out-dir "$EXT_DIR/bundled/tool"
else
    pip wheel . --wheel-dir "$EXT_DIR/bundled/tool" --no-deps
fi

# 4. Compile TypeScript
echo "📦 Compiling TypeScript..."
cd "$EXT_DIR"
npm install
npm run compile

# 5. Package extension
echo "📦 Packaging extension..."
npm run package

echo "✅ Build complete! Extension package: $EXT_DIR/*.vsix"
