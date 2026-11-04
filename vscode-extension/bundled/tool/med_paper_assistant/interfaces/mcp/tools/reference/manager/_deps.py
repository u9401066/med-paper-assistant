"""Registration-time dependencies and shared helpers for the reference manager tools."""

import json
from dataclasses import dataclass
from typing import Any, Optional

from med_paper_assistant.infrastructure.persistence import ReferenceManager

from ..._binding import DepsBinding
from ..._shared import ensure_project_context, get_project_list_for_prompt


@dataclass(frozen=True)
class ReferenceDeps:
    ref_manager: ReferenceManager
    project_manager: Any


REFERENCE: DepsBinding[ReferenceDeps] = DepsBinding("reference_manager_deps")


def ensure_project_exists() -> str:
    """Ensure a project exists for saving references."""
    project_manager = REFERENCE.get().project_manager
    if project_manager is None:
        return ""

    current = project_manager.get_current_project()
    if current:
        return ""

    result = project_manager.get_or_create_temp_project()
    if result.get("success"):
        return "\n\n💡 *已自動建立文獻探索工作區。找到研究方向後，使用 `convert_exploration_to_project` 轉換為正式專案。*"
    return ""


def parse_metadata_json(metadata_json: str) -> tuple[Optional[dict], Optional[str]]:
    if not metadata_json.strip():
        return {}, None

    try:
        parsed_metadata = json.loads(metadata_json)
    except json.JSONDecodeError as exc:
        return None, f"❌ Invalid metadata_json: {exc}"

    if not isinstance(parsed_metadata, dict):
        return None, "❌ metadata_json must decode to a JSON object."

    return parsed_metadata, None


def parse_reference_ids(reference_ids: str) -> list[str]:
    return [
        item.strip()
        for line in reference_ids.splitlines()
        for item in line.split(",")
        if item.strip()
    ]


def project_context_error(
    project: Optional[str], *, with_project_list: bool = True
) -> Optional[str]:
    """Return the error text when ``project`` cannot be activated, else ``None``."""
    if not project:
        return None
    is_valid, msg, _project_info = ensure_project_context(project)
    if is_valid:
        return None
    if with_project_list:
        return f"❌ {msg}\n\n{get_project_list_for_prompt()}"
    return f"❌ {msg}"
