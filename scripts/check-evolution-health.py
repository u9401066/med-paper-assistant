#!/usr/bin/env python3
"""
Evolution Health Check — CI script for the Evolution Health workflow.

Scans all project .audit/ directories for:
1. Pending evolution items that are stale (> 7 days unprocessed)
2. Cross-project evolution verification via EvolutionVerifier

Outputs a JSON report to stdout for consumption by GitHub Actions.

Usage:
    uv run python scripts/check-evolution-health.py

CONSTITUTION §23 compliance:
    Read-only — never modifies any files.
    Reports only; does not auto-apply changes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def main() -> None:
    workspace_root = Path(__file__).parent.parent

    # Collect pending evolution data
    from med_paper_assistant.infrastructure.persistence.pending_evolution_store import (
        PendingEvolutionStore,
    )

    store = PendingEvolutionStore(workspace_root)
    stats = store.summary()
    stale_items = store.get_stale(days=7)

    # Run cross-project evolution verification
    projects_dir = workspace_root / "projects"
    evolution_summary = ""
    if projects_dir.is_dir():
        try:
            from med_paper_assistant.infrastructure.persistence.evolution_verifier import (
                EvolutionVerifier,
            )

            verifier = EvolutionVerifier(projects_dir)
            report = verifier.verify()
            evolution_summary = report.get("summary", "")
        except Exception as e:
            evolution_summary = f"Error running EvolutionVerifier: {e}"

    # Build details string
    details_lines = []
    if stale_items:
        details_lines.append("#### Stale Items\n")
        details_lines.append("| ID | Type | Source | Project | Created |")
        details_lines.append("|---|---|---|---|---|")
        for item in stale_items:
            project = item.project or "workspace"
            details_lines.append(
                f"| {item.id} | {item.type} | {item.source} | {project} | {item.created_at[:10]} |"
            )
        details_lines.append("")

    if stats.get("pending_by_type"):
        details_lines.append("#### Pending by Type\n")
        for t, count in sorted(stats["pending_by_type"].items()):
            details_lines.append(f"- **{t}**: {count}")
        details_lines.append("")

    if evolution_summary:
        details_lines.append("#### Cross-Project Evolution\n")
        details_lines.append(f"```\n{evolution_summary}\n```")

    # Output JSON report
    output = {
        "needs_attention": len(stale_items) > 0,
        "stale_count": len(stale_items),
        "pending_count": stats.get("pending", 0),
        "applied_count": stats.get("applied", 0),
        "dismissed_count": stats.get("dismissed", 0),
        "details": "\n".join(details_lines) if details_lines else "All healthy.",
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
