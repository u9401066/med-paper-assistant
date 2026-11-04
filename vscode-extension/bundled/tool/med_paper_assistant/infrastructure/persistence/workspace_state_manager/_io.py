"""State file read/write, forward-compat defaults, and v1 → v2 migration."""

import json
from datetime import datetime
from typing import Any

import structlog

from . import _models
from ._paths import ProjectPathsMixin

logger = structlog.get_logger()


class StateIOMixin(ProjectPathsMixin):
    """Read, write, and migrate the per-project ``.mdpaper-state.json``."""

    STATE_VERSION = _models.STATE_VERSION

    # =========================================================================
    # State Read/Write
    # =========================================================================

    def get_state(self) -> dict[str, Any]:
        """
        Get the current project state.

        Returns:
            State dictionary with defaults if file doesn't exist.
        """
        sf = self.state_file
        if not sf.exists():
            # Try auto-migrate from root-level v1 state
            self._maybe_migrate_v1()
            if not sf.exists():
                return self._default_state()

        try:
            content = sf.read_text(encoding="utf-8")
            state = json.loads(content)

            # Ensure all required keys exist (forward compat)
            default = self._default_state()
            for key in default:
                if key not in state:
                    state[key] = default[key]
            for key, value in default.get("pipeline_state", {}).items():
                state.setdefault("pipeline_state", {}).setdefault(key, value)

            return state
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read state file {sf}: {e}")
            return self._default_state()

    def save_state(self, state: dict[str, Any]) -> bool:
        """
        Save the project state.

        Args:
            state: State dictionary to save.

        Returns:
            True if saved successfully.
        """
        sf = self.state_file
        try:
            # Ensure parent directory exists
            sf.parent.mkdir(parents=True, exist_ok=True)

            state["version"] = self.STATE_VERSION
            state["last_updated"] = datetime.now().isoformat()

            content = json.dumps(state, indent=2, ensure_ascii=False)
            sf.write_text(content, encoding="utf-8")
            return True
        except OSError as e:
            logger.error(f"Failed to save state file {sf}: {e}")
            return False

    def _maybe_migrate_v1(self) -> None:
        """
        Auto-migrate root-level v1 state file to per-project location.

        If root .mdpaper-state.json exists with version=1 and its
        current_project matches our current project, migrate the data.
        """
        root_file = self.base_path / self.STATE_FILE
        if not root_file.is_file():
            return

        slug = self._get_current_project_slug()
        if not slug:
            return

        try:
            target = self._project_dir(slug) / self.STATE_FILE
        except ValueError:
            return
        if target.exists():
            return

        try:
            content = root_file.read_text(encoding="utf-8")
            old_state = json.loads(content)

            if old_state.get("version") != 1:
                return

            # Only migrate if the old state was for this project
            old_project = old_state.get("current_project")
            if old_project and old_project != slug:
                return

            # Build v2 state from v1 data (drop current_project field)
            new_state = self._default_state()
            for key in [
                "last_activity",
                "workspace_state",
                "recovery_hints",
                "cross_mcp_state",
                "pipeline_state",
            ]:
                if key in old_state:
                    new_state[key] = old_state[key]

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(new_state, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.info(f"Migrated v1 state to {target}")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to migrate v1 state: {e}")

    def _default_state(self) -> dict[str, Any]:
        """Return default state structure (v2: per-project, no current_project)."""
        return _models.build_default_state(self.STATE_VERSION)
