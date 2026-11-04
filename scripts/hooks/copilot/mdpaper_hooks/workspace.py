"""Read-only access to the workspace files the lifecycle hooks care about.

Covers ``.copilot-mode.json``, ``.mdpaper-state.json``, ``.current_project``,
``projects/<slug>/project.json`` and ``.audit/pending-evolutions.yaml``.
Everything degrades to an empty/neutral value instead of raising.
"""

from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path
from typing import Any

from .common import Payload, alt

MODE_FILE = ".copilot-mode.json"
STATE_FILE = ".mdpaper-state.json"
CURRENT_PROJECT_FILE = ".current_project"
PENDING_EVOLUTIONS_FILE = Path(".audit") / "pending-evolutions.yaml"

_ITEM_START = re.compile(r"^(\s*)-\s+id:")
_STATUS_LINE = re.compile(r"^(\s*)status:\s*['\"]?([^'\"\s#]*)")


def read_json(path: Path) -> Any:
    """Parsed JSON, or ``None`` when the file is missing, unreadable or invalid."""
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def read_mode_file(path: Path) -> str | None:
    """Mode in a JSON file: ``None`` if the file is missing, ``normal`` if unreadable."""
    if not path.is_file():
        return None
    data = read_json(path)
    if not isinstance(data, dict):
        return "normal"
    mode = data.get("mode")
    return "normal" if mode is None or mode is False else alt(mode)


def read_workspace_mode(root: Path) -> str | None:
    return read_mode_file(root / MODE_FILE)


def mode_or_normal(root: Path) -> str:
    """Workspace mode where a missing ``.copilot-mode.json`` means ``normal``."""
    mode = read_workspace_mode(root)
    return "normal" if mode is None else mode


def read_state(root: Path) -> Payload:
    data = read_json(root / STATE_FILE)
    return data if isinstance(data, dict) else {}


def writing_section(state: Payload) -> str:
    session = state.get("writing_session")
    return alt(session.get("section")) if isinstance(session, dict) else ""


def read_current_project_file(root: Path) -> str:
    try:
        return (root / CURRENT_PROJECT_FILE).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def resolve_active_project(root: Path, state: Payload, *, prefer_current_file: bool) -> str:
    """Active project slug from ``.current_project`` and the workspace state file.

    SessionStart/SubagentStart prefer the state file; UserPromptSubmit/PostToolUse
    prefer ``.current_project``.
    """
    from_state = alt(state.get("active_project"))
    from_file = read_current_project_file(root)
    first, second = (from_file, from_state) if prefer_current_file else (from_state, from_file)
    return first or second


def _is_plain_project_name(name: str) -> bool:
    return bool(name) and name not in {".", "..", "null"} and Path(name).name == name


def workflow_mode(root: Path, project: str, *, on_error: str = "") -> str:
    """``workflow_mode`` of a project (default ``manuscript``), ``""`` if unknown."""
    if not _is_plain_project_name(project):
        return ""
    config = root / "projects" / project / "project.json"
    if not config.is_file():
        return ""
    data = read_json(config)
    if not isinstance(data, dict):
        return on_error
    value = data.get("workflow_mode")
    return "manuscript" if value is None or value is False else alt(value)


def active_workflow_mode(root: Path) -> str:
    """Workflow mode of the active project as seen by prompt/post-tool hooks."""
    project = resolve_active_project(root, read_state(root), prefer_current_file=True)
    return workflow_mode(root, project)


def count_projects(root: Path) -> int | None:
    """Number of non-temporary project directories, ``None`` without ``projects/``."""
    projects = root / "projects"
    if not projects.is_dir():
        return None
    try:
        return sum(
            1
            for entry in projects.iterdir()
            if entry.is_dir()
            and not entry.is_symlink()
            and not fnmatch.fnmatchcase(entry.name, "temp-*")
        )
    except OSError:
        return 0


def _is_pending(status: str | None) -> bool:
    return status in (None, "pending")


def count_pending_evolutions(root: Path) -> int:
    """Items in ``.audit/pending-evolutions.yaml`` whose status is pending.

    A tiny indentation-aware scan keeps the hook free of a YAML dependency. It
    handles both ``- id:`` at column 0 (what ``PendingEvolutionStore`` writes)
    and indented lists, and ignores ``- id:`` lines nested inside an item.
    """
    try:
        text = (root / PENDING_EVOLUTIONS_FILE).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    pending = 0
    base_indent: int | None = None
    status: str | None = None
    in_item = False
    for line in text.splitlines():
        start = _ITEM_START.match(line)
        if start and base_indent in (None, len(start.group(1))):
            pending += int(in_item and _is_pending(status))
            base_indent, status, in_item = len(start.group(1)), None, True
            continue
        found = _STATUS_LINE.match(line)
        if in_item and found and base_indent is not None:
            if len(found.group(1)) == base_indent + 2:
                status = found.group(2)
    return pending + int(in_item and _is_pending(status))
