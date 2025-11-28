"""
Draw.io Integration Tools

save_diagram, save_diagram_standalone, list_diagrams
"""

import base64
from typing import Optional
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import ProjectManager
from .._shared import ensure_project_context, get_project_list_for_prompt


def register_drawio_tools(mcp: FastMCP, project_manager: ProjectManager):
    """Register Draw.io integration tools."""
    
    @mcp.tool()
    def save_diagram(
        filename: str,
        content: str,
        project: Optional[str] = None,
        content_format: str = "xml",
        description: str = ""
    ) -> str:
        """
        Save a diagram file to the project's results/figures directory.
        
        Use this after getting diagram content from Draw.io MCP's get_diagram_content tool.
        
        Workflow:
        1. User creates/edits diagram in Draw.io
        2. Agent calls drawio.get_diagram_content() to get XML
        3. Agent calls this tool to save to project
        
        Args:
            filename: Diagram filename (e.g., "consort-flowchart.drawio").
            content: Diagram content (XML or base64 encoded XML).
            project: Project slug. Agent should confirm with user.
            content_format: "xml" or "base64".
            description: Optional description.
            
        Returns:
            Success message with saved path, or error message.
        """
        is_valid, msg, project_info = ensure_project_context(project)
        
        if not is_valid:
            return f"""⚠️ **No Project Context**

{msg}

**Options:**
1. Specify a project: `save_diagram(filename="...", content="...", project="project-slug")`
2. Save to standalone location: Use `save_diagram_standalone` tool instead
3. Create a project first: `create_project(name="My Research")`

{get_project_list_for_prompt()}"""
        
        if not filename.endswith('.drawio'):
            filename = f"{filename}.drawio"
        
        project_path = project_info.get("project_path")
        if not project_path:
            return "❌ Error: Could not determine project path"
        
        figures_dir = Path(project_path) / "results" / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        
        if content_format == "base64":
            try:
                content = base64.b64decode(content).decode('utf-8')
            except Exception as e:
                return f"❌ Error decoding base64 content: {e}"
        
        if not content.strip().startswith('<'):
            return "❌ Error: Content does not appear to be valid XML"
        
        output_path = figures_dir / filename
        try:
            output_path.write_text(content, encoding='utf-8')
        except Exception as e:
            return f"❌ Error saving diagram: {e}"
        
        if description:
            meta_path = figures_dir / f"{filename}.meta.txt"
            meta_path.write_text(description, encoding='utf-8')
        
        project_name = project_info.get("name", "Unknown")
        return f"""✅ **Diagram Saved**

**File:** {output_path}
**Project:** {project_name}
**Size:** {len(content)} bytes

The diagram is now part of your research project and can be:
- Exported to PNG/SVG for paper inclusion
- Edited again using Draw.io MCP
- Referenced in your drafts"""
    
    @mcp.tool()
    def save_diagram_standalone(
        filename: str,
        content: str,
        output_dir: str = ".",
        content_format: str = "xml"
    ) -> str:
        """
        Save a diagram to a standalone location (not in any project).
        
        Args:
            filename: Diagram filename (e.g., "quick-diagram.drawio").
            content: Diagram content (XML or base64 encoded XML).
            output_dir: Directory to save to. Defaults to current directory.
            content_format: "xml" or "base64".
            
        Returns:
            Success message with saved path.
        """
        if not filename.endswith('.drawio'):
            filename = f"{filename}.drawio"
        
        if content_format == "base64":
            try:
                content = base64.b64decode(content).decode('utf-8')
            except Exception as e:
                return f"❌ Error decoding base64 content: {e}"
        
        if not content.strip().startswith('<'):
            return "❌ Error: Content does not appear to be valid XML"
        
        output_path = Path(output_dir) / filename
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding='utf-8')
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
        List all diagrams in a project's results/figures directory.
        
        Args:
            project: Project slug. If not specified, uses current project.
            
        Returns:
            List of diagram files with metadata.
        """
        is_valid, msg, project_info = ensure_project_context(project)
        
        if not is_valid:
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
