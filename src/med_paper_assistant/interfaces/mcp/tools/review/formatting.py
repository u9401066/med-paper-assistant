"""
Formatting Tools (Future)

Tools for checking and fixing manuscript formatting.

Planned tools:
- check_formatting: Verify journal-specific formatting
- fix_references: Standardize reference format
- check_figures: Verify figure/table formatting
- generate_cover_letter: Create submission cover letter
"""

from mcp.server.fastmcp import FastMCP


def register_formatting_tools(mcp: FastMCP):
    """Register formatting tools (placeholder for future development)."""

    # TODO: Implement formatting check tools
    #
    # @mcp.tool()
    # def check_formatting(
    #     draft_file: str,
    #     journal: str
    # ) -> str:
    #     """
    #     Check manuscript formatting against journal requirements.
    #
    #     Args:
    #         draft_file: Path to the manuscript file.
    #         journal: Journal name or abbreviation.
    #
    #     Returns:
    #         Formatting compliance report with fix suggestions.
    #     """
    #     pass
    #
    # @mcp.tool()
    # def generate_cover_letter(
    #     project: str,
    #     journal: str,
    #     highlights: list[str] = None
    # ) -> str:
    #     """
    #     Generate a cover letter for journal submission.
    #
    #     Uses concept.md and project info to create personalized letter.
    #     """
    #     pass
    #
    # @mcp.tool()
    # def standardize_references(
    #     draft_file: str,
    #     style: str = "vancouver"
    # ) -> str:
    #     """
    #     Standardize all references to a specific citation style.
    #     """
    #     pass

    pass
