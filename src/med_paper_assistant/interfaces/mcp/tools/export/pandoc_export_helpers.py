"""Shared helpers for the Pandoc export tools (pipeline, gates, paths, reports)."""

import os
from pathlib import Path
from typing import Any, NamedTuple

from med_paper_assistant.infrastructure.services.drafter import normalize_draft_filename
from med_paper_assistant.shared.path_guard import normalize_relative_filename, resolve_child_path

from .._shared import log_tool_error
from .export_inputs import entry_title, require_drafts_dir


class _DraftLocation(NamedTuple):
    drafts_dir: str
    safe_name: str
    path: str
    error: str | None


def _get_pipeline():
    """Lazy-initialize ExportPipeline with current project context."""
    from med_paper_assistant.application.export_pipeline import ExportPipeline
    from med_paper_assistant.infrastructure.persistence import get_project_manager
    from med_paper_assistant.infrastructure.persistence.reference_manager import (
        ReferenceManager,
    )
    from med_paper_assistant.infrastructure.services.pandoc_exporter import PandocExporter

    pm = get_project_manager()
    ref_manager = ReferenceManager(project_manager=pm)
    pandoc = PandocExporter()
    return ExportPipeline(ref_manager, pandoc), pm


def _run_pre_export_citation_gate(content: str, project_dir: str) -> str | None:
    """Run C5 wikilink-resolvable hook as a HARD GATE before export.

    Args:
        content: Draft markdown content (with [[wikilink]] citations).
        project_dir: Absolute path to the project directory.

    Returns:
        None if all citations resolve; error message string if any fail.
    """
    from med_paper_assistant.infrastructure.persistence.writing_hooks import (
        WritingHooksEngine,
    )

    engine = WritingHooksEngine(project_dir=Path(project_dir))
    c5_result = engine.check_wikilink_resolvable(content)

    if c5_result.passed:
        return None

    # Build a clear error message listing every unresolved wikilink
    unresolved = [iss.message for iss in c5_result.issues if iss.severity == "CRITICAL"]
    detail = "\n".join(f"  - {msg}" for msg in unresolved)
    return (
        f"❌ **Export blocked — {c5_result.stats.get('unresolved', '?')} "
        f"unresolved citation(s)**\n\n"
        f"{detail}\n\n"
        f"Fix: Save missing references with `save_reference_mcp(pmid)` "
        f"or correct the wikilinks, then retry export.\n\n"
        f"ℹ️ Hook C5 (Wikilink Resolvable) — pre-export HARD GATE"
    )


def _run_pre_export_review_gate(project_dir: str) -> str | None:
    """Check that Phase 7 review loop was completed before allowing export.

    Returns:
        None if review is complete; error message string if not.
    """
    from med_paper_assistant.infrastructure.persistence.pipeline_gate_validator import (
        PipelineGateValidator,
    )

    validator = PipelineGateValidator(project_dir=Path(project_dir))
    passed, details = validator._check_review_completed()
    if passed:
        return None

    return (
        f"❌ **Export blocked — Review loop not completed**\n\n"
        f"📊 {details}\n\n"
        f"## 🔧 REMEDIATION REQUIRED\n\n"
        f"1. Call `start_review_round()` to begin a review round\n"
        f"2. Write a review report and author response\n"
        f"3. Call `submit_review_round()` to complete the round\n"
        f"4. Repeat until minimum rounds are met\n"
        f"5. Retry export\n\n"
        f"⚠️ This is a **Code-Enforced** hard gate. "
        f"Export cannot proceed without completing the review loop."
    )


def _resolve_draft_path(drafts_dir: str, draft_filename: str) -> tuple[str, str]:
    safe_draft = normalize_draft_filename(draft_filename)
    return (
        safe_draft,
        str(
            resolve_child_path(
                drafts_dir,
                safe_draft,
                field_name="Draft filename",
                allowed_suffixes={".md"},
            )
        ),
    )


def _resolve_output_path(
    exports_dir: str,
    output_filename: str,
    suffix: str,
    field_name: str = "Output filename",
) -> tuple[str, str]:
    safe_output = normalize_relative_filename(
        output_filename,
        field_name=field_name,
        default_suffix=suffix,
        allowed_suffixes={suffix},
    )
    return (
        safe_output,
        str(
            resolve_child_path(
                exports_dir,
                safe_output,
                field_name=field_name,
                allowed_suffixes={suffix},
            )
        ),
    )


def _find_draft(pm: Any, draft_filename: str) -> _DraftLocation:
    drafts_dir = require_drafts_dir(pm.get_project_paths())
    safe_draft_filename, draft_path = _resolve_draft_path(drafts_dir, draft_filename)
    error = None
    if not os.path.exists(draft_path):
        error = f"❌ Draft file not found: `{safe_draft_filename}`"
    return _DraftLocation(drafts_dir, safe_draft_filename, draft_path, error)


def _prepare_export_path(
    drafts_dir: str,
    output_filename: str,
    suffix: str,
    field_name: str = "Output filename",
) -> str:
    exports_dir = os.path.join(os.path.dirname(drafts_dir), "exports")
    os.makedirs(exports_dir, exist_ok=True)
    _, output_path = _resolve_output_path(exports_dir, output_filename, suffix, field_name)
    return output_path


def _export_output_path(draft: _DraftLocation, output_filename: str | None, suffix: str) -> str:
    if not output_filename:
        output_filename = f"{os.path.splitext(draft.safe_name)[0]}{suffix}"
    return _prepare_export_path(draft.drafts_dir, output_filename, suffix)


def _read_draft(draft_path: str) -> str:
    with open(draft_path, "r", encoding="utf-8") as f:
        return f.read()


def _pre_export_gate_error(
    tool_name: str, draft_path: str, project_dir: str, draft_filename: str
) -> str | None:
    """Run the C5 citation gate then the review-loop gate; None when both pass."""
    gate_error = _run_pre_export_citation_gate(_read_draft(draft_path), project_dir)
    if gate_error:
        log_tool_error(tool_name, Exception("C5 gate failed"), {"draft": draft_filename})
        return gate_error

    review_error = _run_pre_export_review_gate(project_dir)
    if review_error:
        log_tool_error(tool_name, Exception("Review gate failed"), {"draft": draft_filename})
        return review_error
    return None


def _project_metadata(pm: Any, *, with_date: bool) -> dict[str, Any] | None:
    """Extract project metadata for title/author injection."""
    project_info = pm.get_project_info()
    if not project_info.get("success"):
        return None
    authors = project_info.get("authors", [])
    metadata: dict[str, Any] = {
        "title": project_info.get("name", ""),
        "authors": authors if authors else [],
    }
    if with_date:
        metadata["date"] = project_info.get("created_at", "")[:10]  # YYYY-MM-DD
    return metadata


def _export_report(headline: str, result: dict[str, Any], csl_style: str) -> str:
    output = headline
    output += f"📄 Output: `{result['output_path']}`\n"
    output += f"📚 Citation tokens prepared: {result['citations_converted']}\n"
    output += f"✅ Bibliography entries resolved: {result.get('citations_resolved', 0)}\n"
    output += f"🎨 Citation style: {csl_style}\n"

    if result.get("citation_keys"):
        output += f"\n**Citation keys** ({len(result['citation_keys'])}):\n"
        for key in result["citation_keys"]:
            output += f"- `{key}`\n"

    if result.get("warnings"):
        output += "\n⚠️ **Warnings:**\n"
        for w in result["warnings"]:
            output += f"- {w}\n"
    return output


def _preview_keys_section(prepared: dict[str, Any]) -> str:
    output = "**Citation keys found:**\n"
    for key in prepared["citation_keys"]:
        output += f"- `[[{key}]]` → `[@{key}]`\n"

    output += f"\n**Bibliography entries resolved:** {len(prepared['bibliography'])} / {len(prepared['citation_keys'])}\n"

    if prepared["bibliography"]:
        output += "\n**CSL-JSON preview:**\n"
        for entry in prepared["bibliography"][:5]:
            title = entry_title(entry)
            output += f"- `{entry.get('id', '?')}`: {title}\n"
        if len(prepared["bibliography"]) > 5:
            output += f"  ... and {len(prepared['bibliography']) - 5} more\n"
    return output


def _preview_report(safe_draft_filename: str, prepared: dict[str, Any]) -> str:
    output = "📋 **Citation Preview**\n\n"
    output += f"📄 File: `{safe_draft_filename}`\n"
    output += f"🔄 Citations converted: {prepared['conversion'].citations_converted}\n\n"

    if prepared["citation_keys"]:
        output += _preview_keys_section(prepared)
    else:
        output += "No citations found in this draft.\n"

    if prepared["warnings"]:
        output += "\n⚠️ **Warnings:**\n"
        for w in prepared["warnings"]:
            output += f"- {w}\n"
    return output


def _bibliography_report(bib_path: str, entries: list[dict[str, Any]]) -> str:
    output = "✅ **Bibliography built successfully**\n\n"
    output += f"📄 Output: `{bib_path}`\n"
    output += f"📚 Entries: {len(entries)}\n\n"

    if entries:
        output += "**References:**\n"
        for entry in entries:
            title = entry_title(entry)
            authors = entry.get("author", [])
            first_author = authors[0].get("family", "?") if authors else "?"
            year = entry.get("issued", {}).get("date-parts", [[None]])[0][0] or "?"
            output += f"- {first_author} ({year}). {title}\n"
    return output
