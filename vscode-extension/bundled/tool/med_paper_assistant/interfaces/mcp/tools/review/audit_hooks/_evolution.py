"""verify_evolution and apply_pending_evolutions tools."""

from med_paper_assistant.infrastructure.persistence.evolution_verifier import (
    EvolutionVerifier,
)
from med_paper_assistant.infrastructure.persistence.pending_evolution_store import (
    PendingEvolutionStore,
)

from ..._shared import log_tool_call, log_tool_error, log_tool_result
from .._tool_doc import nested_tool_doc


def _verification_lines(report: dict) -> tuple[list[str], str]:
    """TOON lines for the evolution report, plus its passed/total evidence tally."""
    lines = [
        "status: ok",
        f"projects_analyzed: {report['cross_project'].get('project_count', 0)}",
        f"global_avg_score: {report['cross_project'].get('global_average_score', 0)}",
    ]

    evidence = report.get("evidence", [])
    passed_count = sum(1 for e in evidence if e["passed"])
    lines.append(f"evidence: {passed_count}/{len(evidence)} passed")

    for e in evidence:
        icon = "✅" if e["passed"] else "❌"
        lines.append(f"  {icon} {e['id']}: {e['detail']}")

    if report.get("cross_project", {}).get("weakest_dimension"):
        lines.append(
            f"weakest_dimension: {report['cross_project']['weakest_dimension']} "
            f"({report['cross_project']['weakest_score']}/10)"
        )

    lines.append("")
    lines.append(report.get("summary", "No summary available."))
    return lines, f"{passed_count}/{len(evidence)}"


@nested_tool_doc
def verify_evolution() -> str:
    """
    📈 Verify self-evolution across all projects.

    Scans all project `.audit/` directories and aggregates:
    - Quality score trends across projects
    - Hook effectiveness improvement patterns
    - Threshold adjustment history
    - Lessons learned accumulation

    Returns an evidence-based report of whether the self-improvement
    system (Hook D / MetaLearningEngine) is producing measurable results.

    No arguments needed — reads from the projects/ directory automatically.
    """
    log_tool_call("verify_evolution", {})
    try:
        from med_paper_assistant.infrastructure.persistence.project_manager import (
            get_project_manager,
        )

        pm = get_project_manager()
        projects_dir = pm.projects_dir

        verifier = EvolutionVerifier(projects_dir)
        report = verifier.verify()

        lines, tally = _verification_lines(report)
        result = "\n".join(lines)
        log_tool_result("verify_evolution", f"evidence={tally}")
        return result

    except Exception as e:
        log_tool_error("verify_evolution", e)
        return f"❌ Error verifying evolution: {e}"


def _preview_pending(store: PendingEvolutionStore) -> str:
    """List the pending evolution items."""
    pending = store.get_pending()
    if not pending:
        return "status: ok\npending: 0\nmessage: No pending evolution items."

    lines = [
        "status: ok",
        f"pending: {len(pending)}",
        f"items[{len(pending)}]{{id,type,source,project,auto_apply,created_at}}:",
    ]
    for item in pending:
        project = item.project or "workspace"
        lines.append(
            f"  {item.id},{item.type},{item.source},{project},"
            f"{item.auto_apply},{item.created_at[:10]}"
        )

    stale = store.get_stale(days=7)
    if stale:
        lines.append(f"\nstale_items: {len(stale)} item(s) older than 7 days")

    result = "\n".join(lines)
    log_tool_result("apply_pending_evolutions", f"preview: {len(pending)} pending")
    return result


def _apply_all_pending(store: PendingEvolutionStore) -> str:
    """Apply every item marked safe to auto-apply."""
    pending = store.get_pending()
    safe = [item for item in pending if item.auto_apply]
    applied_count = 0
    for item in safe:
        store.mark_applied(item.id, by="agent")
        applied_count += 1

    skipped = len(pending) - applied_count
    lines = [
        "status: ok",
        f"applied: {applied_count}",
        f"skipped: {skipped} (requires_confirmation=True)",
    ]
    if skipped > 0:
        manual = [item for item in pending if not item.auto_apply]
        lines.append(f"remaining[{len(manual)}]{{id,type,source}}:")
        for item in manual:
            lines.append(f"  {item.id},{item.type},{item.source}")

    result = "\n".join(lines)
    log_tool_result(
        "apply_pending_evolutions",
        f"apply_all: {applied_count} applied, {skipped} skipped",
    )
    return result


def _resolve_pending(store: PendingEvolutionStore, action: str, item_ids: str) -> str:
    """Apply or dismiss the pending items named in ``item_ids``."""
    if not item_ids:
        return f"❌ item_ids required for action='{action}'"

    ids = [i.strip() for i in item_ids.split(",") if i.strip()]
    results = []
    for item_id in ids:
        if action == "apply":
            ok = store.mark_applied(item_id, by="agent")
        else:
            ok = store.mark_dismissed(item_id, reason="agent_dismissed")
        results.append(f"{item_id}: {'ok' if ok else 'not_found'}")

    lines = [
        "status: ok",
        f"action: {action}",
        f"processed: {len(ids)}",
    ]
    for r in results:
        lines.append(f"  {r}")

    result = "\n".join(lines)
    log_tool_result("apply_pending_evolutions", f"{action}: {len(ids)} items")
    return result


@nested_tool_doc
def apply_pending_evolutions(
    action: str = "preview",
    item_ids: str = "",
) -> str:
    """
    📋 Review and apply pending evolution items from previous conversations.

    Cross-conversation persistence: when meta-learning, writing hooks,
    or tool health diagnostics produce evolution items, they are saved to disk.
    Call this in a NEW conversation to process items left by previous sessions.

    Args:
        action: One of:
            - "preview": List all pending items (default)
            - "apply_all": Auto-apply all safe items (auto_apply=True)
            - "apply": Apply specific items by ID (provide item_ids)
            - "dismiss": Dismiss specific items by ID (provide item_ids)
        item_ids: Comma-separated item IDs for "apply" or "dismiss" actions.

    Returns:
        Summary of pending items or applied changes.
    """
    log_tool_call("apply_pending_evolutions", {"action": action, "item_ids": item_ids})
    try:
        from med_paper_assistant.infrastructure.persistence.project_manager import (
            get_project_manager,
        )

        pm = get_project_manager()
        workspace_root = pm.projects_dir.parent
        store = PendingEvolutionStore(workspace_root)
        if action == "preview":
            return _preview_pending(store)
        elif action == "apply_all":
            return _apply_all_pending(store)
        elif action in ("apply", "dismiss"):
            return _resolve_pending(store, action, item_ids)
        else:
            return f"❌ Invalid action '{action}'. Must be: preview, apply_all, apply, dismiss"

    except Exception as e:
        log_tool_error("apply_pending_evolutions", e)
        return f"❌ Error processing pending evolutions: {e}"
