"""
ToolInvocationStore — Workspace-level persistent telemetry for MCP tool calls.

Records per-tool invocation counts, success/error/misuse rates, and error types.
Persists to workspace_root/.audit/tool-telemetry.yaml

Architecture:
    Infrastructure layer service. Workspace-level (not per-project) because
    global tools like list_projects() have no project context.
    Bridged from tool_logging.py via module-level singleton initialized at
    server startup (initialize_tool_tracking).

Design rationale (CONSTITUTION §23):
    - Tool self-improvement requires objective usage metrics
    - Metrics survive across sessions via persistent YAML storage
    - Feeds MetaLearningEngine D9 for tool description evolution suggestions

Usage:
    store = ToolInvocationStore(workspace_root)
    store.record_invocation("write_draft")
    store.record_success("write_draft")
    store.record_error("validate_concept", "ValidationError")
    store.record_misuse("list_projects")
    stats = store.get_all_stats()
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger()


class ToolInvocationStore:
    """
    Workspace-level persistent telemetry for MCP tool call patterns.

    Tracks per-tool: invocation_count, success_count, error_count,
    misuse_count, and distinct error_types seen.

    Data file: workspace_root/.audit/tool-telemetry.yaml
    """

    DATA_FILE = "tool-telemetry.yaml"

    def __init__(self, workspace_root: str | Path) -> None:
        self._dir = Path(workspace_root) / ".audit"
        self._path = self._dir / self.DATA_FILE
        self._data: dict[str, Any] | None = None

    def _load(self) -> dict[str, Any]:
        """Load or initialize telemetry data. Caches in memory after first load."""
        if self._data is not None:
            return self._data

        if self._path.is_file():
            try:
                loaded = yaml.safe_load(self._path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    # Ensure required keys are present even if file was partially written
                    loaded.setdefault("version", 1)
                    loaded.setdefault("tools", {})
                    self._data = loaded
                    return self._data
            except (yaml.YAMLError, OSError) as e:
                logger.warning("tool_invocation_store.load_failed", error=str(e))

        self._data = {
            "version": 1,
            "tools": {},
            "created_at": datetime.now().isoformat(),
        }
        return self._data

    def _save(self) -> None:
        """Persist telemetry data to disk."""
        self._dir.mkdir(parents=True, exist_ok=True)
        data = self._load()
        data["updated_at"] = datetime.now().isoformat()
        self._path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def _ensure_tool(self, tool_name: str) -> None:
        """Initialize entry for tool_name if not already present."""
        data = self._load()
        if tool_name not in data["tools"]:
            data["tools"][tool_name] = {
                "invocation_count": 0,
                "success_count": 0,
                "error_count": 0,
                "misuse_count": 0,
                "error_types": [],
            }

    def record_invocation(self, tool_name: str) -> None:
        """
        Record that a tool was called.

        Args:
            tool_name: MCP tool function name
        """
        self._ensure_tool(tool_name)
        self._load()["tools"][tool_name]["invocation_count"] += 1
        self._save()

    def record_success(self, tool_name: str) -> None:
        """
        Record a successful tool execution.

        Args:
            tool_name: MCP tool function name
        """
        self._ensure_tool(tool_name)
        self._load()["tools"][tool_name]["success_count"] += 1
        self._save()

    def record_error(self, tool_name: str, error_type: str | None = None) -> None:
        """
        Record a tool execution error.

        Args:
            tool_name: MCP tool function name
            error_type: Exception class name (e.g., "ValueError"). Deduplicated.
        """
        self._ensure_tool(tool_name)
        data = self._load()
        data["tools"][tool_name]["error_count"] += 1
        if error_type:
            existing = data["tools"][tool_name]["error_types"]
            if error_type not in existing:
                existing.append(error_type)
        self._save()

    def record_misuse(self, tool_name: str) -> None:
        """
        Record that an agent called a tool incorrectly (wrong params, wrong context).

        Args:
            tool_name: MCP tool function name
        """
        self._ensure_tool(tool_name)
        self._load()["tools"][tool_name]["misuse_count"] += 1
        self._save()

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """
        Return a copy of telemetry stats for all tracked tools.

        Returns:
            {tool_name: {invocation_count, success_count, error_count,
                         misuse_count, error_types}}
        """
        return dict(self._load().get("tools", {}))

    def get_tool_stats(self, tool_name: str) -> dict[str, Any]:
        """
        Return telemetry stats for a single tool.

        Returns:
            Stats dict, or empty dict if tool has no recorded events.
        """
        return self._load().get("tools", {}).get(tool_name, {})

    def get_zero_invocation_tools(self, known_tools: list[str]) -> list[str]:
        """
        Return tool names from known_tools that have zero recorded invocations.

        Args:
            known_tools: Full list of expected tool names to check against.

        Returns:
            Subset of known_tools with no invocation records.
        """
        data = self._load().get("tools", {})
        return [t for t in known_tools if t not in data or data[t]["invocation_count"] == 0]

    def reset(self) -> None:
        """Clear all telemetry data. For testing only."""
        self._data = None
        if self._path.is_file():
            self._path.unlink()
