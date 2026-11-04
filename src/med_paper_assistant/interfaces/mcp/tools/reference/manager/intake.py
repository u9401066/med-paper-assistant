"""Handlers that import local files, web pages and markdown into the reference registry."""

import json
from pathlib import Path
from typing import Optional, Union

from med_paper_assistant.infrastructure.persistence import ReferenceManager
from med_paper_assistant.shared.path_guard import PathGuardError, resolve_local_import_path

from ..._shared import log_tool_call, log_tool_result
from ._deps import (
    REFERENCE,
    ensure_project_exists,
    parse_metadata_json,
    project_context_error,
)


def _parse_import_metadata(metadata_json: str, parsed_paths: list[str]) -> Union[list, str]:
    """Return one metadata item per path, or the error message to show the caller."""
    if not metadata_json.strip():
        return [{} for _ in parsed_paths]

    try:
        parsed_metadata = json.loads(metadata_json)
    except json.JSONDecodeError as exc:
        return f"❌ Invalid metadata_json: {exc}"

    if isinstance(parsed_metadata, list):
        if len(parsed_metadata) != len(parsed_paths):
            return "❌ metadata_json list length must match the number of provided paths."
        return parsed_metadata
    if isinstance(parsed_metadata, dict):
        return [parsed_metadata for _ in parsed_paths]
    return "❌ metadata_json must decode to a JSON object or JSON list."


def _import_local_files(
    ref_manager: ReferenceManager, parsed_paths: list[str], metadata_items: list
) -> list[str]:
    results = []
    for file_path, metadata in zip(parsed_paths, metadata_items):
        try:
            resolved_path = resolve_local_import_path(file_path)
        except PathGuardError as exc:
            results.append(f"- {Path(file_path).name}: ❌ Invalid local import path: {exc}")
            continue
        result = ref_manager.import_local_file(str(resolved_path), metadata=metadata)
        results.append(f"- {resolved_path.name}: {result}")
    return results


def import_local_papers(paths: str, metadata_json: str = "", project: Optional[str] = None) -> str:
    """
    Import one or more local files into the MedPaper reference registry.

    Args:
        paths: One path or multiple newline/comma-separated paths
        metadata_json: Optional JSON object or JSON list with extracted metadata
        project: Project slug (default: current)
    """
    ref_manager = REFERENCE.get().ref_manager
    log_tool_call(
        "import_local_papers",
        {"paths": paths, "metadata_json": metadata_json, "project": project},
    )

    project_error = project_context_error(project)
    if project_error:
        return project_error

    project_msg = ensure_project_exists()

    raw_paths = [p.strip() for chunk in paths.splitlines() for p in chunk.split(",")]
    parsed_paths = [p for p in raw_paths if p]
    if not parsed_paths:
        return "❌ No valid paths provided."

    metadata_items = _parse_import_metadata(metadata_json, parsed_paths)
    if isinstance(metadata_items, str):
        return metadata_items

    results = _import_local_files(ref_manager, parsed_paths, metadata_items)

    output = "\n".join(results)
    log_tool_result("import_local_papers", output)
    return output + project_msg


def ingest_web_source(
    url: str,
    content: str,
    metadata_json: str = "",
    project: Optional[str] = None,
) -> str:
    """
    Import a fetched web page snapshot into the canonical wiki pipeline.

    Args:
        url: Original source URL
        content: Markdown/text content captured from the page
        metadata_json: Optional JSON metadata object
        project: Project slug (default: current)
    """
    ref_manager = REFERENCE.get().ref_manager
    log_tool_call(
        "ingest_web_source",
        {
            "url": url,
            "has_content": bool(content.strip()),
            "project": project,
        },
    )

    project_error = project_context_error(project)
    if project_error:
        return project_error

    if not url.strip():
        return "❌ URL is required."
    if not content.strip():
        return "❌ content is required."

    metadata, error = parse_metadata_json(metadata_json)
    if error:
        return error

    project_msg = ensure_project_exists()
    result = ref_manager.import_web_source(url, content, metadata=metadata)
    log_tool_result("ingest_web_source", result)
    return result + project_msg


def ingest_markdown_source(
    markdown_text: str = "",
    source_path: str = "",
    metadata_json: str = "",
    project: Optional[str] = None,
) -> str:
    """
    Import markdown text or a markdown file into the canonical wiki pipeline.

    Args:
        markdown_text: Raw markdown content
        source_path: Optional local markdown path
        metadata_json: Optional JSON metadata object
        project: Project slug (default: current)
    """
    ref_manager = REFERENCE.get().ref_manager
    log_tool_call(
        "ingest_markdown_source",
        {
            "source_path": source_path,
            "has_markdown_text": bool(markdown_text.strip()),
            "project": project,
        },
    )

    project_error = project_context_error(project)
    if project_error:
        return project_error

    metadata, error = parse_metadata_json(metadata_json)
    if error:
        return error

    if not markdown_text.strip() and not source_path.strip():
        return "❌ Provide either markdown_text or source_path."

    project_msg = ensure_project_exists()
    if source_path.strip():
        result = ref_manager.import_markdown_file(source_path, metadata=metadata)
    else:
        result = ref_manager.import_markdown_content(
            markdown_text,
            source_name=metadata.get("imported_from", "") if metadata else "",
            metadata=metadata,
        )
    log_tool_result("ingest_markdown_source", result)
    return result + project_msg
