from __future__ import annotations

from pathlib import Path

import pytest
from mcp.server import MCPServer

from med_paper_assistant.interfaces.mcp.tools.project.workspace import register_workspace_tools


@pytest.mark.asyncio
async def test_open_project_files_resolves_current_slug_to_project_info(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = tmp_path / "projects" / "demo"
    (project_dir / "drafts").mkdir(parents=True)
    (project_dir / "concept.md").write_text("# Concept", encoding="utf-8")
    (project_dir / "drafts" / "draft.md").write_text("# Draft", encoding="utf-8")

    class FakeProjectManager:
        projects_dir = tmp_path / "projects"

        @staticmethod
        def get_current_project() -> str:
            return "demo"

        @staticmethod
        def get_project_info(slug: str) -> dict[str, object]:
            assert slug == "demo"
            return {
                "success": True,
                "slug": slug,
                "name": "Demo Project",
                "project_path": str(project_dir),
            }

    from med_paper_assistant.interfaces.mcp.tools.project.vscode_launcher import LaunchResult

    opened: list[list[str]] = []

    def fake_open(paths):
        opened.append(list(paths))
        return LaunchResult(cli="code", opened=list(paths))

    monkeypatch.setattr(
        "med_paper_assistant.interfaces.mcp.tools.project.workspace.open_files_in_vscode",
        fake_open,
    )
    tools = register_workspace_tools(MCPServer("workspace-test"), FakeProjectManager())

    result = await tools["open_project_files"]()

    assert "Demo Project" in result
    assert "concept.md" in result
    assert "draft.md" in result
    assert len(opened) == 1 and len(opened[0]) == 2
