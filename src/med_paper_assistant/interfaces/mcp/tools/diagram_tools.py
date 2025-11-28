"""
Diagram Tools Module

Tools for saving and managing diagrams in research projects.
Works in conjunction with Draw.io MCP for diagram creation/editing.
"""

import os
import base64
from typing import Optional
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import ProjectManager
from .project_context import ensure_project_context, get_project_list_for_prompt


def register_diagram_tools(mcp: FastMCP, project_manager: ProjectManager):
    """Register diagram-related tools with the MCP server."""
    
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
                     Will add .drawio extension if not present.
            content: Diagram content (XML or base64 encoded XML).
            project: Project slug. Agent should confirm with user before calling.
                     If None and no active project, returns error with instructions.
            content_format: "xml" or "base64" - format of the content parameter.
            description: Optional description of the diagram.
            
        Returns:
            Success message with saved path, or error message.
        """
        # Validate project context
        is_valid, msg, project_info = ensure_project_context(project)
        
        if not is_valid:
            # No project - offer to save to standalone location
            return f"""⚠️ **No Project Context**

{msg}

**Options:**
1. Specify a project: `save_diagram(filename="...", content="...", project="project-slug")`
2. Save to standalone location: Use `save_diagram_standalone` tool instead
3. Create a project first: `create_project(name="My Research")`

{get_project_list_for_prompt()}"""
        
        # Ensure filename has .drawio extension
        if not filename.endswith('.drawio'):
            filename = f"{filename}.drawio"
        
        # Get project path
        project_path = project_info.get("project_path")
        if not project_path:
            return "❌ Error: Could not determine project path"
        
        # Create figures directory if not exists
        figures_dir = Path(project_path) / "results" / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        
        # Decode content if base64
        if content_format == "base64":
            try:
                content = base64.b64decode(content).decode('utf-8')
            except Exception as e:
                return f"❌ Error decoding base64 content: {e}"
        
        # Validate content looks like XML
        if not content.strip().startswith('<'):
            return "❌ Error: Content does not appear to be valid XML"
        
        # Save file
        output_path = figures_dir / filename
        try:
            output_path.write_text(content, encoding='utf-8')
        except Exception as e:
            return f"❌ Error saving diagram: {e}"
        
        # Create metadata file
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
        
        Use this for quick diagrams that aren't part of a formal research project.
        
        Args:
            filename: Diagram filename (e.g., "quick-diagram.drawio").
            content: Diagram content (XML or base64 encoded XML).
            output_dir: Directory to save to. Defaults to current directory.
            content_format: "xml" or "base64" - format of the content parameter.
            
        Returns:
            Success message with saved path.
        """
        # Ensure filename has .drawio extension
        if not filename.endswith('.drawio'):
            filename = f"{filename}.drawio"
        
        # Decode content if base64
        if content_format == "base64":
            try:
                content = base64.b64decode(content).decode('utf-8')
            except Exception as e:
                return f"❌ Error decoding base64 content: {e}"
        
        # Validate content looks like XML
        if not content.strip().startswith('<'):
            return "❌ Error: Content does not appear to be valid XML"
        
        # Save file
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
        # Validate project context
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
            
            # Check for metadata
            meta_path = figures_dir / f"{diagram.name}.meta.txt"
            description = ""
            if meta_path.exists():
                description = f" - {meta_path.read_text()[:50]}..."
            
            output.append(f"{i}. **{diagram.name}** ({size_kb:.1f} KB){description}")
        
        output.append(f"\n📂 Location: {figures_dir}")
        
        return "\n".join(output)
