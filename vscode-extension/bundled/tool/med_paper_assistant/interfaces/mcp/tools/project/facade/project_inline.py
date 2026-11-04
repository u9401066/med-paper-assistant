"""Project facade actions that run inline instead of delegating to a registered tool."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from med_paper_assistant.infrastructure.persistence.exemplar_usage_store import (
    ALLOWED_EXEMPLAR_ROLES,
    ExemplarPolicyError,
    ExemplarUsageStore,
)

from ..._shared import resolve_project_context
from ..facade_guards import JOURNAL_PROFILE_FILENAME, source_dir_error, write_journal_profile
from .asset_ingestion import record_asset_ingestion_receipt
from .journal_profile import build_journal_profile
from .project_args import ProjectActionArgs
from .source_scan import write_source_materials_manifest


def _parse_json_list(raw: str, field_name: str) -> tuple[list[Any], str]:
    """Parse a JSON list/dict field for facade inputs."""
    if not raw.strip():
        return [], ""
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError as exc:
        return [], f"invalid {field_name} JSON: {exc.msg}"
    if isinstance(loaded, list):
        return loaded, ""
    if isinstance(loaded, dict):
        if isinstance(loaded.get("sections"), list):
            return loaded["sections"], ""
        if isinstance(loaded.get("items"), list):
            return loaded["items"], ""
        return list(loaded.keys()), ""
    return [], f"{field_name} must be a JSON list or object"


def _project_or_error(slug: str) -> tuple[dict[str, Any] | None, str]:
    project_info, workflow_error = resolve_project_context(slug or None)
    if workflow_error or project_info is None:
        return None, workflow_error or "❌ Project context could not be resolved."
    return project_info, ""


def journal_profile_action(args: ProjectActionArgs) -> str:
    project_info, error = _project_or_error(args.slug)
    if project_info is None:
        return error
    project_dir = Path(project_info["project_path"])
    profile = build_journal_profile(
        target_journal=args.target_journal or project_info.get("target_journal", ""),
        paper_type=args.paper_type or project_info.get("paper_type", ""),
        citation_style=args.citation_style,
        language_preference=args.language_preference,
        writing_style=args.writing_style,
    )
    profile_path = project_dir / JOURNAL_PROFILE_FILENAME
    if blocked := write_journal_profile(profile_path, profile, overwrite=args.confirm):
        return blocked
    return (
        "status: ok\n"
        "action: journal_profile\n"
        f"file: {profile_path.relative_to(project_dir).as_posix()}\n"
        f"journal: {profile['journal']['name']}\n"
        f"paper_type: {profile['paper']['type']}\n"
        f"citation_style: {profile['references']['style']}\n"
        'next: project_action(action="source_materials"), then pipeline_action(action="validate_phase", phase=0)'
    )


def source_materials_action(args: ProjectActionArgs) -> str:
    project_info, error = _project_or_error(args.slug)
    if project_info is None:
        return error
    project_dir = Path(project_info["project_path"])
    if scan_error := source_dir_error(args.source_dir, project_dir):
        return scan_error
    manifest_path, report_path, manifest = write_source_materials_manifest(
        project_dir=project_dir,
        project_slug=str(project_info.get("slug", args.slug or project_dir.name)),
        source_dir=args.source_dir,
        max_depth=args.max_depth,
        include_markdown=args.include_markdown,
        include_project_files=args.include_project_files,
    )
    summary = manifest["summary"]
    pending_paths = manifest["agent_next_steps"]["asset_aware_file_paths"][:10]
    pending_lines = "\n".join(f"  - {path}" for path in pending_paths)
    if not pending_lines:
        pending_lines = "  []"
    return (
        "status: ok\n"
        "action: source_materials\n"
        f"manifest: {manifest_path.relative_to(project_dir).as_posix()}\n"
        f"report: {report_path.relative_to(project_dir).as_posix()}\n"
        f"scan_root: {manifest['scan_root']}\n"
        f"total_candidates: {summary['total_candidates']}\n"
        f"pending_asset_aware: {summary['pending_asset_aware']}\n"
        f"ready_native: {summary['ready_native']}\n"
        "asset_aware_file_paths:\n"
        f"{pending_lines}\n"
        'next: call asset-aware ingest_documents for pending paths, then pipeline_action(action="validate_phase", phase=0)'
    )


def record_asset_ingestion_action(args: ProjectActionArgs) -> str:
    project_info, error = _project_or_error(args.slug)
    if project_info is None:
        return error
    sections, sections_error = _parse_json_list(args.sections_json, "sections_json")
    if sections_error:
        return f"❌ {sections_error}"
    artifact_paths, artifact_error = _parse_json_list(
        args.artifact_paths_json,
        "artifact_paths_json",
    )
    if artifact_error:
        return f"❌ {artifact_error}"

    ok, message = record_asset_ingestion_receipt(
        project_dir=Path(project_info["project_path"]),
        source_material_id=args.source_material_id,
        source_path=args.source_path,
        asset_aware_doc_id=args.asset_aware_doc_id,
        sections=sections,
        artifact_paths=artifact_paths,
        ingestion_status=args.ingestion_status,
    )
    if not ok:
        return f"❌ {message}"
    return (
        "status: ok\n"
        "action: record_asset_ingestion\n"
        f"{message}\n"
        'next: pipeline_action(action="validate_phase", phase=21)'
    )


def _list_exemplar_usage(store: ExemplarUsageStore, project_dir: Path) -> str:
    summary = store.summary()
    allowed_roles = ", ".join(sorted(ALLOWED_EXEMPLAR_ROLES))
    return (
        "status: ok\n"
        "action: exemplar_usage\n"
        "mode: list\n"
        f"artifact: {store.path.relative_to(project_dir).as_posix()}\n"
        f"total_records: {summary['total']}\n"
        f"integrity_passed: {str(summary['integrity_passed']).lower()}\n"
        f"allowed_roles: {allowed_roles}\n"
        "policy: exemplars provide transformative calibration only; independently "
        "verify every evidence and citation claim"
    )


def _record_exemplar_usage(
    args: ProjectActionArgs, store: ExemplarUsageStore, project_dir: Path
) -> str:
    roles, roles_error = _parse_json_list(args.exemplar_roles_json, "exemplar_roles_json")
    if roles_error:
        return f"❌ {roles_error}"
    target_sections, target_error = _parse_json_list(
        args.exemplar_target_sections_json,
        "exemplar_target_sections_json",
    )
    if target_error:
        return f"❌ {target_error}"
    try:
        record = store.record(
            source_id=args.exemplar_source_id,
            roles=roles,
            target_sections=target_sections,
            purpose=args.exemplar_purpose,
            source_sha256=args.exemplar_source_sha256,
        )
    except ExemplarPolicyError as exc:
        return f"❌ Exemplar policy violation: {exc}"
    return (
        "status: ok\n"
        "action: exemplar_usage\n"
        "mode: record\n"
        f"record_id: {record['id']}\n"
        f"artifact: {store.path.relative_to(project_dir).as_posix()}\n"
        f"roles: {', '.join(record['roles'])}\n"
        "evidence_eligible: false\n"
        "citation_credit: false\n"
        "requires_independent_verification: true"
    )


def exemplar_usage_action(args: ProjectActionArgs) -> str:
    project_info, error = _project_or_error(args.slug)
    if project_info is None:
        return error
    project_dir = Path(project_info["project_path"])
    store = ExemplarUsageStore(project_dir)

    if not args.exemplar_source_id.strip():
        return _list_exemplar_usage(store, project_dir)
    return _record_exemplar_usage(args, store, project_dir)


INLINE_ACTIONS: dict[str, Callable[[ProjectActionArgs], str]] = {
    "journal_profile": journal_profile_action,
    "source_materials": source_materials_action,
    "record_asset_ingestion": record_asset_ingestion_action,
    "exemplar_usage": exemplar_usage_action,
}
