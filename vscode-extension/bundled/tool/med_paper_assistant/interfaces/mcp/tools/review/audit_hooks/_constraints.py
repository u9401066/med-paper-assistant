"""check_domain_constraints and evolve_constraint tools."""

from pathlib import Path
from typing import Optional

from med_paper_assistant.infrastructure.persistence.domain_constraint_engine import (
    DomainConstraintEngine,
)

from ..._shared import log_tool_call, log_tool_error, log_tool_result
from .._tool_doc import nested_tool_doc
from ._common import _coerce_project_info, resolve_manuscript_project


def _resolve_paper_type(project_dir: str, paper_type: str) -> str:
    """Return the explicit paper type, else the project setting, else the default."""
    pt = paper_type
    if not pt:
        settings_path = Path(project_dir) / ".paper-settings.yaml"
        if settings_path.is_file():
            settings_text = settings_path.read_text(encoding="utf-8")
            for line in settings_text.splitlines():
                if line.strip().startswith("paper_type:"):
                    pt = line.split(":", 1)[1].strip().strip("'\"")
                    break
        if not pt:
            pt = "original-research"
    return pt


def _constraint_lines(pt: str, section: str, result: dict, summary: dict) -> list[str]:
    """TOON lines for a constraint validation result."""
    lines = [
        f"🔒 Domain Constraint Check ({pt})",
        f"Section: {section}",
        f"Constraints: {summary['total_constraints']} "
        f"(base: {result['base_constraints']}, learned: {result['learned_constraints']})",
        "",
    ]

    if result["passed"]:
        lines.append(f"✅ PASSED — {result['violation_count']} warnings, 0 critical")
    else:
        lines.append(
            f"❌ FAILED — {result['violation_count']} violations "
            f"({result['critical_count']} critical)"
        )

    if result["violations"]:
        lines.append("")
        lines.append("Violations:")
        for v in result["violations"]:
            icon = "🔴" if v["severity"] == "CRITICAL" else "🟡"
            lines.append(f"  {icon} [{v['constraint_id']}] {v['message']}")
            if v.get("suggestion"):
                lines.append(f"     → {v['suggestion']}")

    if summary.get("evolution_events", 0) > 0:
        lines.append("")
        lines.append(f"📈 Evolution: {summary['evolution_events']} constraints learned")
    return lines


def _check_constraints(content: str, section: str, paper_type: str, project: Optional[str]) -> str:
    """Validate ``content`` against the project's domain constraints."""
    project_info, workflow_error = resolve_manuscript_project(project)
    if workflow_error:
        return workflow_error
    project_info = _coerce_project_info(project_info)
    project_dir = str(project_info["project_path"])

    pt = _resolve_paper_type(project_dir, paper_type)

    engine = DomainConstraintEngine(project_dir, paper_type=pt)
    result = engine.validate_against_constraints(content, section=section)
    summary = engine.get_constraint_summary()

    output = "\n".join(_constraint_lines(pt, section, result, summary))
    log_tool_result(
        "check_domain_constraints",
        f"passed={result['passed']}, violations={result['violation_count']}",
    )
    return output


@nested_tool_doc
def check_domain_constraints(
    content: str,
    section: str = "manuscript",
    paper_type: str = "",
    project: Optional[str] = None,
) -> str:
    """
    🔒 Validate content against domain constraints (Sand Spreader).

    Checks content against structured JSON constraints for the paper type.
    Detects: AI vocabulary, missing sections, word count violations,
    and any learned constraints from meta-learning evolution.

    Args:
        content: Text content to validate.
        section: Section name (e.g., "manuscript", "introduction").
        paper_type: Override paper type. Defaults to project's type.

    Returns:
        Constraint validation report with violations.
    """
    log_tool_call(
        "check_domain_constraints",
        {"section": section, "paper_type": paper_type, "project": project},
    )
    try:
        return _check_constraints(content, section, paper_type, project)
    except Exception as e:
        log_tool_error("check_domain_constraints", e)
        return f"❌ Error checking constraints: {e}"


def _invalid_evolution_error(category: str, severity: str) -> str | None:
    """Return the validation error for a malformed category or severity, if any."""
    # Validate category
    valid_categories = {
        "statistical",
        "structural",
        "vocabulary",
        "evidential",
        "temporal",
        "reporting",
        "boundary",
    }
    if category not in valid_categories:
        return f"❌ Invalid category '{category}'. Valid: {sorted(valid_categories)}"

    if severity not in ("INFO", "WARNING", "CRITICAL"):
        return f"❌ Invalid severity '{severity}'. Valid: INFO, WARNING, CRITICAL"
    return None


def _evolved_lines(
    constraint_id: str,
    rule: str,
    category: str,
    severity: str,
    reason: str,
    source_hook: str,
    result: dict,
    engine: DomainConstraintEngine,
) -> list[str]:
    """TOON lines confirming the evolved constraint and the new constraint totals."""
    lines = [
        f"📈 Constraint Evolved: {constraint_id}",
        f"Rule: {rule}",
        f"Category: {category}",
        f"Severity: {severity}",
        f"Reason: {reason or 'not specified'}",
        f"Source hook: {source_hook or 'none'}",
        f"Learned at: {result.get('learned_at', 'unknown')}",
    ]

    summary = engine.get_constraint_summary()
    lines.append(
        f"\nTotal constraints: {summary['total_constraints']} "
        f"(learned: {summary['by_provenance'].get('learned', 0)})"
    )
    return lines


def _evolve(
    constraint_id: str,
    rule: str,
    category: str,
    description: str,
    severity: str,
    reason: str,
    source_hook: str,
    project: Optional[str],
) -> str:
    """Validate and record a learned constraint, then report the constraint totals."""
    project_info, workflow_error = resolve_manuscript_project(project)
    if workflow_error:
        return workflow_error
    project_info = _coerce_project_info(project_info)
    project_dir = str(project_info["project_path"])

    error = _invalid_evolution_error(category, severity)
    if error:
        return error

    engine = DomainConstraintEngine(project_dir)
    result = engine.evolve(
        constraint_id=constraint_id,
        rule=rule,
        category=category,
        description=description,
        severity=severity,
        reason=reason,
        source_hook=source_hook,
    )

    lines = _evolved_lines(
        constraint_id, rule, category, severity, reason, source_hook, result, engine
    )
    output = "\n".join(lines)
    log_tool_result("evolve_constraint", f"id={constraint_id}")
    return output


@nested_tool_doc
def evolve_constraint(
    constraint_id: str,
    rule: str,
    category: str,
    description: str,
    severity: str = "WARNING",
    reason: str = "",
    source_hook: str = "",
    project: Optional[str] = None,
) -> str:
    """
    📈 Add a learned constraint from recurring hook pattern.

    Called when MetaLearningEngine detects a pattern that should become
    a permanent structured constraint. This converts ephemeral hook
    feedback into permanent JSON knowledge.

    Args:
        constraint_id: Unique ID (e.g., "L001").
        rule: Rule name (e.g., "no_passive_in_results").
        category: Category (statistical, structural, vocabulary,
                  evidential, temporal, reporting, boundary).
        description: What this constraint enforces.
        severity: INFO, WARNING, or CRITICAL.
        reason: Why this constraint was added.
        source_hook: Which hook triggered this (e.g., "A5").

    Returns:
        Confirmation of constraint evolution.
    """
    log_tool_call(
        "evolve_constraint",
        {"constraint_id": constraint_id, "rule": rule, "project": project},
    )
    try:
        return _evolve(
            constraint_id, rule, category, description, severity, reason, source_hook, project
        )
    except Exception as e:
        log_tool_error("evolve_constraint", e)
        return f"❌ Error evolving constraint: {e}"
