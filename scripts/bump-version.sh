#!/bin/bash
# Bump version in all release-facing package/runtime surfaces.
# Usage: ./scripts/bump-version.sh 0.3.0
#        ./scripts/bump-version.sh 0.3.0 --tag  (also creates git tag)
set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <version> [--tag]"
    echo "  e.g. $0 0.3.0"
    echo "  e.g. $0 0.3.0rc1"
    echo "  e.g. $0 0.3.0 --tag"
    exit 1
fi

VERSION="$1"
CREATE_TAG="${2:-}"

# Validate the PEP 440 subset accepted by pyproject.toml/package publishing.
if ! python3 - "$VERSION" <<'PY'
import re
import sys

version = sys.argv[1]
pattern = r"[0-9]+\.[0-9]+\.[0-9]+((a|b|rc)[0-9]+|\.post[0-9]+|\.dev[0-9]+)?"
if not re.fullmatch(pattern, version):
    raise SystemExit(1)
PY
then
    echo "❌ Invalid version format: $VERSION (expected PEP 440 like X.Y.Z, X.Y.Zrc1, X.Y.Z.post1, or X.Y.Z.dev1)"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "📌 Bumping version to $VERSION..."

replace_line() {
    local file="$1"
    local pattern="$2"
    local replacement="$3"
    python3 - "$file" "$pattern" "$replacement" <<'PY'
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
pattern = sys.argv[2]
replacement = sys.argv[3]
text = path.read_text(encoding="utf-8")
updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
if count != 1:
    raise SystemExit(f"Pattern not found exactly once in {path}: {pattern}")
path.write_text(updated, encoding="utf-8")
PY
}

# 1. Update pyproject.toml
PYPROJECT="$ROOT_DIR/pyproject.toml"
if [ -f "$PYPROJECT" ]; then
    replace_line "$PYPROJECT" '^version = ".*"$' "version = \"$VERSION\""
    echo "  ✅ pyproject.toml → $VERSION"
else
    echo "  ⚠️ pyproject.toml not found"
fi

# 2. Update Python runtime version
PY_INIT="$ROOT_DIR/src/med_paper_assistant/__init__.py"
if [ -f "$PY_INIT" ]; then
    replace_line "$PY_INIT" '^__version__ = ".*"$' "__version__ = \"$VERSION\""
    echo "  ✅ src/med_paper_assistant/__init__.py → $VERSION"
else
    echo "  ⚠️ src/med_paper_assistant/__init__.py not found"
fi

# 3. Update vscode-extension/package.json and package-lock.json
PACKAGE_JSON="$ROOT_DIR/vscode-extension/package.json"
PACKAGE_LOCK="$ROOT_DIR/vscode-extension/package-lock.json"
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
if [ -f "$PACKAGE_LOCK" ]; then
    node -e "
      const fs = require('fs');
      const lock = JSON.parse(fs.readFileSync('$PACKAGE_LOCK', 'utf8'));
      lock.version = '$VERSION';
      if (lock.packages && lock.packages['']) lock.packages[''].version = '$VERSION';
      fs.writeFileSync('$PACKAGE_LOCK', JSON.stringify(lock, null, 2) + '\n');
    "
    echo "  ✅ package-lock.json → $VERSION"
else
    echo "  ⚠️ package-lock.json not found"
fi

# 4. Update bundled Python runtime version
BUNDLED_INIT="$ROOT_DIR/vscode-extension/bundled/tool/med_paper_assistant/__init__.py"
if [ -f "$BUNDLED_INIT" ]; then
    replace_line "$BUNDLED_INIT" '^__version__ = ".*"$' "__version__ = \"$VERSION\""
    echo "  ✅ bundled med_paper_assistant/__init__.py → $VERSION"
else
    echo "  ⚠️ bundled med_paper_assistant/__init__.py not found"
fi

# 5. Show results
echo ""
echo "📋 Version sync:"
echo "  pyproject.toml:  $(grep '^version' "$PYPROJECT" | head -1)"
echo "  python:          $(grep '^__version__' "$PY_INIT" | head -1)"
echo "  package.json:    $(node -p "require('$PACKAGE_JSON').version")"
echo "  package-lock:    $(node -p "require('$PACKAGE_LOCK').version")"
echo "  bundled python:  $(grep '^__version__' "$BUNDLED_INIT" | head -1)"

# 6. Optionally create git tag
if [ "$CREATE_TAG" = "--tag" ]; then
    echo ""
    echo "🏷️  Creating tag v$VERSION..."
    git add "$PYPROJECT" "$PY_INIT" "$PACKAGE_JSON" "$PACKAGE_LOCK" "$BUNDLED_INIT"
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
