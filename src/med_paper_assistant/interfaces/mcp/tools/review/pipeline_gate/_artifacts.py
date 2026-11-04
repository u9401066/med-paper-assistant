"""Artifact helpers shared by the pipeline gate tools."""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import structlog

from med_paper_assistant.infrastructure.persistence.autonomous_audit_loop import (
    AutonomousAuditLoop,
)


def _compute_manuscript_hash(project_dir: str | Path) -> str:
    """Hash exactly the draft artifact consumed by the review hooks.

    When ``manuscript.md`` exists it is the canonical review target; changing a
    scratch/section file must not satisfy the "review changed the manuscript"
    requirement.  Section-only projects use the same sorted aggregate fallback
    as ``read_review_manuscript_content``.
    """
    drafts_dir = Path(project_dir) / "drafts"
    if not drafts_dir.is_dir():
        return ""
    manuscript = drafts_dir / "manuscript.md"
    md_files = [manuscript] if manuscript.is_file() else sorted(drafts_dir.glob("*.md"))
    if not md_files:
        return ""
    h = hashlib.sha256()
    for f in md_files:
        h.update(f.name.encode("utf-8"))
        h.update(f.read_bytes())
    return h.hexdigest()


def _write_pipeline_completed(project_dir: Path, slug: str) -> None:
    """Write pipeline-completed.json marker when Phase 11 gate passes."""
    audit_dir = project_dir / ".audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    marker = {
        "project": slug,
        "status": "COMPLETED",
        "completed_at": datetime.now().isoformat(),
        "phases_completed": [0, 1, 2, 3, 4, 5, 6, 65, 7, 8, 9, 10, 11],
    }
    marker_path = audit_dir / "pipeline-completed.json"
    marker_path.write_text(json.dumps(marker, indent=2, ensure_ascii=False), encoding="utf-8")
    structlog.get_logger().info("Pipeline completed", project=slug, marker=str(marker_path))


def _count_review_report_issues(audit_dir: Path, round_num: int) -> dict[str, int]:
    """Parse review-report YAML frontmatter to count reported issues."""
    report_path = audit_dir / f"review-report-{round_num}.md"
    if not report_path.is_file():
        return {"major": 0, "minor": 0, "optional": 0}
    content = report_path.read_text(encoding="utf-8")
    # Parse YAML frontmatter totals
    counts: dict[str, int] = {"major": 0, "minor": 0, "optional": 0}
    for key in counts:
        match = re.search(rf"^\s*{key}:\s*(\d+)", content, re.MULTILINE)
        if match:
            counts[key] = int(match.group(1))
    return counts


def _empty_scores_error(expected_dimensions: list[str] | tuple[str, ...]) -> str:
    """Error payload for a score submission that is not a non-empty object."""
    return json.dumps(
        {
            "schema": "mdpaper.review_scores.error.v1",
            "error": "scores_must_be_non_empty_object",
            "expected_dimensions": list(expected_dimensions),
            "example": {dim: 8 for dim in expected_dimensions},
            "fix_hint": "Submit scores as a JSON object using exactly the expected dimension names.",
        },
        indent=2,
        ensure_ascii=False,
    )


def _invalid_score_values(scores: dict, expected: list[str]) -> dict[str, str]:
    """Per-dimension problems with the submitted score values."""
    invalid_values: dict[str, str] = {}
    for dim, value in scores.items():
        if dim not in expected:
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            invalid_values[dim] = "must be a number"
        elif value < 0 or value > 10:
            invalid_values[dim] = "must be between 0 and 10"
    return invalid_values


def _validate_review_score_schema(
    scores: dict,
    expected_dimensions: list[str] | tuple[str, ...],
) -> tuple[bool, str]:
    """Validate review score schema before it can affect audit-loop state."""
    if not isinstance(scores, dict) or not scores:
        return False, _empty_scores_error(expected_dimensions)

    received = list(scores)
    expected = list(expected_dimensions)
    unknown = sorted(set(received) - set(expected))
    missing = sorted(set(expected) - set(received))
    invalid_values = _invalid_score_values(scores, expected)

    if unknown or missing or invalid_values:
        return (
            False,
            json.dumps(
                {
                    "schema": "mdpaper.review_scores.error.v1",
                    "error": "score_schema_mismatch",
                    "expected_dimensions": expected,
                    "received_dimensions": received,
                    "unknown_dimensions": unknown,
                    "missing_dimensions": missing,
                    "invalid_values": invalid_values,
                    "example": {dim: 8 for dim in expected},
                    "fix_hint": (
                        "Use these exact keys: "
                        + ", ".join(expected)
                        + ". Do not use reviewer-specific labels such as methodology, domain, or statistics."
                    ),
                },
                indent=2,
                ensure_ascii=False,
            ),
        )

    return True, ""


def _log_review_round_to_evolution(
    project_dir, loop: AutonomousAuditLoop, scores: dict, verdict: str
) -> None:
    """Append review_round event to evolution-log.jsonl."""
    from datetime import datetime
    from pathlib import Path

    elog = Path(project_dir) / ".audit" / "evolution-log.jsonl"
    status = loop.get_status()

    entry = {
        "event": "review_round",
        "round": status["current_round"],
        "verdict": verdict,
        "scores": scores,
        "weighted_score": status.get("latest_weighted_score"),
        "timestamp": datetime.now().isoformat(),
    }

    try:
        elog.parent.mkdir(parents=True, exist_ok=True)
        with open(elog, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        structlog.get_logger().warning("Failed to write evolution log entry", path=str(elog))
