"""Foam query (DQL) rendering shared by inline blocks and saved queries.

Foam 0.47 semantics this module relies on:

* ``type`` filters Foam's resource kind (``note``/``image``/``attachment``),
  never the frontmatter ``type``; unknown filter keys add no predicate at all.
  Frontmatter is therefore matched with a sandboxed ``jexl`` expression.
* ``.foam/queries/<id>.yaml`` holds the same body as a ``foam-query`` block.
  VS Code shows those files as Smart Folders and the official Foam MCP
  (``foam-cli mcp``) exposes them through ``list_queries`` / ``run_query``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

import structlog

from med_paper_assistant.shared.yaml_escape import escape_yaml_value

logger = structlog.get_logger()

SAVED_QUERY_PREFIX = "medpaper-"
TABLE_SELECT = "select: [title, properties.type, tags, backlink-count]"
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _jexl_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def frontmatter_equals(property_name: str, value: str) -> str:
    """Return a Jexl expression matching one frontmatter property value."""
    if _IDENTIFIER.match(property_name):
        accessor = f"resource.properties.{property_name}"
    else:
        accessor = f"resource.properties[{_jexl_string(property_name)}]"
    return f"{accessor} == {_jexl_string(value)}"


def jexl_filter(expression: str) -> str:
    return f'jexl: "{escape_yaml_value(expression)}"'


def query_body(filters: Sequence[str], *, format_name: str) -> List[str]:
    """Render a query body from pre-rendered ``key: value`` filter lines."""
    lines = ["filter:"]
    if len(filters) == 1:
        lines.append(f"  {filters[0]}")
    else:
        lines.append("  and:")
        lines.extend(f"    - {item}" for item in filters)
    if format_name == "count":
        lines.append("format: count")
    else:
        lines.extend([TABLE_SELECT, "sort: title ASC", f"format: {format_name}"])
    return lines


def _fenced(lines: List[str]) -> List[str]:
    return ["```foam-query", *lines, "```"]


def frontmatter_query_block(
    property_name: str, value: str, *, format_name: str = "count"
) -> List[str]:
    filters = [jexl_filter(frontmatter_equals(property_name, value))]
    return _fenced(query_body(filters, format_name=format_name))


def linked_reference_query_block(*, format_name: str) -> List[str]:
    """References linked from the note that contains the block."""
    filters = [jexl_filter(frontmatter_equals("type", "reference")), 'links_from: "$current"']
    return _fenced(query_body(filters, format_name=format_name))


@dataclass(frozen=True)
class SavedQuery:
    query_id: str
    name: str
    description: str
    property_name: str
    value: str

    def render(self) -> str:
        filters = [jexl_filter(frontmatter_equals(self.property_name, self.value))]
        lines = [
            f'name: "{escape_yaml_value(self.name)}"',
            f'description: "{escape_yaml_value(self.description)}"',
            *query_body(filters, format_name="table"),
        ]
        return "\n".join(lines) + "\n"


MANAGED_SAVED_QUERIES = (
    SavedQuery("references", "MedPaper references", "Reference notes", "type", "reference"),
    SavedQuery(
        "analysis-queue",
        "MedPaper analysis queue",
        "References without saved analysis",
        "analysis_state",
        "pending",
    ),
    SavedQuery(
        "fulltext-queue",
        "MedPaper fulltext queue",
        "References without ingested full text",
        "fulltext_state",
        "missing",
    ),
    SavedQuery(
        "review-queue",
        "MedPaper review queue",
        "Notes whose review is pending",
        "review_state",
        "pending",
    ),
    SavedQuery(
        "draft-sections", "MedPaper draft sections", "Draft section notes", "type", "draft-section"
    ),
    SavedQuery("figures", "MedPaper figures", "Figure asset notes", "type", "figure-note"),
    SavedQuery("tables", "MedPaper tables", "Table asset notes", "type", "table-note"),
)


def write_saved_queries(workspace_root: Path) -> List[str]:
    """Write MedPaper-managed saved queries; never touches other query files."""
    queries_dir = workspace_root / ".foam" / "queries"
    written: List[str] = []
    try:
        queries_dir.mkdir(parents=True, exist_ok=True)
        for query in MANAGED_SAVED_QUERIES:
            query_id = f"{SAVED_QUERY_PREFIX}{query.query_id}"
            path = queries_dir / f"{query_id}.yaml"
            content = query.render()
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                path.write_text(content, encoding="utf-8")
            written.append(query_id)
    except OSError as exc:
        logger.warning("Failed to write Foam saved queries", error=str(exc))
    return written
