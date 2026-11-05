#!/usr/bin/env python3
"""Classify a commit range into CI areas for ``.github/workflows/ci.yml``.

The ``changes`` job runs this script and every other CI job is gated on one of
its outputs. The classifier is deliberately **fail-open**: any uncertainty —
scheduled or manual runs, a missing/zero base SHA, a GitHub API error, a diff
truncated at the compare API's 300-file cap, an empty diff, or a change to the
CI wiring itself — selects every area. A skipped required check reports
success, so under-selection would let untested code merge; over-selection only
costs runner time.

Standard library only: the ``changes`` job runs on the runner's system Python
before any dependency install.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Sequence

AREAS: tuple[str, ...] = ("python", "vsx", "dashboard", "markdown", "sdk2")
FULL_SMOKE_OS: tuple[str, ...] = ("ubuntu-latest", "windows-latest", "macos-14")
WINDOWS_SMOKE_OS: tuple[str, ...] = ("windows-latest",)
COMPARE_FILE_CAP = 300
DIFF_EVENTS = frozenset({"push", "pull_request"})

# Editing the CI wiring re-validates everything it gates.
ALWAYS_FULL = re.compile(
    r"^(?:\.github/workflows/ci\.yml|scripts/ci_changed_areas\.py|\.pre-commit-config\.yaml)$"
)

# Python lint/tests read docs, workflows, plugin mirrors, and vscode-extension
# manifests, so only paths no Python test reads may skip the Python jobs.
PYTHON_EXEMPT = re.compile(r"^(?:memory-bank|dashboard|projects|\.vscode)/")

AREA_RULES: dict[str, re.Pattern[str]] = {
    # Everything vscode-extension/bundle-manifest.json mirrors into the VSIX, plus the
    # repo files `npm run validate` / vitest read: tool-surface authority and its docs,
    # the MCP integration lock, and the release workflow.
    "vsx": re.compile(
        r"^(?:vscode-extension/|src/med_paper_assistant/|integrations/cgu/"
        r"|\.claude/skills/|\.github/(?:prompts|agents)/|\.github/copilot-instructions\.md$"
        r"|\.copilot-mode\.json$|templates/|docs/(?:reference|how-to|assets)/"
        r"|tool-surface-authority\.json$|mcp-integration-lock\.json$"
        r"|\.github/workflows/release\.yml$|(?:README(?:\.zh-TW)?|ARCHITECTURE)\.md$"
        r"|docs/design/benchmark-evaluation-roadmap\.md$)"
    ),
    "dashboard": re.compile(r"^dashboard/"),
    "markdown": re.compile(r"(?:\.md$|^\.prettier)"),
    "sdk2": re.compile(
        r"^(?:mcp-integration-lock\.json$|uv\.lock$|pyproject\.toml$|\.gitmodules$"
        r"|integrations/|tests/integration/test_zotero_sdk2)"
    ),
}

# Paths whose behaviour differs by OS (shell/PowerShell helpers, hook launchers,
# lockfiles, filesystem/encoding infrastructure, and the smoke tests themselves)
# re-run the full ubuntu/windows/macOS matrix.
PLATFORM_FULL = re.compile(
    r"^(?:scripts/|integrations/|\.github/hooks/|\.gitmodules$|pyproject\.toml$|uv\.lock$"
    r"|mcp-integration-lock\.json$|vscode-extension/(?:src|scripts)/"
    r"|vscode-extension/package(?:-lock)?\.json$"
    r"|src/med_paper_assistant/(?:infrastructure|shared)/"
    r"|tests/(?:test_export_pipeline|test_figure_embedding|test_config_paths"
    r"|test_copilot_hook_guard|test_mcp_integration)\.py$"
    r"|tests/integration/test_watermark)"
)
# Other Python source/test edits get a Windows-only smoke; Linux is already
# covered by the Python Tests job and macOS by the weekly + release matrix.
PLATFORM_WINDOWS = re.compile(r"^(?:src|tests)/")

_ZERO_SHA = re.compile(r"^0+$")


def full_selection(reason: str) -> dict[str, object]:
    selection: dict[str, object] = {area: True for area in AREAS}
    selection["smoke_os"] = list(FULL_SMOKE_OS)
    selection["reason"] = reason
    return selection


def classify_paths(paths: Iterable[str]) -> dict[str, object]:
    """Map changed repo-relative paths to CI areas and the smoke OS matrix."""
    normalized = sorted(
        {path.strip().replace("\\", "/").removeprefix("./") for path in paths if path.strip()}
    )
    if not normalized:
        return full_selection("empty diff")
    if any(ALWAYS_FULL.match(path) for path in normalized):
        return full_selection("CI wiring changed")

    selection: dict[str, object] = {
        "python": any(not PYTHON_EXEMPT.match(path) for path in normalized),
    }
    for area, rule in AREA_RULES.items():
        selection[area] = any(rule.search(path) for path in normalized)

    if any(PLATFORM_FULL.match(path) for path in normalized):
        selection["smoke_os"] = list(FULL_SMOKE_OS)
    elif any(PLATFORM_WINDOWS.match(path) for path in normalized):
        selection["smoke_os"] = list(WINDOWS_SMOKE_OS)
    else:
        selection["smoke_os"] = []
    selection["reason"] = f"{len(normalized)} changed path(s)"
    return selection


Fetcher = Callable[[str, str, str, str], list[str]]


def fetch_changed_paths(repo: str, base: str, head: str, token: str) -> list[str]:
    """Return changed paths (including rename sources) from the compare API."""
    url = f"https://api.github.com/repos/{repo}/compare/{base}...{head}"
    request = urllib.request.Request(  # noqa: S310 - fixed https GitHub API URL
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "med-paper-assistant-ci",
        },
    )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
                payload = json.load(response)
            break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(2 * (attempt + 1))
    else:
        raise RuntimeError(f"compare API failed: {last_error}")

    files = payload.get("files")
    if not isinstance(files, list):
        raise RuntimeError("compare API response has no file list")
    if len(files) >= COMPARE_FILE_CAP:
        raise RuntimeError(f"compare API file list truncated at {len(files)} files")
    paths: list[str] = []
    for entry in files:
        for key in ("filename", "previous_filename"):
            value = entry.get(key) if isinstance(entry, dict) else None
            if isinstance(value, str) and value:
                paths.append(value)
    return paths


def decide(
    *,
    event: str,
    repo: str,
    base: str,
    head: str,
    token: str,
    fetcher: Fetcher = fetch_changed_paths,
) -> dict[str, object]:
    if event not in DIFF_EVENTS:
        return full_selection(f"event '{event or 'unknown'}' runs the full matrix")
    if not base or _ZERO_SHA.match(base) or not head or not repo:
        return full_selection("no usable base/head SHA")
    if not token:
        return full_selection("no token for the compare API")
    try:
        paths = fetcher(repo, base, head, token)
    except Exception as exc:  # fail-open: any classifier failure runs everything
        return full_selection(f"diff unavailable ({exc})")
    return classify_paths(paths)


def render_outputs(selection: dict[str, object]) -> list[str]:
    lines = [f"{area}={'true' if selection[area] else 'false'}" for area in AREAS]
    lines.append(f"smoke_os={json.dumps(selection['smoke_os'], separators=(',', ':'))}")
    lines.append(f"reason={selection['reason']}")
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--event", default=os.environ.get("CI_EVENT_NAME", ""))
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--base", default=os.environ.get("CI_BASE_SHA", ""))
    parser.add_argument("--head", default=os.environ.get("CI_HEAD_SHA", ""))
    parser.add_argument(
        "--files-from",
        help="Classify newline-separated paths from this file ('-' for stdin) instead of the API",
    )
    parser.add_argument("--github-output", help="Append key=value outputs to this file")
    args = parser.parse_args(argv)

    if args.files_from:
        stream = sys.stdin if args.files_from == "-" else open(args.files_from, encoding="utf-8")
        with stream:
            selection = classify_paths(line.strip() for line in stream)
    else:
        selection = decide(
            event=args.event,
            repo=args.repo,
            base=args.base,
            head=args.head,
            token=os.environ.get("GITHUB_TOKEN", ""),
        )

    lines = render_outputs(selection)
    print("\n".join(lines))
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
