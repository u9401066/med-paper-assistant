"""
Foam VS Code Settings Manager.

Manages dynamic Foam settings to ensure project isolation.
When switching projects, updates foam.files.ignore to exclude
other projects' references directories.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class FoamSettingsManager:
    """
    Manages VS Code settings for Foam project isolation.

    Ensures that when working on Project A, references from
    Project B are not visible in Foam autocomplete.
    """

    # Directories that should always be ignored by Foam
    # Use whitelist approach: exclude everything except current project's references
    ALWAYS_IGNORE = [
        # Root level - exclude everything
        ".venv/**",
        "node_modules/**",
        ".git/**",
        "__pycache__/**",
        "integrations/**",
        "tests/**",
        "dashboard/**",
        "memory-bank/**",
        "templates/**",
        "scripts/**",
        ".claude/**",
        ".github/**",
        "src/**",
        "docs/**",
        "*.md",
        "*.json",
        "*.toml",
        "*.yaml",
        "*.yml",
        "*.txt",
        "*.lock",
    ]

    # Within current project, exclude everything except references
    PROJECT_INTERNAL_IGNORE = [
        "concept.md",
        "project.json",
        ".memory/**",
        "drafts/**",
        "data/**",
        "results/**",
    ]

    def __init__(self, workspace_root: Path):
        """
        Initialize Foam settings manager.

        Args:
            workspace_root: Root of the VS Code workspace.
        """
        self.workspace_root = workspace_root
        self.settings_path = workspace_root / ".vscode" / "settings.json"
        self.projects_dir = workspace_root / "projects"

    def update_for_project(self, current_slug: str) -> Dict[str, Any]:
        """
        Update Foam settings to isolate the current project.

        Args:
            current_slug: The slug of the current active project.

        Returns:
            Result of the update operation.
        """
        if not self.settings_path.exists():
            return {"success": False, "error": "VS Code settings.json not found"}

        try:
            # Read current settings (handle JSONC comments)
            settings_text = self.settings_path.read_text(encoding="utf-8")
            settings = self._parse_jsonc(settings_text)

            # Build new ignore list
            ignore_list = self._build_ignore_list(current_slug)

            # Update foam.files.ignore
            settings["foam.files.ignore"] = ignore_list

            # Write back (preserving some formatting)
            self._write_settings(settings)

            return {
                "success": True,
                "message": f"Foam settings updated for project '{current_slug}'",
                "ignored_projects": [
                    p
                    for p in ignore_list
                    if p.startswith("projects/") and p != f"projects/{current_slug}/**"
                ],
            }

        except Exception as e:
            logger.error(f"Failed to update Foam settings: {e}")
            return {"success": False, "error": f"Failed to update Foam settings: {str(e)}"}

    def _build_ignore_list(self, current_slug: str) -> List[str]:
        """
        Build the foam.files.ignore list using WHITELIST approach.

        ONLY projects/{current_slug}/references/** is visible to Foam.
        Everything else is ignored.

        Strategy:
        1. ALWAYS_IGNORE: Root-level exclusions (src, docs, *.md, etc.)
        2. PROJECT_INTERNAL_IGNORE: Within current project, exclude non-reference files
        3. Other projects: Entirely excluded

        Args:
            current_slug: Current project (only its references/ will be visible).

        Returns:
            List of glob patterns to ignore.
        """
        ignore_list = list(self.ALWAYS_IGNORE)

        # Add current project's internal exclusions (everything except references/)
        for pattern in self.PROJECT_INTERNAL_IGNORE:
            ignore_list.append(f"projects/{current_slug}/{pattern}")

        # Exclude all other projects entirely
        if self.projects_dir.exists():
            for project_dir in self.projects_dir.iterdir():
                if project_dir.is_dir() and project_dir.name != current_slug:
                    ignore_list.append(f"projects/{project_dir.name}/**")

        return ignore_list

    def _parse_jsonc(self, text: str) -> Dict[str, Any]:
        """
        Parse JSONC (JSON with comments) by removing comments.

        Args:
            text: JSONC text content.

        Returns:
            Parsed dictionary.
        """
        import re

        # Remove single-line comments
        text = re.sub(r"//.*$", "", text, flags=re.MULTILINE)
        # Remove multi-line comments
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        # Remove trailing commas before } or ]
        text = re.sub(r",(\s*[}\]])", r"\1", text)

        return json.loads(text)

    def _write_settings(self, settings: Dict[str, Any]) -> None:
        """
        Write settings back to file with nice formatting.

        Args:
            settings: Settings dictionary to write.
        """
        # Write with nice formatting
        content = json.dumps(settings, indent=4, ensure_ascii=False)
        self.settings_path.write_text(content, encoding="utf-8")

    def get_current_ignore_list(self) -> List[str]:
        """
        Get the current foam.files.ignore list.

        Returns:
            Current ignore patterns or empty list.
        """
        if not self.settings_path.exists():
            return []

        try:
            settings_text = self.settings_path.read_text(encoding="utf-8")
            settings = self._parse_jsonc(settings_text)
            return settings.get("foam.files.ignore", [])
        except Exception:
            return []
