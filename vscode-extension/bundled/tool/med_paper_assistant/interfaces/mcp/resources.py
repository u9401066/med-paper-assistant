"""MCP resource registrations for workspace metadata."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence.project_manager import ProjectManager
from med_paper_assistant.infrastructure.persistence.workspace_state_manager import (
    get_workspace_state_manager,
)
from med_paper_assistant.infrastructure.services import TemplateReader


def register_resources(
    mcp: FastMCP,
    project_manager: ProjectManager,
    template_reader: TemplateReader,
) -> None:
    """Register lightweight workspace resources for MCP clients."""

    @mcp.resource("medpaper://workspace/state")
    def workspace_state_resource() -> str:
        state = get_workspace_state_manager().get_state()
        return json.dumps(state, indent=2, ensure_ascii=False)

    @mcp.resource("medpaper://workspace/projects")
    def workspace_projects_resource() -> str:
        projects = project_manager.list_projects()
        return json.dumps(projects, indent=2, ensure_ascii=False)

    @mcp.resource("medpaper://templates/catalog")
    def template_catalog_resource() -> str:
        templates = template_reader.list_templates()
        payload = {
            "count": len(templates),
            "templates": templates,
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)
