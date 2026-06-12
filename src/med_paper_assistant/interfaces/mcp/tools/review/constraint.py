"""
Constraint Ledger Tool — the monotonic manuscript-convergence ratchet.

Wraps ConstraintLedger as a single facade-style MCP tool. Every problem a hook
or reviewer raises becomes a CONSTRAINT that must be either satisfied (fixed) or
explicitly waived (with a reason) before the manuscript can be declared
converged. Constraints never silently vanish — the ledger is the manuscript's
externalized, never-forgetting working memory (CONSTITUTION §22, §25-26).

Per-project: reads/writes projects/{slug}/.audit/constraint-ledger.yaml
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence.constraint_ledger import ConstraintLedger

from .._shared import (
    get_optional_tool_decorator,
    log_tool_call,
    log_tool_error,
    log_tool_result,
    resolve_project_context,
)

_READ_ACTIONS = {"status", "summary", "list", "report", "markdown"}
_MUTATION_ACTIONS = {"satisfy", "waive", "reopen"}
_SUPPORTED_ACTIONS = _READ_ACTIONS | _MUTATION_ACTIONS | {"add", "ingest"}


def register_constraint_tools(
    mcp: FastMCP,
    *,
    register_public_verbs: bool = True,
) -> dict[str, Callable[..., Any]]:
    """Register the constraint-ledger tool with the MCP server."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    @tool()
    def constraint_action(
        action: str = "status",
        source: str = "",
        description: str = "",
        severity: str = "WARNING",
        section: str = "",
        key: str = "",
        reason: str = "",
        actor: str = "",
        issues: str = "",
        project: Optional[str] = None,
    ) -> str:
        """
        ⚖️ Manuscript constraint ledger — the monotonic convergence ratchet.

        Every problem a hook or reviewer raises becomes a CONSTRAINT that must be
        either satisfied (fixed) or explicitly waived (with a reason) before the
        manuscript can be declared converged. Constraints never silently vanish.

        Actions:
        - status  (default): convergence report (open/satisfied/waived + open list)
        - add     : record a new constraint (needs source + description)
        - satisfy : mark a constraint fixed (needs key; optional reason)
        - waive   : explicitly accept without fixing (needs key + reason)
        - reopen  : re-open a resolved constraint after a regression (needs key + reason)
        - ingest  : bulk-add from a JSON array of hook issues (idempotent)

        Args:
            action: status|add|satisfy|waive|reopen|ingest. Defaults to status.
            source: Who raised it (e.g. "P7", "reviewer-round-2", "B13"). For add.
            description: What must be resolved. For add.
            severity: CRITICAL|WARNING|INFO. For add. Defaults to WARNING.
            section: Manuscript section the constraint applies to. For add.
            key: Constraint key (c_xxxxxxxxxxxx). For satisfy/waive/reopen.
            reason: Resolution/waiver/reopen reason. REQUIRED for waive and reopen.
            actor: Who performed the transition (defaults: agent for satisfy/reopen,
                human for waive).
            issues: JSON array of {hook_id, severity, section, message} objects. For ingest.
            project: Project slug (optional, uses current project).

        Returns:
            Markdown/text report of the resulting ledger state.
        """
        log_tool_call("constraint_action", {"action": action, "key": key, "project": project})
        try:
            normalized = (action or "status").strip().lower()
            if normalized in {"help", "actions", "supported"}:
                return "supported_actions: " + ", ".join(sorted(_SUPPORTED_ACTIONS))
            if normalized not in _SUPPORTED_ACTIONS:
                return (
                    f"❌ Unsupported action '{action}'. "
                    f"Supported: {', '.join(sorted(_SUPPORTED_ACTIONS))}"
                )

            project_info, workflow_error = resolve_project_context(project)
            if workflow_error:
                return workflow_error
            if project_info is None:
                return "❌ Project context unavailable."

            project_dir = Path(project_info["project_path"])
            ledger = ConstraintLedger(project_dir / ".audit")

            if normalized in _READ_ACTIONS:
                result = ledger.to_markdown()
                log_tool_result("constraint_action", f"status converged={ledger.is_converged()}")
                return result

            if normalized == "add":
                if not source.strip() or not description.strip():
                    return "❌ action='add' requires both source and description."
                constraint = ledger.add(
                    source.strip(),
                    description.strip(),
                    severity=(severity or "WARNING").strip().upper(),
                    section=section.strip(),
                )
                summary = ledger.summary()
                log_tool_result("constraint_action", f"add {constraint.key}")
                return (
                    "✅ Constraint recorded\n"
                    f"key: {constraint.key}\n"
                    f"status: {constraint.status}\n"
                    f"severity: {constraint.severity}\n"
                    f"source: {constraint.source}\n"
                    f"open_remaining: {summary['open']} (critical {summary['open_critical']})"
                )

            if normalized == "ingest":
                try:
                    parsed = json.loads(issues) if issues.strip() else []
                except json.JSONDecodeError as exc:
                    return f"❌ action='ingest' requires a valid JSON array of issues: {exc}"
                if not isinstance(parsed, list):
                    return "❌ action='ingest' expects a JSON array of issue objects."
                added = ledger.ingest_hook_issues(parsed)
                summary = ledger.summary()
                log_tool_result("constraint_action", f"ingest +{added}")
                return (
                    f"✅ Ingested {added} new constraint(s)\n"
                    f"open: {summary['open']} (critical {summary['open_critical']}) | "
                    f"satisfied: {summary['satisfied']} | "
                    f"waived: {summary['waived']} | total: {summary['total']}"
                )

            # Lifecycle transitions on an existing key.
            if not key.strip():
                return f"❌ action='{normalized}' requires a constraint key."

            if normalized == "satisfy":
                changed = ledger.satisfy(
                    key.strip(), reason=reason.strip(), actor=(actor or "agent").strip()
                )
                verb = "satisfied"
            elif normalized == "waive":
                if not reason.strip():
                    return "❌ action='waive' requires a reason."
                changed = ledger.waive(
                    key.strip(), reason=reason.strip(), actor=(actor or "human").strip()
                )
                verb = "waived"
            else:  # reopen
                if not reason.strip():
                    return "❌ action='reopen' requires a reason."
                changed = ledger.reopen(
                    key.strip(), reason=reason.strip(), actor=(actor or "agent").strip()
                )
                verb = "reopened"

            if not changed:
                return f"❌ No constraint found with key '{key}'."
            summary = ledger.summary()
            log_tool_result("constraint_action", f"{verb} {key}")
            return (
                f"✅ Constraint {verb}: {key}\n"
                f"converged: {ledger.is_converged()}\n"
                f"open: {summary['open']} (critical {summary['open_critical']}) | "
                f"satisfied: {summary['satisfied']} | waived: {summary['waived']}"
            )

        except ValueError as exc:
            log_tool_error("constraint_action", exc)
            return f"❌ {exc}"
        except Exception as exc:  # noqa: BLE001 — surface as message, never crash transport
            log_tool_error("constraint_action", exc)
            return f"❌ Error in constraint_action: {exc}"

    return {"constraint_action": constraint_action}
