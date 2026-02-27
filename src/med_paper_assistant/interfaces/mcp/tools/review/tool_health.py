"""
Tool Health Diagnostic — MCP tool for workspace-level tool telemetry inspection.

Provides diagnose_tool_health(), which agents can call at pipeline start to identify
tools with high error rates, high misuse rates, or zero invocations.

Reads from ToolInvocationStore (workspace-level) — no project context required.
Output format: TOON (Token-Oriented Object Notation) for token efficiency.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence.tool_invocation_store import (
    ToolInvocationStore,
)

from .._shared import log_tool_call, log_tool_error, log_tool_result

# Thresholds for health categorisation
_ERROR_RATE_THRESHOLD = 0.25  # >25% error rate → high_error
_MISUSE_RATE_THRESHOLD = 0.15  # >15% misuse rate → high_misuse


def register_tool_health_tools(mcp: FastMCP) -> None:
    """Register tool health diagnostic tools with the MCP server."""

    @mcp.tool()
    def diagnose_tool_health(project: Optional[str] = None) -> str:
        """
        Diagnose MCP tool health across the workspace.

        Call this at pipeline start to identify tools with problems:
        - High error rate (>25%): tool may be broken or misconfigured
        - High misuse rate (>15%): description confuses agents (see run_meta_learning D9)
        - Zero invocations (tool never called — potentially unknown to agent)

        Health score: 100 × (1 - problem_tools / total_tracked_tools)

        Reads workspace-level telemetry. No project context required.
        The `project` parameter is accepted for API consistency but unused.

        Args:
            project: Unused. Accepted for API consistency with other tools.

        Returns:
            TOON-format health report with health_score and per-category tables.
            Returns status: no_data if no telemetry has been collected yet.
        """
        log_tool_call("diagnose_tool_health", {"project": project})
        try:
            from med_paper_assistant.infrastructure.persistence.project_manager import (
                get_project_manager,
            )

            pm = get_project_manager()
            workspace_root = pm.projects_dir.parent
            store = ToolInvocationStore(workspace_root)
            all_stats = store.get_all_stats()

            if not all_stats:
                result = (
                    "status: no_data\n"
                    "message: No tool telemetry recorded yet.\n"
                    "action: Run any pipeline tool to begin collecting telemetry."
                )
                log_tool_result("diagnose_tool_health", "no_data", success=True)
                return result

            # Categorise tools by health status
            high_error: list[tuple[str, dict]] = []
            high_misuse: list[tuple[str, dict]] = []

            for tool_name, stats in all_stats.items():
                inv = stats.get("invocation_count", 0)
                err = stats.get("error_count", 0)
                mis = stats.get("misuse_count", 0)

                if inv <= 0:
                    continue

                if err / inv > _ERROR_RATE_THRESHOLD:
                    high_error.append((tool_name, stats))
                if mis / inv > _MISUSE_RATE_THRESHOLD:
                    high_misuse.append((tool_name, stats))

            # Compute health score (0–100)
            total_tools = len(all_stats)
            problem_tool_names = set()
            for t, _ in high_error:
                problem_tool_names.add(t)
            for t, _ in high_misuse:
                problem_tool_names.add(t)
            problem_count = len(problem_tool_names)
            health_score = max(0, round(100 * (1 - problem_count / max(total_tools, 1))))

            lines = [
                "status: ok",
                f"health_score: {health_score}/100",
                f"tools_tracked: {total_tools}",
                f"problem_tools: {problem_count}",
            ]

            if high_error:
                high_error.sort(key=lambda x: x[1].get("error_count", 0), reverse=True)
                lines.append(
                    f"\nhigh_error_tools[{len(high_error)}]"
                    "{tool,invocations,errors,error_rate,error_types}:"
                )
                for tool_name, stats in high_error:
                    inv = stats.get("invocation_count", 0)
                    err = stats.get("error_count", 0)
                    rate = f"{err / inv:.0%}" if inv else "N/A"
                    types = ";".join(stats.get("error_types", [])) or "unknown"
                    lines.append(f"  {tool_name},{inv},{err},{rate},{types}")

            if high_misuse:
                high_misuse.sort(key=lambda x: x[1].get("misuse_count", 0), reverse=True)
                lines.append(
                    f"\nhigh_misuse_tools[{len(high_misuse)}]"
                    "{tool,invocations,misuses,misuse_rate}:"
                )
                for tool_name, stats in high_misuse:
                    inv = stats.get("invocation_count", 0)
                    mis = stats.get("misuse_count", 0)
                    rate = f"{mis / inv:.0%}" if inv else "N/A"
                    lines.append(f"  {tool_name},{inv},{mis},{rate}")

            if not high_error and not high_misuse:
                lines.append("\nresult: All tracked tools healthy")

            lines.append(f"\ntelemetry_file: .audit/{ToolInvocationStore.DATA_FILE}")

            result = "\n".join(lines)
            log_tool_result(
                "diagnose_tool_health",
                f"score={health_score}, problems={problem_count}",
                success=True,
            )

            # Flush unhealthy tools to PendingEvolutionStore for cross-conversation tracking
            if problem_count > 0:
                _flush_health_alerts(workspace_root, high_error, high_misuse)

            return result

        except Exception as e:
            log_tool_error("diagnose_tool_health", e)
            return f"❌ Error diagnosing tool health: {e}"


def _flush_health_alerts(
    workspace_root: Path,
    high_error: list[tuple[str, dict]],
    high_misuse: list[tuple[str, dict]],
) -> None:
    """Persist unhealthy tool alerts as pending evolution items."""
    try:
        from med_paper_assistant.infrastructure.persistence.pending_evolution_store import (
            EvolutionItem,
            PendingEvolutionStore,
        )

        store = PendingEvolutionStore(workspace_root)
        for tool_name, stats in high_error:
            inv = stats.get("invocation_count", 0)
            err = stats.get("error_count", 0)
            store.add(
                EvolutionItem(
                    item_type="tool_fix",
                    source="diagnose_tool_health_error",
                    auto_apply=False,
                    payload={
                        "tool": tool_name,
                        "error_rate": f"{err / inv:.0%}" if inv else "N/A",
                        "error_count": err,
                        "error_types": stats.get("error_types", []),
                    },
                )
            )
        for tool_name, stats in high_misuse:
            inv = stats.get("invocation_count", 0)
            mis = stats.get("misuse_count", 0)
            store.add(
                EvolutionItem(
                    item_type="tool_fix",
                    source="diagnose_tool_health_misuse",
                    auto_apply=False,
                    payload={
                        "tool": tool_name,
                        "misuse_rate": f"{mis / inv:.0%}" if inv else "N/A",
                        "misuse_count": mis,
                    },
                )
            )
    except Exception:
        import structlog

        structlog.get_logger().warning(
            "flush_health_alerts.failed",
            exc_info=True,
        )
