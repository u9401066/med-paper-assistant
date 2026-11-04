"""Single source of truth for the MedPaper workspace root.

The workspace root is the directory that owns ``projects/``, ``logs/`` and the
workspace-level state files. Resolution order:

1. ``MEDPAPER_BASE_DIR`` (set by the VS Code extension or the user).
2. ``CLAUDE_PROJECT_DIR`` (exported by Claude Code to plugin subprocesses).
3. The current working directory, unless it lies inside an Agent Plugins
   package (``PLUGIN_ROOT``). Agent Plugins clients launch stdio MCP servers
   with the plugin root as their working directory, and package contents are
   replaced on update, so user data must never be written there. In that case
   the client-managed persistent ``PLUGIN_DATA`` directory is used instead.
"""

from __future__ import annotations

import os
from pathlib import Path

WORKSPACE_ENV_VARS: tuple[str, ...] = ("MEDPAPER_BASE_DIR", "CLAUDE_PROJECT_DIR")
PLUGIN_ROOT_ENV_VARS: tuple[str, ...] = (
    "PLUGIN_ROOT",
    "CLAUDE_PLUGIN_ROOT",
    "COPILOT_PLUGIN_ROOT",
)
PLUGIN_DATA_ENV_VARS: tuple[str, ...] = (
    "PLUGIN_DATA",
    "CLAUDE_PLUGIN_DATA",
    "COPILOT_PLUGIN_DATA",
)
PLUGIN_WORKSPACE_DIRNAME = "workspace"


def _first_env(names: tuple[str, ...]) -> str | None:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def plugin_root() -> Path | None:
    """Return the Agent Plugins package root when running as a plugin subprocess."""
    value = _first_env(PLUGIN_ROOT_ENV_VARS)
    return Path(value).expanduser().resolve() if value else None


def plugin_workspace_dir() -> Path | None:
    """Return the persistent plugin-managed workspace directory, if available."""
    value = _first_env(PLUGIN_DATA_ENV_VARS)
    if not value:
        return None
    return (Path(value).expanduser() / PLUGIN_WORKSPACE_DIRNAME).resolve()


def resolve_workspace_root() -> Path:
    """Resolve the MedPaper workspace root (see module docstring for order)."""
    configured = _first_env(WORKSPACE_ENV_VARS)
    if configured:
        return Path(configured).expanduser().resolve()

    cwd = Path.cwd().resolve()
    package_root = plugin_root()
    if package_root is not None and _is_within(cwd, package_root):
        data_workspace = plugin_workspace_dir()
        if data_workspace is not None:
            data_workspace.mkdir(parents=True, exist_ok=True)
            return data_workspace
    return cwd
