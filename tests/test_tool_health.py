"""Tests for diagnose_tool_health MCP tool."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from med_paper_assistant.infrastructure.persistence.tool_invocation_store import (
    ToolInvocationStore,
)
from med_paper_assistant.interfaces.mcp.tools.review.tool_health import (
    register_tool_health_tools,
)

# get_project_manager is imported locally inside the tool function, so we patch at source
_PM_PATCH = "med_paper_assistant.infrastructure.persistence.project_manager.get_project_manager"


# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    return ws


@pytest.fixture()
def store(workspace: Path) -> ToolInvocationStore:
    return ToolInvocationStore(workspace)


@pytest.fixture()
def tool_funcs(workspace: Path) -> dict:
    """Register tool health tools on a mock MCP and return captured callables."""
    mock_mcp = MagicMock()
    captured: dict = {}

    def fake_tool(*args, **kwargs):
        def decorator(fn):
            captured[fn.__name__] = fn
            return fn

        return decorator

    mock_mcp.tool = fake_tool
    register_tool_health_tools(mock_mcp)
    return captured


def _mock_pm(workspace: Path):
    """Context manager patching get_project_manager to point at workspace."""
    pm = MagicMock()
    pm.projects_dir = workspace / "projects"
    pm.projects_dir.mkdir(parents=True, exist_ok=True)
    return patch(_PM_PATCH, return_value=pm)


# ── Tests ──────────────────────────────────────────────────────────────


class TestDiagnoseToolHealth:
    def test_no_data_returns_no_data_status(self, tool_funcs: dict, workspace: Path) -> None:
        """Empty telemetry → status: no_data."""
        with _mock_pm(workspace):
            result = tool_funcs["diagnose_tool_health"]()
        assert "status: no_data" in result

    def test_status_ok_with_data(
        self, tool_funcs: dict, workspace: Path, store: ToolInvocationStore
    ) -> None:
        """Healthy tools → status: ok."""
        for _ in range(10):
            store.record_invocation("good_tool")
            store.record_success("good_tool")
        with _mock_pm(workspace):
            result = tool_funcs["diagnose_tool_health"]()
        assert result.startswith("status: ok")

    def test_toon_format_starts_with_status(
        self, tool_funcs: dict, workspace: Path, store: ToolInvocationStore
    ) -> None:
        """TOON compliance: output must always start with 'status:'."""
        store.record_invocation("t")
        store.record_success("t")
        with _mock_pm(workspace):
            result = tool_funcs["diagnose_tool_health"]()
        assert result.startswith("status:")

    def test_health_score_100_all_healthy(
        self, tool_funcs: dict, workspace: Path, store: ToolInvocationStore
    ) -> None:
        for _ in range(10):
            store.record_invocation("perfect_tool")
            store.record_success("perfect_tool")
        with _mock_pm(workspace):
            result = tool_funcs["diagnose_tool_health"]()
        assert "health_score: 100/100" in result

    def test_high_error_rate_tool_detected(
        self, tool_funcs: dict, workspace: Path, store: ToolInvocationStore
    ) -> None:
        """Tool with >25% error rate must appear in high_error_tools section."""
        for _ in range(4):
            store.record_invocation("broken")
        for _ in range(3):  # 75% error rate
            store.record_error("broken", "RuntimeError")
        with _mock_pm(workspace):
            result = tool_funcs["diagnose_tool_health"]()
        assert "high_error_tools" in result
        assert "broken" in result

    def test_high_misuse_rate_tool_detected(
        self, tool_funcs: dict, workspace: Path, store: ToolInvocationStore
    ) -> None:
        """Tool with >15% misuse rate must appear in high_misuse_tools section."""
        for _ in range(5):
            store.record_invocation("confusing")
        for _ in range(2):  # 40% misuse rate
            store.record_misuse("confusing")
        with _mock_pm(workspace):
            result = tool_funcs["diagnose_tool_health"]()
        assert "high_misuse_tools" in result
        assert "confusing" in result

    def test_health_score_reduced_by_problem_tool(
        self, tool_funcs: dict, workspace: Path, store: ToolInvocationStore
    ) -> None:
        for _ in range(4):
            store.record_invocation("problem")
        for _ in range(3):
            store.record_error("problem", "TypeError")
        with _mock_pm(workspace):
            result = tool_funcs["diagnose_tool_health"]()
        for line in result.split("\n"):
            if line.startswith("health_score:"):
                score = int(line.split(":")[1].strip().split("/")[0])
                assert score < 100
                return
        pytest.fail("health_score line not found in result")

    def test_all_healthy_message(
        self, tool_funcs: dict, workspace: Path, store: ToolInvocationStore
    ) -> None:
        """No problems → 'All tracked tools healthy' message."""
        for _ in range(10):
            store.record_invocation("ok")
            store.record_success("ok")
        with _mock_pm(workspace):
            result = tool_funcs["diagnose_tool_health"]()
        assert "All tracked tools healthy" in result

    def test_telemetry_file_name_in_output(
        self, tool_funcs: dict, workspace: Path, store: ToolInvocationStore
    ) -> None:
        store.record_invocation("x")
        with _mock_pm(workspace):
            result = tool_funcs["diagnose_tool_health"]()
        assert ToolInvocationStore.DATA_FILE in result

    def test_project_param_accepted(self, tool_funcs: dict, workspace: Path) -> None:
        """project param should be accepted without error (reserved/unused)."""
        with _mock_pm(workspace):
            result = tool_funcs["diagnose_tool_health"](project="my-project")
        assert "status:" in result

    def test_tools_counted_correctly(
        self, tool_funcs: dict, workspace: Path, store: ToolInvocationStore
    ) -> None:
        for t in ["tool_a", "tool_b", "tool_c"]:
            store.record_invocation(t)
            store.record_success(t)
        with _mock_pm(workspace):
            result = tool_funcs["diagnose_tool_health"]()
        assert "tools_tracked: 3" in result
