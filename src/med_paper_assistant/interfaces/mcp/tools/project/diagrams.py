"""
Diagram Management Tools (Project Integration)

save_diagram, save_diagram_standalone, list_diagrams

These tools save Draw.io diagrams to project's results/figures directory.
They work with the separate drawio-mcp server that handles diagram creation/editing.
"""

import base64
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import ProjectManager

from .._shared import ensure_project_context, get_project_list_for_prompt


def register_diagram_tools(mcp: FastMCP, project_manager: ProjectManager):
    """Register Draw.io integration tools."""

    @mcp.tool()
    def save_diagram(
        filename: str,
        content: str,
        project: Optional[str] = None,
        content_format: str = "xml",
        description: str = "",
        output_dir: str = "",
    ) -> str:
        """
        Save Draw.io diagram to project figures or standalone location.

        Args:
            filename: Diagram filename (e.g., "consort-flowchart.drawio")
            content: Diagram XML content
            project: Project slug (default: current). If no project, saves standalone.
            content_format: xml|base64
            description: Optional description
            output_dir: Standalone output directory (used when no project context)
        """
        if not filename.endswith(".drawio"):
            filename = f"{filename}.drawio"

        if content_format == "base64":
            try:
                content = base64.b64decode(content).decode("utf-8")
            except Exception as e:
                return f"❌ Error decoding base64 content: {e}"

        if not content.strip().startswith("<"):
            return "❌ Error: Content does not appear to be valid XML"

        # Try project context first
        is_valid, msg, project_info = ensure_project_context(project)

        if is_valid and project_info:
            project_path = project_info.get("project_path")
            if project_path:
                figures_dir = Path(project_path) / "results" / "figures"
                figures_dir.mkdir(parents=True, exist_ok=True)

                output_path = figures_dir / filename
                try:
                    output_path.write_text(content, encoding="utf-8")
                except Exception as e:
                    return f"❌ Error saving diagram: {e}"

                if description:
                    meta_path = figures_dir / f"{filename}.meta.txt"
                    meta_path.write_text(description, encoding="utf-8")

                project_name = project_info.get("name", "Unknown")
                return f"""✅ **Diagram Saved**

**File:** {output_path}
**Project:** {project_name}
**Size:** {len(content)} bytes

The diagram is now part of your research project and can be:
- Exported to PNG/SVG for paper inclusion
- Edited again using Draw.io MCP
- Referenced in your drafts"""

        # No project context — save standalone
        save_dir = Path(output_dir) if output_dir else Path(".")
        output_path = save_dir / filename
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")
        except Exception as e:
            return f"❌ Error saving diagram: {e}"

        return f"""✅ **Diagram Saved (Standalone)**

**File:** {output_path.absolute()}
**Size:** {len(content)} bytes

💡 This diagram is not associated with any project.
To associate with a project, use `save_diagram` with a project parameter."""

    @mcp.tool()
    def list_diagrams(project: Optional[str] = None) -> str:
        """
        List diagrams in project's results/figures directory.

        Args:
            project: Project slug (default: current)
        """
        is_valid, msg, project_info = ensure_project_context(project)

        if not is_valid or project_info is None:
            return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

        project_path = project_info.get("project_path")
        if not project_path:
            return "❌ Error: Could not determine project path"

        figures_dir = Path(project_path) / "results" / "figures"

        if not figures_dir.exists():
            return f"📁 No figures directory found in project '{project_info.get('name')}'"

        diagrams = list(figures_dir.glob("*.drawio"))

        if not diagrams:
            return f"📁 No diagrams found in project '{project_info.get('name')}'"

        output = [f"📊 **Diagrams in '{project_info.get('name')}'**\n"]

        for i, diagram in enumerate(sorted(diagrams), 1):
            size = diagram.stat().st_size
            size_kb = size / 1024

            meta_path = figures_dir / f"{diagram.name}.meta.txt"
            description = ""
            if meta_path.exists():
                description = f" - {meta_path.read_text()[:50]}..."

            output.append(f"{i}. **{diagram.name}** ({size_kb:.1f} KB){description}")

        output.append(f"\n📂 Location: {figures_dir}")

        return "\n".join(output)
