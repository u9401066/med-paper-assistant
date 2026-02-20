#!/bin/bash
# Build script for MedPaper Assistant VS Code Extension

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXT_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$EXT_DIR")"

echo "🔨 Building MedPaper Assistant VS Code Extension..."

# 0. Update Submodules to ensure latest code
echo "🔄 Updating Git submodules..."
cd "$ROOT_DIR"
git submodule update --init --recursive --remote
cd "$EXT_DIR"

# 1. Copy Skills from .claude/skills/
echo "📖 Copying Skills..."
SKILLS_SRC="$ROOT_DIR/.claude/skills"
SKILLS_DST="$EXT_DIR/skills"

if [ -d "$SKILLS_SRC" ]; then
    # Copy ALL research skills + paper-aware hooks
    for skill in literature-review concept-development concept-validation \
                 parallel-search project-management draft-writing \
                 reference-management word-export auto-paper \
                 academic-debate idea-validation manuscript-review \
                 submission-preparation git-precommit; do
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
    # Copy ALL mdpaper prompts + capability index
    for prompt in mdpaper.write-paper mdpaper.literature-survey \
                 mdpaper.manuscript-revision mdpaper.search \
                 mdpaper.concept mdpaper.draft mdpaper.project \
                 mdpaper.format mdpaper.strategy mdpaper.analysis \
                 mdpaper.clarify mdpaper.help; do
        if [ -f "$PROMPTS_SRC/$prompt.prompt.md" ]; then
            cp "$PROMPTS_SRC/$prompt.prompt.md" "$PROMPTS_DST/" 2>/dev/null || true
        fi
    done
    # Copy capability index
    if [ -f "$PROMPTS_SRC/_capability-index.md" ]; then
        cp "$PROMPTS_SRC/_capability-index.md" "$PROMPTS_DST/" 2>/dev/null || true
    fi
fi

# 3. Copy Python MCP source (for development)
echo "🐍 Copying Python MCP source..."
PYTHON_DST_ROOT="$EXT_DIR/bundled/tool"

# MedPaper Assistant
echo "   - med_paper_assistant"
PYTHON_SRC_MDPAPER="$ROOT_DIR/src/med_paper_assistant"
PYTHON_DST_MDPAPER="$PYTHON_DST_ROOT/med_paper_assistant"
if [ -d "$PYTHON_SRC_MDPAPER" ]; then
    rm -rf "$PYTHON_DST_MDPAPER"
    cp -r "$PYTHON_SRC_MDPAPER" "$PYTHON_DST_MDPAPER"
fi

# CGU
echo "   - cgu"
PYTHON_SRC_CGU="$ROOT_DIR/integrations/cgu/src/cgu"
PYTHON_DST_CGU="$PYTHON_DST_ROOT/cgu"
if [ -d "$PYTHON_SRC_CGU" ]; then
    rm -rf "$PYTHON_DST_CGU"
    cp -r "$PYTHON_SRC_CGU" "$PYTHON_DST_CGU"
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
