#!/bin/bash
# Bump version in pyproject.toml and vscode-extension/package.json
# Usage: ./scripts/bump-version.sh 0.3.0
#        ./scripts/bump-version.sh 0.3.0 --tag  (also creates git tag)
set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <version> [--tag]"
    echo "  e.g. $0 0.3.0"
    echo "  e.g. $0 0.3.0 --tag"
    exit 1
fi

VERSION="$1"
CREATE_TAG="${2:-}"

# Validate semver format
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$'; then
    echo "❌ Invalid version format: $VERSION (expected: X.Y.Z or X.Y.Z-beta.1)"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "📌 Bumping version to $VERSION..."

# 1. Update pyproject.toml
PYPROJECT="$ROOT_DIR/pyproject.toml"
if [ -f "$PYPROJECT" ]; then
    sed -i "s/^version = \".*\"/version = \"$VERSION\"/" "$PYPROJECT"
    echo "  ✅ pyproject.toml → $VERSION"
else
    echo "  ⚠️ pyproject.toml not found"
fi

# 2. Update vscode-extension/package.json
PACKAGE_JSON="$ROOT_DIR/vscode-extension/package.json"
if [ -f "$PACKAGE_JSON" ]; then
    # Use node for reliable JSON editing
    node -e "
      const fs = require('fs');
      const pkg = JSON.parse(fs.readFileSync('$PACKAGE_JSON', 'utf8'));
      pkg.version = '$VERSION';
      fs.writeFileSync('$PACKAGE_JSON', JSON.stringify(pkg, null, 2) + '\n');
    "
    echo "  ✅ package.json → $VERSION"
else
    echo "  ⚠️ package.json not found"
fi

# 3. Show results
echo ""
echo "📋 Version sync:"
echo "  pyproject.toml:  $(grep '^version' "$PYPROJECT" | head -1)"
echo "  package.json:    $(node -p "require('$PACKAGE_JSON').version")"

# 4. Optionally create git tag
if [ "$CREATE_TAG" = "--tag" ]; then
    echo ""
    echo "🏷️  Creating tag v$VERSION..."
    git add "$PYPROJECT" "$PACKAGE_JSON"
    git commit -m "chore: bump version to $VERSION"
    git tag -a "v$VERSION" -m "Release v$VERSION"
    echo "  ✅ Tag v$VERSION created"
    echo ""
    echo "👉 To publish: git push && git push --tags"
else
    echo ""
    echo "👉 Next steps:"
    echo "  1. git add -A && git commit -m 'chore: bump version to $VERSION'"
    echo "  2. git tag -a v$VERSION -m 'Release v$VERSION'"
    echo "  3. git push && git push --tags"
    echo ""
    echo "  Or: $0 $VERSION --tag  (does steps 1-2 automatically)"
fi
