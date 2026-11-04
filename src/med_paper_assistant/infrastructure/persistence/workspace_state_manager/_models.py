"""Constants and default-state schema for the workspace state file."""

from __future__ import annotations

from typing import Any

STATE_FILE = ".mdpaper-state.json"
STATE_VERSION = 2


def build_default_state(version: int) -> dict[str, Any]:
    """Return default state structure (v2: per-project, no current_project)."""
    return {
        "version": version,
        "last_activity": None,
        "last_updated": None,
        "workspace_state": {
            "open_drafts": [],
            "pending_validations": [],
            "last_search_pmids": [],
            "last_tool_called": None,
        },
        "recovery_hints": {
            "agent_was_doing": None,
            "next_suggested_action": None,
            "important_context": [],
        },
        "cross_mcp_state": {
            "pubmed_session_active": False,
            "cgu_session_active": False,
        },
        "pipeline_state": {
            "active": False,
            "project": None,
            "current_phase": None,
            "current_phase_name": None,
            "current_round": None,
            "last_gate_result": None,
            "last_gate_failures": [],
            "last_gate_details": None,
            "next_required_action": None,
            "phases_passed": [],
            "phases_remaining": [],
            "review_verdict": None,
            "last_heartbeat": None,
        },
        "writing_session": {
            "active": False,
            "current_section": None,
            "last_file_modified": None,
            "last_operation": None,
            "word_count": 0,
            "sections_on_disk": [],
            "timestamp": None,
            "agent_context": None,
        },
    }
