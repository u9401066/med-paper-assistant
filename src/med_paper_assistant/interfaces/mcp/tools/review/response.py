"""
Reviewer Response Generator

Generate structured responses to peer reviewer comments.
"""

from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.services import Drafter

from .._shared import (
    ensure_project_context,
    get_project_list_for_prompt,
    log_tool_call,
    log_tool_result,
)


def register_response_tools(mcp: FastMCP, drafter: Drafter):
    """Register reviewer response generation tools."""

    @mcp.tool()
    def create_reviewer_response(
        reviewer_comments: str,
        output_format: str = "structured",
        project: Optional[str] = None,
    ) -> str:
        """
        Generate a structured response template for reviewer comments.

        This tool helps organize responses to peer reviewer comments during
        manuscript revision. It creates a professional point-by-point response
        document.

        Args:
            reviewer_comments: The reviewer's comments (copy-paste from decision letter).
            output_format: Format for responses:
                - "structured": Numbered point-by-point format (default)
                - "table": Table format with columns for comment/response/changes
                - "letter": Formal response letter format
            project: Project slug. If not specified, uses current project.

        Returns:
            Formatted response template with placeholders for your responses.

        Example:
            create_reviewer_response(
                reviewer_comments=\"\"\"
                Reviewer 1:
                1. The sample size calculation needs clarification.
                2. Please provide more details about the randomization process.
                \"\"\"
            )

        Output:
            ## Response to Reviewer 1

            ### Comment 1
            > The sample size calculation needs clarification.

            **Response:**
            [Your response here]

            **Changes made:**
            [Describe changes to manuscript, with page/line numbers]

            ---
        """
        log_tool_call(
            "create_reviewer_response",
            {"output_format": output_format, "project": project},
        )

        if project:
            is_valid, msg, _ = ensure_project_context(project)
            if not is_valid:
                return f"❌ {msg}\n\n{get_project_list_for_prompt()}"

        # Parse reviewer comments
        parsed = _parse_reviewer_comments(reviewer_comments)

        if not parsed:
            return (
                "❌ Could not parse reviewer comments.\n\n"
                "Please format as:\n"
                "```\n"
                "Reviewer 1:\n"
                "1. First comment\n"
                "2. Second comment\n"
                "\n"
                "Reviewer 2:\n"
                "1. First comment\n"
                "```"
            )

        # Generate response template
        if output_format == "table":
            result = _generate_table_format(parsed)
        elif output_format == "letter":
            result = _generate_letter_format(parsed)
        else:
            result = _generate_structured_format(parsed)

        log_tool_result("create_reviewer_response", f"parsed {len(parsed)} reviewers", success=True)
        return result

    @mcp.tool()
    def format_revision_changes(
        original_text: str,
        revised_text: str,
        location: str = "",
    ) -> str:
        """
        Format manuscript changes for reviewer response.

        Creates a clear diff-style presentation of changes made,
        suitable for inclusion in a point-by-point response.

        Args:
            original_text: The original text before revision.
            revised_text: The revised text after changes.
            location: Location in manuscript (e.g., "Page 5, Lines 120-125").

        Returns:
            Formatted change description for response document.

        Example:
            format_revision_changes(
                original_text="We enrolled 100 patients.",
                revised_text="We enrolled 100 patients based on a power analysis
                             targeting 80% power to detect a 20% difference.",
                location="Methods, Page 5, Line 120"
            )
        """
        log_tool_call(
            "format_revision_changes",
            {"location": location},
        )

        output = "**Changes made:**\n\n"

        if location:
            output += f"*Location: {location}*\n\n"

        output += "~~Original:~~\n"
        output += f"> {original_text}\n\n"

        output += "**Revised:**\n"
        output += f"> {revised_text}\n"

        log_tool_result("format_revision_changes", "success", success=True)
        return output


def _parse_reviewer_comments(text: str) -> dict[str, list[str]]:
    """Parse reviewer comments into structured format."""
    import re

    reviewers: dict[str, list[str]] = {}
    current_reviewer = None
    current_comments: list[str] = []

    lines = text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for reviewer header
        reviewer_match = re.match(
            r"^(?:Reviewer|Rev\.?)\s*#?\s*(\d+)\s*[:\-]?\s*(.*)$", line, re.IGNORECASE
        )
        if reviewer_match:
            # Save previous reviewer's comments
            if current_reviewer and current_comments:
                reviewers[current_reviewer] = current_comments

            current_reviewer = f"Reviewer {reviewer_match.group(1)}"
            current_comments = []

            # Check if there's a comment on the same line
            if reviewer_match.group(2):
                current_comments.append(reviewer_match.group(2))
            continue

        # Check for numbered comment
        comment_match = re.match(r"^(\d+)[\.)\-]\s*(.+)$", line)
        if comment_match and current_reviewer:
            current_comments.append(comment_match.group(2))
            continue

        # Check for bullet point
        bullet_match = re.match(r"^[\-\*•]\s*(.+)$", line)
        if bullet_match and current_reviewer:
            current_comments.append(bullet_match.group(1))
            continue

        # Continuation of previous comment
        if current_reviewer and current_comments:
            current_comments[-1] += " " + line
        elif current_reviewer:
            current_comments.append(line)

    # Save last reviewer
    if current_reviewer and current_comments:
        reviewers[current_reviewer] = current_comments

    # If no reviewers found, try to parse as single reviewer
    if not reviewers and text.strip():
        comments = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            comment_match = re.match(r"^(\d+)[\.)\-]\s*(.+)$", line)
            if comment_match:
                comments.append(comment_match.group(2))
            elif comments:
                comments[-1] += " " + line
            else:
                comments.append(line)
        if comments:
            reviewers["Reviewer 1"] = comments

    return reviewers


def _generate_structured_format(parsed: dict[str, list[str]]) -> str:
    """Generate structured point-by-point response format."""
    output = "# Response to Reviewers\n\n"
    output += "*Thank you for the opportunity to revise our manuscript. "
    output += "Below we provide point-by-point responses to each comment.*\n\n"
    output += "---\n\n"

    for reviewer, comments in parsed.items():
        output += f"## Response to {reviewer}\n\n"

        for i, comment in enumerate(comments, 1):
            output += f"### Comment {i}\n\n"
            output += f"> {comment}\n\n"
            output += "**Response:**\n\n"
            output += "[Your response here]\n\n"
            output += "**Changes made:**\n\n"
            output += "[Describe changes with page/line numbers, or 'No changes made']\n\n"
            output += "---\n\n"

    output += "\n## Summary of Changes\n\n"
    output += "| Section | Change | Location |\n"
    output += "|---------|--------|----------|\n"
    output += "| [Section] | [Brief description] | Page X, Lines Y-Z |\n"

    return output


def _generate_table_format(parsed: dict[str, list[str]]) -> str:
    """Generate table format for reviewer responses."""
    output = "# Response to Reviewers\n\n"

    for reviewer, comments in parsed.items():
        output += f"## {reviewer}\n\n"
        output += "| # | Comment | Response | Changes Made |\n"
        output += "|---|---------|----------|---------------|\n"

        for i, comment in enumerate(comments, 1):
            # Truncate comment for table
            comment_short = comment[:100] + "..." if len(comment) > 100 else comment
            output += f"| {i} | {comment_short} | [Response] | [Changes] |\n"

        output += "\n"

    return output


def _generate_letter_format(parsed: dict[str, list[str]]) -> str:
    """Generate formal response letter format."""
    output = "# Response to Reviewers\n\n"
    output += "[Date]\n\n"
    output += "Dear Editor,\n\n"
    output += "Thank you for the opportunity to revise our manuscript titled "
    output += '"[MANUSCRIPT TITLE]" (Manuscript ID: [ID]).\n\n'
    output += "We have carefully considered all reviewer comments and have revised "
    output += "the manuscript accordingly. Below we provide detailed responses to each point.\n\n"

    for reviewer, comments in parsed.items():
        output += f"**{reviewer}:**\n\n"

        for i, comment in enumerate(comments, 1):
            output += f"*Comment {i}: \"{comment}\"*\n\n"
            output += "Response: [Your response here]\n\n"

    output += "We hope that these revisions adequately address the reviewers' concerns. "
    output += "We look forward to hearing from you.\n\n"
    output += "Sincerely,\n\n"
    output += "[Corresponding Author]\n"

    return output
