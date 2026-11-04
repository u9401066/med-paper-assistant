"""Pipeline doctor tool: one JSON readiness snapshot for the full pipeline."""

import json
import shutil
from pathlib import Path
from typing import Any, Optional

from med_paper_assistant.infrastructure.persistence.pipeline_gate_validator import (
    PipelineGateValidator,
)
from med_paper_assistant.shared.jsonc import load_jsonc

from ..._shared import log_tool_call, log_tool_error, log_tool_result
from .._tool_doc import nested_tool_doc
from ._common import _require_project_info, resolve_manuscript_project

_PHASE_TOOLS: list[dict[str, Any]] = [
    {
        "phase": 0,
        "tools": [
            "project_action:source_materials",
            "project_action:journal_profile",
            "project_action:record_asset_ingestion",
        ],
    },
    {
        "phase": 1,
        "tools": [
            "project_action:create",
            "project_action:update",
            "project_action:setup",
        ],
    },
    {"phase": 2, "tools": ["pubmed-search", "save_reference_mcp"]},
    {
        "phase": 21,
        "tools": [
            "asset-aware:ingest_documents",
            "project_action:record_asset_ingestion",
            "pipeline_action:validate_phase",
        ],
    },
    {
        "phase": 3,
        "tools": [
            "validation_action:concept",
            "pipeline_action:approve_concept_review",
        ],
    },
    {"phase": 4, "tools": ["manuscript-plan", "pipeline_action:validate_phase"]},
    {
        "phase": 5,
        "tools": [
            "draft_action",
            "analysis_action",
            "run_quality_checks:writing_hooks",
        ],
    },
    {
        "phase": 6,
        "tools": ["run_quality_checks:quality", "run_quality_checks:data_artifacts"],
    },
    {"phase": 65, "tools": ["evolution-log", "quality-scorecard"]},
    {
        "phase": 7,
        "tools": [
            "pipeline_action:start_review",
            "pipeline_action:submit_review",
            "run_quality_checks:review",
        ],
    },
    {"phase": 8, "tools": ["sync_references", "validation_action:wikilinks"]},
    {
        "phase": 9,
        "tools": [
            "export_document:docx",
            "export_document:pdf",
            "inspect_export:inspect_docx_xml",
        ],
    },
    {
        "phase": 10,
        "tools": [
            "run_quality_checks:pipeline_retrospective",
            "run_quality_checks:meta_learning",
        ],
    },
    {
        "phase": 11,
        "tools": ["pipeline_action:validate_phase", "optional_git_provenance"],
    },
]


def _workspace_root(project_dir: Path) -> Path:
    """Locate the workspace root that owns ``.vscode/mcp.json``."""
    return (
        project_dir.parent.parent if project_dir.parent.name == "projects" else project_dir.parent
    )


def _external_mcp_status(workspace_root: Path) -> dict[str, Any]:
    """Report whether the companion MCP servers are declared and runnable."""
    mcp_path = workspace_root / ".vscode" / "mcp.json"
    servers: dict[str, Any] = {}
    if mcp_path.is_file():
        try:
            parsed = load_jsonc(mcp_path)
            if isinstance(parsed, dict):
                servers = parsed.get("servers") or parsed.get("mcpServers") or {}
        except (json.JSONDecodeError, OSError):
            servers = {}

    external = {}
    for name in ["asset-aware", "pubmed-search", "drawio"]:
        spec = servers.get(name, {}) if isinstance(servers, dict) else {}
        command = str(spec.get("command") or "")
        command_found = bool(shutil.which(command)) if command else False
        external[name] = {
            "declared": bool(spec),
            "command": command,
            "command_found": command_found,
            "args": spec.get("args") if isinstance(spec.get("args"), list) else [],
            "status": (
                "ready" if command_found else "declared_but_command_missing" if spec else "missing"
            ),
        }
    return external


def _last_gate() -> Any:
    """Return the last recorded gate details, if the workspace state is readable."""
    try:
        from med_paper_assistant.infrastructure.persistence.workspace_state_manager import (
            get_workspace_state_manager,
        )

        workspace_state = get_workspace_state_manager().get_state()
        last_gate = workspace_state.get("pipeline_state", {}).get("last_gate_details")
    except Exception:
        return None
    return last_gate


@nested_tool_doc
def pipeline_doctor(
    project: Optional[str] = None,
) -> str:
    """Return one JSON readiness snapshot for the full 11-phase pipeline."""
    log_tool_call("pipeline_doctor", {"project": project})
    try:
        project_info, workflow_error = resolve_manuscript_project(project)
        if workflow_error:
            return workflow_error
        project_info = _require_project_info(project_info)
        project_dir = Path(project_info["project_path"])
        workspace_root = _workspace_root(project_dir)

        validator = PipelineGateValidator(project_dir)
        status = validator.get_pipeline_status()

        external = _external_mcp_status(workspace_root)
        last_gate = _last_gate()

        payload = {
            "schema": "mdpaper.pipeline_doctor.v1",
            "project": project_info.get("slug"),
            "project_path": str(project_dir),
            "pipeline_status": status,
            "phase_tools": _PHASE_TOOLS,
            "external_mcp": external,
            "last_gate": last_gate,
        }
        log_tool_result("pipeline_doctor", "doctor snapshot generated", success=True)
        return json.dumps(payload, ensure_ascii=False, indent=2)
    except Exception as e:
        log_tool_error("pipeline_doctor", e)
        return f"❌ Error running pipeline doctor: {e}"
