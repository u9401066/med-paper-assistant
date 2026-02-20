#!/bin/bash
# Validate MedPaper Assistant VSX Extension build integrity
# Run after build to verify everything is in sync

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXT_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$EXT_DIR")"

PASS=0
FAIL=0
WARN=0

pass() { echo "  ✅ $1"; ((PASS++)); }
fail() { echo "  ❌ $1"; ((FAIL++)); }
warn() { echo "  ⚠️  $1"; ((WARN++)); }

echo "🔍 MedPaper VSX Extension Build Validation"
echo "============================================"
echo ""

# ─── V1: TypeScript Compilation ───
echo "📦 V1: TypeScript Compilation"
if [ -f "$EXT_DIR/out/extension.js" ]; then
    pass "extension.js exists"
else
    fail "extension.js missing — run 'npm run compile'"
fi

if [ -f "$EXT_DIR/out/utils.js" ]; then
    pass "utils.js exists"
else
    fail "utils.js missing — run 'npm run compile'"
fi

echo ""

# ─── V2: Skills Sync ───
echo "📖 V2: Skills Sync"
SKILLS_SRC="$ROOT_DIR/.claude/skills"
SKILLS_DST="$EXT_DIR/skills"

# Expected skills (from utils.ts BUNDLED_SKILLS)
EXPECTED_SKILLS=(
    literature-review concept-development concept-validation
    parallel-search project-management draft-writing
    reference-management word-export auto-paper
    academic-debate idea-validation manuscript-review
    submission-preparation git-precommit
)

for skill in "${EXPECTED_SKILLS[@]}"; do
    src_file="$SKILLS_SRC/$skill/SKILL.md"
    dst_file="$SKILLS_DST/$skill/SKILL.md"

    if [ ! -f "$src_file" ]; then
        fail "Source skill missing: $skill"
    elif [ ! -f "$dst_file" ]; then
        fail "Bundled skill missing: $skill"
    elif ! diff -q "$src_file" "$dst_file" > /dev/null 2>&1; then
        warn "Skill outdated: $skill"
    else
        pass "Skill synced: $skill"
    fi
done

BUNDLED_COUNT=$(find "$SKILLS_DST" -name "SKILL.md" | wc -l)
echo "  📊 Bundled skills: $BUNDLED_COUNT / ${#EXPECTED_SKILLS[@]}"

echo ""

# ─── V3: Prompts Sync ───
echo "📋 V3: Prompts Sync"
PROMPTS_SRC="$ROOT_DIR/.github/prompts"
PROMPTS_DST="$EXT_DIR/prompts"

EXPECTED_PROMPTS=(
    mdpaper.write-paper mdpaper.literature-survey
    mdpaper.manuscript-revision mdpaper.search
    mdpaper.concept mdpaper.draft mdpaper.project
    mdpaper.format mdpaper.strategy mdpaper.analysis
    mdpaper.clarify mdpaper.help
)

for prompt in "${EXPECTED_PROMPTS[@]}"; do
    src_file="$PROMPTS_SRC/${prompt}.prompt.md"
    dst_file="$PROMPTS_DST/${prompt}.prompt.md"

    if [ ! -f "$src_file" ]; then
        fail "Source prompt missing: $prompt"
    elif [ ! -f "$dst_file" ]; then
        fail "Bundled prompt missing: $prompt"
    elif ! diff -q "$src_file" "$dst_file" > /dev/null 2>&1; then
        warn "Prompt outdated: $prompt"
    else
        pass "Prompt synced: $prompt"
    fi
done

# Check _capability-index.md
if [ -f "$PROMPTS_DST/_capability-index.md" ]; then
    if diff -q "$PROMPTS_SRC/_capability-index.md" "$PROMPTS_DST/_capability-index.md" > /dev/null 2>&1; then
        pass "_capability-index.md synced"
    else
        warn "_capability-index.md outdated"
    fi
else
    fail "_capability-index.md missing"
fi

echo ""

# ─── V4: Package.json Consistency ───
echo "📄 V4: Package.json Consistency"
PKG="$EXT_DIR/package.json"

# Check version format
VERSION=$(node -e "console.log(require('$PKG').version)" 2>/dev/null || echo "")
if [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    pass "Version format valid: $VERSION"
else
    fail "Invalid version format: $VERSION"
fi

# Check required chat commands
REQUIRED_CMDS=("search" "draft" "concept" "project" "format" "autopaper" "analysis" "strategy" "help")
for cmd in "${REQUIRED_CMDS[@]}"; do
    if node -e "
        const pkg = require('$PKG');
        const cmds = pkg.contributes.chatParticipants[0].commands.map(c => c.name);
        process.exit(cmds.includes('$cmd') ? 0 : 1);
    " 2>/dev/null; then
        pass "Chat command: /$cmd"
    else
        fail "Missing chat command: /$cmd"
    fi
done

echo ""

# ─── V5: VSIX Package ───
echo "📦 V5: VSIX Package"
VSIX_FILE=$(find "$EXT_DIR" -maxdepth 1 -name "*.vsix" -type f | head -1)
if [ -n "$VSIX_FILE" ]; then
    SIZE=$(du -h "$VSIX_FILE" | cut -f1)
    pass "VSIX exists: $(basename "$VSIX_FILE") ($SIZE)"

    # Check VSIX version matches package.json
    VSIX_VERSION=$(basename "$VSIX_FILE" | grep -oP '\d+\.\d+\.\d+')
    if [ "$VSIX_VERSION" = "$VERSION" ]; then
        pass "VSIX version matches package.json: $VSIX_VERSION"
    else
        warn "VSIX version ($VSIX_VERSION) != package.json ($VERSION)"
    fi
else
    warn "No VSIX file found (run 'npm run package')"
fi

echo ""

# ─── V6: Unit Tests ───
echo "🧪 V6: Unit Tests"
if command -v npx &> /dev/null && [ -f "$EXT_DIR/node_modules/.bin/vitest" ]; then
    cd "$EXT_DIR"
    if npx vitest run --reporter=dot 2>&1 | tail -3 | grep -q "passed"; then
        TEST_RESULT=$(npx vitest run --reporter=dot 2>&1 | tail -1)
        pass "Unit tests: $TEST_RESULT"
    else
        fail "Unit tests failed"
    fi
else
    warn "vitest not installed — run 'npm install'"
fi

echo ""

# ─── Summary ───
echo "============================================"
echo "📊 Validation Summary"
echo "  ✅ Passed: $PASS"
echo "  ⚠️  Warnings: $WARN"
echo "  ❌ Failed: $FAIL"
echo ""

if [ $FAIL -gt 0 ]; then
    echo "❌ BUILD VALIDATION FAILED"
    exit 1
elif [ $WARN -gt 0 ]; then
    echo "⚠️  BUILD OK with warnings (run build.sh to re-sync)"
    exit 0
else
    echo "✅ ALL CHECKS PASSED"
    exit 0
fi
