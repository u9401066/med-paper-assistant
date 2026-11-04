#!/usr/bin/env python3
"""
Pre-commit hook: Check which documentation files may need updating
based on the staged changes.

Usage:
  As a pre-commit hook (in .pre-commit-config.yaml):
    entry: uv run python scripts/check-doc-updates.py

  Standalone:
    uv run python scripts/check-doc-updates.py [--strict]
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass

# ─── Configuration: Change Patterns → Doc Reminders ───────────────


@dataclass
class DocRule:
    """A rule mapping file change patterns to documentation updates."""

    name: str
    triggers: list[str]  # glob-like patterns (prefix match)
    docs: list[str]  # docs that may need updating
    reason: str  # why this doc needs updating
    severity: str = "warn"  # "warn" or "error"


RULES: list[DocRule] = [
    # ── Tool / Feature Changes ─────────────────────────
    DocRule(
        name="MCP Tool Changes",
        triggers=[
            "src/med_paper_assistant/interfaces/mcp/tools/",
            "src/med_paper_assistant/interfaces/mcp/server.py",
        ],
        docs=["README.md", "ARCHITECTURE.md", "README.zh-TW.md"],
        reason="Tool count or API may have changed",
    ),
    DocRule(
        name="Infrastructure Changes",
        triggers=[
            "src/med_paper_assistant/infrastructure/",
            "src/med_paper_assistant/domain/",
        ],
        docs=["ARCHITECTURE.md"],
        reason="Domain/infrastructure architecture may have changed",
    ),
    # ── Skill / Prompt Changes ─────────────────────────
    DocRule(
        name="Skill Changes",
        triggers=[
            ".claude/skills/",
        ],
        docs=["AGENTS.md", "README.md", "README.zh-TW.md"],
        reason="Skill count, triggers, or capabilities may have changed",
    ),
    DocRule(
        name="Prompt Changes",
        triggers=[
            ".github/prompts/",
        ],
        docs=["AGENTS.md", "README.md", "README.zh-TW.md"],
        reason="Prompt count or descriptions may have changed",
    ),
    # ── Agent / Governance Changes ─────────────────────
    DocRule(
        name="Governance Changes",
        triggers=[
            "CONSTITUTION.md",
            ".github/bylaws/",
        ],
        docs=["AGENTS.md", ".github/copilot-instructions.md"],
        reason="Rules/bylaws changed — agent instructions may need syncing",
    ),
    DocRule(
        name="Agent Instruction Changes",
        triggers=[
            "AGENTS.md",
        ],
        docs=[".github/copilot-instructions.md"],
        reason="AGENTS.md updated — copilot-instructions quick reference may need syncing",
    ),
    # ── Extension / Dashboard Changes ──────────────────
    DocRule(
        name="VS Code Extension Changes",
        triggers=[
            "vscode-extension/src/",
            "vscode-extension/package.json",
        ],
        docs=["README.md", "README.zh-TW.md", "vscode-extension/README.md"],
        reason="Extension features or commands may have changed",
    ),
    DocRule(
        name="Dashboard Changes",
        triggers=[
            "dashboard/src/",
            "dashboard/package.json",
        ],
        docs=["README.md", "README.zh-TW.md", "dashboard/README.md"],
        reason="Dashboard features may have changed",
    ),
    # ── Integration / Submodule Changes ────────────────
    DocRule(
        name="Integration Changes",
        triggers=[
            "integrations/",
        ],
        docs=["README.md", "README.zh-TW.md", "integrations/README.md"],
        reason="Integration tool count or configuration may have changed",
    ),
    # ── Config / Setup Changes ─────────────────────────
    DocRule(
        name="Build Config Changes",
        triggers=[
            "pyproject.toml",
            "scripts/setup.sh",
            "scripts/setup.ps1",
        ],
        docs=["README.md", "README.zh-TW.md", "CONTRIBUTING.md"],
        reason="Dependencies, install steps, or Python version may have changed",
    ),
    DocRule(
        name="Pre-commit Config Changes",
        triggers=[
            ".pre-commit-config.yaml",
        ],
        docs=["CONTRIBUTING.md"],
        reason="Pre-commit hooks changed — contributor guide may need updating",
    ),
    # ── Version / Release Changes ──────────────────────
    DocRule(
        name="Version Bump",
        triggers=[
            "scripts/bump-version.sh",
            "scripts/release.sh",
        ],
        docs=["CHANGELOG.md", "ROADMAP.md"],
        reason="Release workflow changed — changelog and roadmap may need updating",
    ),
    # ── Hook / Quality Changes ─────────────────────────
    DocRule(
        name="Hook Changes",
        triggers=[
            "src/med_paper_assistant/interfaces/mcp/tools/review/",
            ".claude/skills/git-precommit/",
            ".claude/skills/auto-paper/",
        ],
        docs=["AGENTS.md", ".github/copilot-instructions.md"],
        reason="Hook count or behavior changed — agent docs may need updating",
    ),
    # ── Design Doc Changes ─────────────────────────────
    DocRule(
        name="Design Changes",
        triggers=[
            "docs/design/",
        ],
        docs=["ARCHITECTURE.md", "ROADMAP.md"],
        reason="Design documents changed — architecture/roadmap may need syncing",
    ),
]


def get_staged_files() -> list[str]:
    """Get list of staged files from git."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]


def check_rules(staged_files: list[str]) -> list[tuple[DocRule, list[str]]]:
    """Check which rules are triggered by the staged files.

    Returns list of (rule, triggered_files) tuples.
    """
    triggered: list[tuple[DocRule, list[str]]] = []

    for rule in RULES:
        matching_files = []
        for f in staged_files:
            for pattern in rule.triggers:
                if f.startswith(pattern) or f == pattern:
                    matching_files.append(f)
                    break

        if matching_files:
            # Exclude rules where all required docs are already staged
            unstaged_docs = [d for d in rule.docs if d not in staged_files]
            if unstaged_docs:
                triggered.append((rule, matching_files))

    return triggered


def main() -> int:
    strict = "--strict" in sys.argv
    staged_files = get_staged_files()

    if not staged_files:
        return 0

    triggered = check_rules(staged_files)

    if not triggered:
        return 0

    # Deduplicate: collect all doc reminders
    doc_reasons: dict[str, list[str]] = {}
    for rule, _ in triggered:
        for doc in rule.docs:
            if doc not in staged_files:
                doc_reasons.setdefault(doc, []).append(rule.reason)

    if not doc_reasons:
        return 0

    # Print summary
    print("\n" + "=" * 60)
    print("📝 Documentation Update Reminder")
    print("=" * 60)
    print()

    for rule, matching_files in triggered:
        unstaged_docs = [d for d in rule.docs if d not in staged_files]
        if unstaged_docs:
            print(f"  🔔 {rule.name}")
            print(f"     Reason: {rule.reason}")
            print(
                f"     Changed: {', '.join(matching_files[:3])}"
                + (f" (+{len(matching_files) - 3} more)" if len(matching_files) > 3 else "")
            )
            print(f"     → Check: {', '.join(unstaged_docs)}")
            print()

    print("-" * 60)
    print("📋 Summary — docs that may need updating:")
    for doc, reasons in sorted(doc_reasons.items()):
        unique_reasons = list(dict.fromkeys(reasons))  # preserve order, dedupe
        print(f"   • {doc}")
        for r in unique_reasons:
            print(f"     └─ {r}")
    print("-" * 60)
    print()

    if strict:
        print("❌ STRICT MODE: Commit blocked. Update docs or use --no-verify.")
        return 1

    print("⚠️  This is a reminder only. Commit will proceed.")
    print("    To update docs, run: git reset HEAD && <edit docs> && git add -A")
    print()
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(errors="replace")
    sys.exit(main())
