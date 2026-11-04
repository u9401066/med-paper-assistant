"""
Formatting Tools

Comprehensive manuscript checking tool combining:
- Journal formatting checks (word limits, abstract, references, tables, figures)
- Consistency checks (citations, numbers, abbreviations, p-value, table/figure refs)
- Submission checklist (required documents and statements)
"""

from mcp.server import MCPServer

from med_paper_assistant.infrastructure.persistence import ReferenceManager
from med_paper_assistant.infrastructure.services import Drafter

from ..._shared import get_optional_tool_decorator
from ._tool import FormattingTool


def register_formatting_tools(
    mcp: MCPServer,
    drafter: Drafter,
    ref_manager: ReferenceManager,
    *,
    register_public_verbs: bool = True,
):
    """Register formatting check tools."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)
    check_formatting = tool()(FormattingTool(drafter, ref_manager).check_formatting)
    return {"check_formatting": check_formatting}


__all__ = ["register_formatting_tools"]
