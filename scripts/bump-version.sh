#!/usr/bin/env bash
# Synchronize every public version surface. This script never commits or tags.
# Usage: ./scripts/bump-version.sh 1.0.0
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <version>"
    echo "  e.g. $0 1.0.0"
    exit 1
fi

VERSION="$1"
RELEASE_DATE="${RELEASE_DATE:-$(date -u +%F)}"

# The released Python package and VSIX share a SemVer-compatible PEP 440 version.
if ! python3 - "$VERSION" <<'PY'
import re
import sys

if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", sys.argv[1]):
    raise SystemExit(1)
PY
then
    echo "❌ Invalid version format: $VERSION (expected X.Y.Z)"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

CURRENT_VERSION="$(python3 - <<'PY'
import re
from pathlib import Path

match = re.search(r'^version = "([^"]+)"$', Path("pyproject.toml").read_text(encoding="utf-8"), re.M)
if match is None:
    raise SystemExit("pyproject.toml has no project version")
print(match.group(1))
PY
)"

echo "📌 Synchronizing $CURRENT_VERSION → $VERSION ($RELEASE_DATE)"

python3 - "$CURRENT_VERSION" "$VERSION" "$RELEASE_DATE" <<'PY'
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

old, new, release_date = sys.argv[1:]


def replace_exact(path: str, pattern: str, replacement: str, *, count: int = 1) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    updated, replaced = re.subn(pattern, replacement, text, count=count, flags=re.MULTILINE)
    if replaced != count:
        raise SystemExit(f"Expected {count} match(es) in {target}, found {replaced}: {pattern}")
    target.write_text(updated, encoding="utf-8")


replace_exact("pyproject.toml", r'^version = ".*"$', f'version = "{new}"')
replace_exact(
    "src/med_paper_assistant/__init__.py",
    r'^__version__ = ".*"$',
    f'__version__ = "{new}"',
)
replace_exact(
    "vscode-extension/bundled/tool/med_paper_assistant/__init__.py",
    r'^__version__ = ".*"$',
    f'__version__ = "{new}"',
)

for package_path in ("vscode-extension/package.json", "vscode-extension/package-lock.json"):
    path = Path(package_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["version"] = new
    if package_path.endswith("package-lock.json"):
        payload["packages"][""]["version"] = new
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

replace_exact("CITATION.cff", r"^version: .*$", f"version: {new}")
replace_exact("CITATION.cff", r"^date-released: .*$", f"date-released: {release_date}")
for readme in ("README.md", "README.zh-TW.md"):
    replace_exact(readme, r"version = \{[^}]+\}", f"version = {{{new}}}")
replace_exact(
    "docs/index.md",
    r"`v[0-9]+\.[0-9]+\.[0-9]+`(?= 提供 MCP SDK2-only runtime)",
    f"`v{new}`",
)

changelog = Path("CHANGELOG.md")
text = changelog.read_text(encoding="utf-8")
heading = f"## [{new}] - {release_date}"
if heading not in text:
    marker = "## [Unreleased]"
    if text.count(marker) != 1:
        raise SystemExit("CHANGELOG.md must contain exactly one [Unreleased] heading")
    text = text.replace(marker, f"{marker}\n\n{heading}", 1)
    changelog.write_text(text, encoding="utf-8")

vsx_changelog = Path("vscode-extension/CHANGELOG.md")
vsx_text = vsx_changelog.read_text(encoding="utf-8")
vsx_heading = f"## {new} - {release_date}"
if vsx_heading not in vsx_text:
    insertion = (
        f"{vsx_heading}\n\n"
        "- See the repository CHANGELOG for the complete release notes.\n\n"
    )
    first_heading = re.search(r"^## ", vsx_text, flags=re.MULTILINE)
    if first_heading is None:
        vsx_text = f"{vsx_text.rstrip()}\n\n{insertion}"
    else:
        vsx_text = vsx_text[: first_heading.start()] + insertion + vsx_text[first_heading.start() :]
    vsx_changelog.write_text(vsx_text, encoding="utf-8")
PY

# The root package version is embedded in uv.lock and must match the source tree.
uv lock --offline

echo "✅ Version surfaces synchronized. Review CHANGELOG.md and vscode-extension/CHANGELOG.md."
echo "   No files were staged, committed, tagged, or pushed."
