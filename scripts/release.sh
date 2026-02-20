#!/bin/bash
# release.sh — Complete release checklist + execution
# Usage: ./scripts/release.sh 0.3.1
#        ./scripts/release.sh 0.3.1 --dry-run  (check only, no actions)
set -e

VERSION="$1"
DRY_RUN="${2:-}"

if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version> [--dry-run]"
    echo "  e.g. $0 0.3.1"
    echo "  e.g. $0 0.3.1 --dry-run"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

PASS=0
FAIL=0
WARN=0

check() {
    local label="$1"
    local result="$2"
    if [ "$result" = "0" ]; then
        echo "  ✅ $label"
        ((PASS++))
    else
        echo "  ❌ $label"
        ((FAIL++))
    fi
}

warn() {
    local label="$1"
    echo "  ⚠️  $label"
    ((WARN++))
}

echo "═══════════════════════════════════════════════"
echo "  📦 Release Checklist for v$VERSION"
echo "═══════════════════════════════════════════════"
echo ""

# ──────────────────────────────────────────
# 1. Pre-flight checks
# ──────────────────────────────────────────
echo "🔍 Pre-flight Checks"

# Clean working tree
if git diff --quiet && git diff --cached --quiet; then
    check "Working tree clean" 0
else
    check "Working tree clean (uncommitted changes)" 1
fi

# On master branch
BRANCH=$(git branch --show-current)
if [ "$BRANCH" = "master" ]; then
    check "On master branch" 0
else
    check "On master branch (currently: $BRANCH)" 1
fi

# Up to date with remote
git fetch origin --quiet 2>/dev/null || true
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/master 2>/dev/null || echo "unknown")
if [ "$LOCAL" = "$REMOTE" ]; then
    check "In sync with origin/master" 0
else
    check "In sync with origin/master" 1
fi

# Tag doesn't exist yet
if git tag -l "v$VERSION" | grep -q "v$VERSION"; then
    check "Tag v$VERSION not yet created (already exists!)" 1
else
    check "Tag v$VERSION not yet created" 0
fi

echo ""

# ──────────────────────────────────────────
# 2. Tests
# ──────────────────────────────────────────
echo "🧪 Tests"

# Python tests
if uv run pytest tests/ -x -q --timeout=60 2>/dev/null; then
    check "Python tests pass" 0
else
    check "Python tests pass" 1
fi

# VSX tests
if cd vscode-extension && npx vitest run --reporter=dot 2>/dev/null; then
    check "VSX tests pass" 0
else
    check "VSX tests pass" 1
fi
cd "$ROOT_DIR"

echo ""

# ──────────────────────────────────────────
# 3. Quality gates
# ──────────────────────────────────────────
echo "🔒 Quality Gates"

# Ruff lint
if uv run ruff check src/ tests/ 2>/dev/null; then
    check "Ruff lint clean" 0
else
    check "Ruff lint clean" 1
fi

# Mypy
if uv run mypy src/ --ignore-missing-imports 2>/dev/null; then
    check "Mypy type check" 0
else
    check "Mypy type check" 1
fi

# Bandit security
if uv run bandit -r src/ -q 2>/dev/null; then
    check "Bandit security scan" 0
else
    warn "Bandit security scan (non-blocking)"
fi

echo ""

# ──────────────────────────────────────────
# 4. Version consistency
# ──────────────────────────────────────────
echo "📋 Version Consistency"

PYPI_VER=$(grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/')
VSX_VER=$(node -p "require('./vscode-extension/package.json').version" 2>/dev/null || echo "error")

if [ "$PYPI_VER" = "$VERSION" ]; then
    check "pyproject.toml = $VERSION" 0
else
    check "pyproject.toml = $PYPI_VER (expected $VERSION)" 1
fi

if [ "$VSX_VER" = "$VERSION" ]; then
    check "package.json = $VERSION" 0
else
    check "package.json = $VSX_VER (expected $VERSION)" 1
fi

# CHANGELOG has this version
if grep -q "## \[$VERSION\]" CHANGELOG.md 2>/dev/null || grep -q "## \[Unreleased\]" CHANGELOG.md 2>/dev/null; then
    check "CHANGELOG.md has entry for $VERSION or [Unreleased]" 0
else
    warn "CHANGELOG.md may need update for $VERSION"
fi

echo ""

# ──────────────────────────────────────────
# 5. Summary
# ──────────────────────────────────────────
echo "═══════════════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed, $WARN warnings"
echo "═══════════════════════════════════════════════"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo "❌ $FAIL check(s) failed. Fix issues before releasing."
    echo ""
    echo "Quick fix hints:"
    echo "  Version mismatch → ./scripts/bump-version.sh $VERSION"
    echo "  Dirty tree       → git add -A && git commit"
    echo "  Test failures    → uv run pytest tests/ -x"
    exit 1
fi

if [ "$DRY_RUN" = "--dry-run" ]; then
    echo ""
    echo "🏁 Dry run complete. All checks passed!"
    echo "   Run without --dry-run to execute release."
    exit 0
fi

echo ""

# ──────────────────────────────────────────
# 6. Execute release
# ──────────────────────────────────────────
echo "🚀 Executing release..."

# Bump version if needed
if [ "$PYPI_VER" != "$VERSION" ] || [ "$VSX_VER" != "$VERSION" ]; then
    echo "  📌 Bumping version to $VERSION..."
    "$SCRIPT_DIR/bump-version.sh" "$VERSION"
    git add pyproject.toml vscode-extension/package.json uv.lock
    git commit -m "chore: bump version to $VERSION"
fi

# Create annotated tag
echo "  🏷️  Creating tag v$VERSION..."
git tag -a "v$VERSION" -m "Release v$VERSION"

# Push
echo "  📤 Pushing to origin..."
git push origin master
git push origin "v$VERSION"

echo ""
echo "✅ Release v$VERSION pushed!"
echo "   GitHub Actions will now:"
echo "   1. Run tests"
echo "   2. Publish to PyPI"
echo "   3. Publish to VS Marketplace"
echo "   4. Create GitHub Release"
echo ""
echo "   Monitor: https://github.com/u9401066/med-paper-assistant/actions"
