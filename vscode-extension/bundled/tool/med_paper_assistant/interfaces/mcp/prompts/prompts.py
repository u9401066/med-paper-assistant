"""MCP prompt registrations for interoperable prompt discovery."""

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.services import TemplateReader


def register_prompts(mcp: FastMCP, template_reader: TemplateReader):
    """Register a small set of interoperable MCP prompts."""

    @mcp.prompt()
    def project_bootstrap(
        research_goal: str = "",
        target_journal: str = "",
        paper_type: str = "",
    ) -> str:
        """Generate a project setup prompt for a new manuscript."""
        lines = [
            "Set up a new MedPaper project.",
            "Confirm the active project context before modifying project content.",
            "Summarize the paper type, scope, and required references before drafting.",
        ]
        if research_goal:
            lines.append(f"Research goal: {research_goal}")
        if target_journal:
            lines.append(f"Target journal: {target_journal}")
        if paper_type:
            lines.append(f"Paper type: {paper_type}")
        return "\n".join(lines)

    @mcp.prompt()
    def draft_section_plan(
        section: str,
        objective: str = "",
        citation_keys: str = "",
    ) -> str:
        """Generate a drafting brief for a manuscript section."""
        lines = [
            f"Draft the {section} section.",
            "Validate the concept before drafting if this is project content.",
            "Use only verified references and keep protected novelty statements intact.",
        ]
        if objective:
            lines.append(f"Objective: {objective}")
        if citation_keys:
            lines.append(f"Prioritize these citations: {citation_keys}")
        return "\n".join(lines)

    @mcp.prompt()
    def word_export_checklist(template_name: str = "") -> str:
        """Generate a Word export checklist prompt."""
        templates = template_reader.list_templates()
        lines = [
            "Prepare the manuscript for Word export.",
            "Verify citations, section order, and word limits before export.",
            "Use the document session workflow rather than manual copy-paste.",
        ]
        if template_name:
            lines.append(f"Requested template: {template_name}")
        if templates:
            preview = ", ".join(templates[:5])
            suffix = "..." if len(templates) > 5 else ""
            lines.append(f"Available templates: {preview}{suffix}")
        return "\n".join(lines)
