"""
Diagram Management Tools (Project Integration)

save_diagram, save_diagram_standalone, list_diagrams

These tools save Draw.io source diagrams and optional rendered companion assets
to the project's results/figures directory.  Companion assets (PNG/SVG) are the
exportable files that Pandoc can embed into Word/PDF outputs.
"""

import base64
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import ProjectManager

from .._shared import (
    ensure_project_context,
    get_optional_tool_decorator,
    get_project_list_for_prompt,
)

_TEXT_DIAGRAM_FORMATS = {"xml", "svg", "txt", "text"}
_BINARY_DIAGRAM_FORMATS = {"png", "jpg", "jpeg", "gif", "webp", "pdf"}


def _decode_rendered_content(content: str, content_format: str, output_format: str) -> bytes:
    """Decode rendered diagram content into bytes for writing.

    Args:
        content: Raw or base64-encoded rendered content.
        content_format: One of ``xml``, ``text``, ``base64``, or ``auto``.
        output_format: File format/extension without leading dot.

    Returns:
        Bytes ready to be written to disk.

    Raises:
        ValueError: If the content cannot be decoded using the requested mode.
    """
    fmt = (content_format or "auto").lower()
    out_fmt = output_format.lower()

    if fmt == "base64":
        return base64.b64decode(content)

    if fmt in {"xml", "text"}:
        return content.encode("utf-8")

    if fmt != "auto":
        raise ValueError(f"Unsupported rendered content format: {content_format}")

    if out_fmt in _BINARY_DIAGRAM_FORMATS:
        return base64.b64decode(content)

    if content.lstrip().startswith("<"):
        return content.encode("utf-8")

    try:
        decoded = base64.b64decode(content)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise ValueError(f"Could not auto-decode rendered content: {exc}") from exc

    return decoded


def _save_companion_rendered_asset(
    diagram_path: Path,
    rendered_content: str,
    rendered_format: str,
    rendered_content_format: str,
    rendered_filename: str = "",
) -> Path:
    """Save an exportable rendered asset next to the source .drawio file.

    Args:
        diagram_path: Path to the saved ``.drawio`` source file.
        rendered_content: Raw or base64-encoded image/XML content.
        rendered_format: Output format (``svg``, ``png``, etc.).
        rendered_content_format: Decoding mode (``text``, ``base64``, ``auto``).
        rendered_filename: Optional explicit filename for the companion asset.

    Returns:
        Absolute path to the saved companion asset.
    """
    fmt = rendered_format.lower().lstrip(".")
    if not fmt:
        raise ValueError("rendered_format is required when rendered_content is provided")

    asset_name = rendered_filename or f"{diagram_path.stem}.{fmt}"
    asset_path = diagram_path.with_name(asset_name)
    asset_bytes = _decode_rendered_content(rendered_content, rendered_content_format, fmt)
    asset_path.write_bytes(asset_bytes)
    return asset_path


def register_diagram_tools(
    mcp: FastMCP,
    project_manager: ProjectManager,
    *,
    register_public_verbs: bool = True,
):
    """Register Draw.io integration tools."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    @tool()
    def save_diagram(
        filename: str,
        content: str,
        project: Optional[str] = None,
        content_format: str = "xml",
        description: str = "",
        output_dir: str = "",
        rendered_content: str = "",
        rendered_format: str = "",
        rendered_content_format: str = "auto",
        rendered_filename: str = "",
    ) -> str:
        """
        Save Draw.io diagram source and optional rendered asset to project figures or standalone location.

        Args:
            filename: Diagram filename (e.g., "consort-flowchart.drawio")
            content: Diagram XML content
            project: Project slug (default: current). If no project, saves standalone.
            content_format: xml|base64
            description: Optional description
            output_dir: Standalone output directory (used when no project context)
            rendered_content: Optional rendered PNG/SVG content for export embedding
            rendered_format: Rendered asset format (svg, png, jpg, ...)
            rendered_content_format: text|base64|auto
            rendered_filename: Optional explicit rendered asset filename
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

                rendered_output_path = None
                if rendered_content:
                    try:
                        rendered_output_path = _save_companion_rendered_asset(
                            output_path,
                            rendered_content,
                            rendered_format,
                            rendered_content_format,
                            rendered_filename,
                        )
                    except Exception as e:
                        return f"❌ Error saving rendered diagram asset: {e}"

                if description:
                    meta_path = figures_dir / f"{filename}.meta.txt"
                    meta_path.write_text(description, encoding="utf-8")

                project_name = project_info.get("name", "Unknown")
                rendered_line = (
                    f"**Rendered Asset:** {rendered_output_path}\n" if rendered_output_path else ""
                )
                return f"""✅ **Diagram Saved**

**File:** {output_path}
{rendered_line}**Project:** {project_name}
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

        rendered_output_path = None
        if rendered_content:
            try:
                rendered_output_path = _save_companion_rendered_asset(
                    output_path,
                    rendered_content,
                    rendered_format,
                    rendered_content_format,
                    rendered_filename,
                )
            except Exception as e:
                return f"❌ Error saving rendered diagram asset: {e}"

        rendered_line = (
            f"**Rendered Asset:** {rendered_output_path}\n" if rendered_output_path else ""
        )
        return f"""✅ **Diagram Saved (Standalone)**

**File:** {output_path.absolute()}
{rendered_line}**Size:** {len(content)} bytes

💡 This diagram is not associated with any project.
To associate with a project, use `save_diagram` with a project parameter."""

    @tool()
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

    return {
        "save_diagram": save_diagram,
        "list_diagrams": list_diagrams,
    }
