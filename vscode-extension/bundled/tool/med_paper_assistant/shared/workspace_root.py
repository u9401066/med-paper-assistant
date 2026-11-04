"""Single source of truth for the MedPaper workspace root.

The workspace root is the directory that owns ``projects/``, ``logs/`` and the
workspace-level state files. Resolution order:

1. An explicit runtime binding made through :func:`bind_workspace_root`
   (``workspace_state_action(action="bind", workspace_dir=...)``). MCP roots
   are deprecated (SEP-2577), so the agent passes the user's workspace folder
   as an ordinary tool parameter instead.
2. ``MEDPAPER_BASE_DIR`` (set by the VS Code extension or the user).
3. ``CLAUDE_PROJECT_DIR`` (exported by Claude Code to plugin subprocesses).
4. The current working directory, unless it lies inside an Agent Plugins
   package (``PLUGIN_ROOT``). Agent Plugins clients launch stdio MCP servers
   with the plugin root as their working directory, and package contents are
   replaced on update, so user data must never be written there. In that case
   the client-managed persistent ``PLUGIN_DATA`` directory is used instead.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import NamedTuple

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

SOURCE_BOUND = "bound"
SOURCE_PLUGIN_DATA = "plugin_data"
SOURCE_CWD = "cwd"

_bound_root: Path | None = None


class WorkspaceRoot(NamedTuple):
    """A resolved workspace root together with where it came from."""

    path: Path
    source: str


def _first_env_item(names: tuple[str, ...]) -> tuple[str, str] | None:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return name, value
    return None


def _first_env(names: tuple[str, ...]) -> str | None:
    item = _first_env_item(names)
    return item[1] if item else None


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


def describe_workspace_root() -> WorkspaceRoot:
    """Resolve the workspace root and report its source.

    ``source`` is ``"bound"``, ``"env:<NAME>"``, ``"plugin_data"`` or ``"cwd"``.
    """
    if _bound_root is not None:
        return WorkspaceRoot(_bound_root, SOURCE_BOUND)

    configured = _first_env_item(WORKSPACE_ENV_VARS)
    if configured:
        name, value = configured
        return WorkspaceRoot(Path(value).expanduser().resolve(), f"env:{name}")

    cwd = Path.cwd().resolve()
    package_root = plugin_root()
    if package_root is not None and _is_within(cwd, package_root):
        data_workspace = plugin_workspace_dir()
        if data_workspace is not None:
            data_workspace.mkdir(parents=True, exist_ok=True)
            return WorkspaceRoot(data_workspace, SOURCE_PLUGIN_DATA)
    return WorkspaceRoot(cwd, SOURCE_CWD)


def resolve_workspace_root() -> Path:
    """Resolve the MedPaper workspace root (see module docstring for order)."""
    return describe_workspace_root().path


def bind_workspace_root(workspace_dir: str | os.PathLike[str]) -> Path:
    """Bind this server process to an explicit workspace directory.

    The directory must be an existing absolute path outside the Agent Plugins
    package. The binding takes precedence over environment variables because it
    is a deliberate runtime choice; it lasts until the process exits or
    :func:`clear_workspace_binding` is called.
    """
    global _bound_root
    raw = str(workspace_dir).strip()
    if not raw:
        raise ValueError("workspace_dir is required")
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        raise ValueError(f"workspace_dir must be an absolute path, got: {raw}")
    resolved = candidate.resolve()
    if not resolved.is_dir():
        raise ValueError(f"workspace_dir does not exist or is not a directory: {resolved}")
    package_root = plugin_root()
    if package_root is not None and _is_within(resolved, package_root):
        raise ValueError(
            "workspace_dir lies inside the Agent Plugins package, whose contents are "
            f"replaced on update: {resolved}"
        )
    _bound_root = resolved
    return resolved


def clear_workspace_binding() -> None:
    """Drop the runtime binding so env/cwd resolution applies again."""
    global _bound_root
    _bound_root = None
