#!/usr/bin/env bash
# Fail-closed release preflight. Publishing is explicit and never mutates source files.
# Usage: ./scripts/release.sh 1.0.0              # checks only
#        ./scripts/release.sh 1.0.0 --publish    # tag/push after every check passes
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "Usage: $0 <version> [--publish]"
    exit 1
fi

VERSION="$1"
MODE="${2:-}"
if [ -n "$MODE" ] && [ "$MODE" != "--publish" ]; then
    echo "Unknown option: $MODE"
    exit 1
fi
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Invalid release version: $VERSION (expected X.Y.Z)"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

if [ -n "$(git status --porcelain=v1 --untracked-files=all)" ]; then
    echo "❌ Release requires a completely clean tree, including untracked files."
    exit 1
fi
if [ "$(git branch --show-current)" != "master" ]; then
    echo "❌ Release must run from master."
    exit 1
fi

git fetch origin master --tags --quiet
if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/master)" ]; then
    echo "❌ Local master must exactly match origin/master."
    exit 1
fi
if git rev-parse --verify --quiet "refs/tags/v$VERSION" >/dev/null; then
    echo "❌ Tag v$VERSION already exists."
    exit 1
fi
if ! grep -Fqx "## [$VERSION] - $(date -u +%F)" CHANGELOG.md; then
    echo "❌ CHANGELOG.md must contain today's frozen v$VERSION release heading."
    exit 1
fi

uv lock --check
uv sync --frozen --all-extras
uv run pytest tests/test_release_hardening.py -q
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run bandit -r src/ -q
uv run pytest tests/ -q -m "not integration and not slow"
uv run pytest tests/integration/test_zotero_sdk2_install_smoke.py -q -m "integration and slow"
uv build

npm --prefix vscode-extension ci
npm --prefix vscode-extension run lint
npm --prefix vscode-extension run test:ci
npm --prefix vscode-extension run bundle:check
npm --prefix vscode-extension run package
npm --prefix vscode-extension run test:install-smoke

echo "✅ Release v$VERSION preflight passed."
if [ "$MODE" != "--publish" ]; then
    echo "   Re-run with --publish to create and push the annotated tag."
    exit 0
fi

git tag -a "v$VERSION" -m "Release v$VERSION"
git push origin "v$VERSION"
echo "✅ Tag v$VERSION pushed; GitHub Actions owns PyPI, VS Marketplace, and GitHub Release publication."
