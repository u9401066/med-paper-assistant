#!/bin/bash
# Build script for MedPaper Assistant VS Code Extension
# Syncs skills/prompts from source, compiles, tests, validates, and packages.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXT_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$EXT_DIR")"

echo "🔨 Building MedPaper Assistant VS Code Extension..."

# 0. Update Submodules to ensure latest code
echo "🔄 Updating Git submodules..."
cd "$ROOT_DIR"
git submodule update --init --recursive --remote 2>/dev/null || echo "  ⚠️ Submodule update skipped (no remote)"
cd "$EXT_DIR"

# ──────────────────────────────────────────────────────
# 1. Copy Skills from .claude/skills/
#    Keep in sync with src/utils.ts BUNDLED_SKILLS
# ──────────────────────────────────────────────────────
echo "📖 Copying Skills..."
SKILLS_SRC="$ROOT_DIR/.claude/skills"
SKILLS_DST="$EXT_DIR/skills"

BUNDLED_SKILLS=(
    literature-review concept-development concept-validation
    parallel-search project-management draft-writing
    reference-management word-export auto-paper
    academic-debate idea-validation manuscript-review
    submission-preparation git-precommit
)

SKILLS_COPIED=0
if [ -d "$SKILLS_SRC" ]; then
    for skill in "${BUNDLED_SKILLS[@]}"; do
        if [ -d "$SKILLS_SRC/$skill" ]; then
            mkdir -p "$SKILLS_DST/$skill"
            cp "$SKILLS_SRC/$skill/SKILL.md" "$SKILLS_DST/$skill/" 2>/dev/null || true
            SKILLS_COPIED=$((SKILLS_COPIED + 1))
        else
            echo "  ⚠️ Source skill not found: $skill"
        fi
    done
fi
echo "  → Copied $SKILLS_COPIED / ${#BUNDLED_SKILLS[@]} skills"

# ──────────────────────────────────────────────────────
# 2. Copy Prompts from .github/prompts/
# ──────────────────────────────────────────────────────
echo "📋 Copying Prompts..."
PROMPTS_SRC="$ROOT_DIR/.github/prompts"
PROMPTS_DST="$EXT_DIR/prompts"

BUNDLED_PROMPTS=(
    mdpaper.write-paper mdpaper.literature-survey
    mdpaper.manuscript-revision mdpaper.search
    mdpaper.concept mdpaper.draft mdpaper.project
    mdpaper.format mdpaper.strategy mdpaper.analysis
    mdpaper.clarify mdpaper.help
)

PROMPTS_COPIED=0
if [ -d "$PROMPTS_SRC" ]; then
    for prompt in "${BUNDLED_PROMPTS[@]}"; do
        if [ -f "$PROMPTS_SRC/$prompt.prompt.md" ]; then
            cp "$PROMPTS_SRC/$prompt.prompt.md" "$PROMPTS_DST/" 2>/dev/null || true
            PROMPTS_COPIED=$((PROMPTS_COPIED + 1))
        else
            echo "  ⚠️ Source prompt not found: $prompt"
        fi
    done
    if [ -f "$PROMPTS_SRC/_capability-index.md" ]; then
        cp "$PROMPTS_SRC/_capability-index.md" "$PROMPTS_DST/" 2>/dev/null || true
    fi
fi
echo "  → Copied $PROMPTS_COPIED / ${#BUNDLED_PROMPTS[@]} prompts"

# ──────────────────────────────────────────────────────
# 2b. Copy copilot-instructions.md
# ──────────────────────────────────────────────────────
echo "📋 Copying copilot-instructions.md..."
COPILOT_INSTR_SRC="$ROOT_DIR/.github/copilot-instructions.md"
if [ -f "$COPILOT_INSTR_SRC" ]; then
    cp "$COPILOT_INSTR_SRC" "$EXT_DIR/copilot-instructions.md"
    echo "  → Copied copilot-instructions.md"
else
    echo "  ⚠️ copilot-instructions.md not found"
fi

# ──────────────────────────────────────────────────────
# 2c. Copy Templates
#     Keep in sync with src/utils.ts BUNDLED_TEMPLATES
# ──────────────────────────────────────────────────────
echo "📄 Copying Templates..."
TEMPLATES_SRC="$ROOT_DIR/templates"
TEMPLATES_DST="$EXT_DIR/templates"

BUNDLED_TEMPLATES=(
    journal-profile.template.yaml
)

TEMPLATES_COPIED=0
mkdir -p "$TEMPLATES_DST"
for tmpl in "${BUNDLED_TEMPLATES[@]}"; do
    if [ -f "$TEMPLATES_SRC/$tmpl" ]; then
        cp "$TEMPLATES_SRC/$tmpl" "$TEMPLATES_DST/" 2>/dev/null || true
        TEMPLATES_COPIED=$((TEMPLATES_COPIED + 1))
    else
        echo "  ⚠️ Source template not found: $tmpl"
    fi
done
echo "  → Copied $TEMPLATES_COPIED / ${#BUNDLED_TEMPLATES[@]} templates"

# ──────────────────────────────────────────────────────
# 3. Copy Python MCP source (for development)
# ──────────────────────────────────────────────────────
echo "🐍 Copying Python MCP source..."
PYTHON_DST_ROOT="$EXT_DIR/bundled/tool"

echo "   - med_paper_assistant"
PYTHON_SRC_MDPAPER="$ROOT_DIR/src/med_paper_assistant"
PYTHON_DST_MDPAPER="$PYTHON_DST_ROOT/med_paper_assistant"
if [ -d "$PYTHON_SRC_MDPAPER" ]; then
    rm -rf "$PYTHON_DST_MDPAPER"
    cp -r "$PYTHON_SRC_MDPAPER" "$PYTHON_DST_MDPAPER"
fi

echo "   - cgu"
PYTHON_SRC_CGU="$ROOT_DIR/integrations/cgu/src/cgu"
PYTHON_DST_CGU="$PYTHON_DST_ROOT/cgu"
if [ -d "$PYTHON_SRC_CGU" ]; then
    rm -rf "$PYTHON_DST_CGU"
    cp -r "$PYTHON_SRC_CGU" "$PYTHON_DST_CGU"
fi

# ──────────────────────────────────────────────────────
# 4. Install deps & compile TypeScript
# ──────────────────────────────────────────────────────
echo "📦 Installing dependencies..."
cd "$EXT_DIR"
npm install --silent 2>/dev/null || npm install

echo "📦 Compiling TypeScript..."
npm run compile

# ──────────────────────────────────────────────────────
# 5. Run unit tests
# ──────────────────────────────────────────────────────
echo "🧪 Running tests..."
if npx vitest run --reporter=verbose 2>&1; then
    echo "  → Tests passed ✅"
else
    echo "  ❌ Tests failed! Fix issues before packaging."
    exit 1
fi

# ──────────────────────────────────────────────────────
# 6. Package extension
# ──────────────────────────────────────────────────────
echo "📦 Packaging extension..."
npm run package

# ──────────────────────────────────────────────────────
# 7. Run build validation
# ──────────────────────────────────────────────────────
echo ""
"$SCRIPT_DIR/validate-build.sh"

echo ""
echo "✅ Build complete! Extension package: $EXT_DIR/*.vsix"
