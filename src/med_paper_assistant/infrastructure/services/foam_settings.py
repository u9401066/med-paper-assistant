"""
Foam VS Code Settings Manager.

Manages dynamic Foam settings to ensure project isolation.
When switching projects, updates ``foam.files.exclude`` so only the active
project's notes are visible to Foam (the VS Code extension and the official
``foam-cli mcp`` server both read this setting from ``.vscode/settings.json``).
"""

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

import structlog

from med_paper_assistant.shared.foam_queries import write_saved_queries
from med_paper_assistant.shared.jsonc import loads_jsonc

from .foam_graph_views import (
    MANAGED_GRAPH_VIEW_NAMES,
    build_graph_views,
    load_project_custom_graph_views,
    merge_graph_views,
)

logger = structlog.get_logger()

LEGACY_IGNORE_KEY = "foam.files.ignore"
EXCLUDE_KEY = "foam.files.exclude"

# Foam 0.47 default for `foam.files.exclude` (foam-core vscode-settings.ts).
# The setting is an array, so writing it replaces these defaults unless merged.
FOAM_DEFAULT_FILES_EXCLUDE = [
    "**/.vscode/**/*",
    "**/_layouts/**/*",
    "**/_site/**/*",
    "**/node_modules/**/*",
    "**/.yarn/**/*",
    "**/vendor/bundle/**/*",
    "**/.venv/**/*",
    "**/venv/**/*",
    "**/env/**/*",
    "**/.env/**/*",
    "**/.direnv/**/*",
    "**/site-packages/**/*",
    "**/target/**/*",
    "**/dist/**/*",
    "**/build/**/*",
    "**/.next/**/*",
    "**/.nuxt/**/*",
    "**/.terraform/**/*",
    "**/.gradle/**/*",
    "**/.idea/**/*",
    "**/.cache/**/*",
    "**/__pycache__/**/*",
]


def _unique(patterns: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(patterns))


class FoamSettingsManager:
    """
    Manages VS Code settings for Foam project isolation.

    Ensures that when working on Project A, references from
    Project B are not visible in Foam autocomplete.
    """

    # Directories that should always be excluded from Foam.
    # Whitelist approach: exclude everything except the current project's notes.
    ALWAYS_IGNORE = [
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

    MANAGED_GRAPH_VIEW_NAMES = MANAGED_GRAPH_VIEW_NAMES

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
            settings = self._parse_jsonc(self.settings_path.read_text(encoding="utf-8"))

            isolation = self._build_ignore_list(current_slug)
            custom_views = load_project_custom_graph_views(self.projects_dir, current_slug)
            graph_views = merge_graph_views(
                settings.get("foam.graph.views"),
                build_graph_views(current_slug, custom_views),
            )

            settings[EXCLUDE_KEY] = self._build_exclude_list(isolation, settings)
            settings.pop(LEGACY_IGNORE_KEY, None)
            settings["foam.graph.views"] = graph_views
            settings["foam.graph.navigateToPreview"] = True
            self._write_settings(settings)

            return {
                "success": True,
                "message": f"Foam settings updated for project '{current_slug}'",
                "graph_views": [view["name"] for view in graph_views],
                "ignored_projects": [
                    p
                    for p in isolation
                    if p.startswith("projects/") and p != f"projects/{current_slug}/**"
                ],
                "saved_queries": write_saved_queries(self.workspace_root),
            }

        except Exception as e:
            logger.error(f"Failed to update Foam settings: {e}")
            return {"success": False, "error": f"Failed to update Foam settings: {str(e)}"}

    def _build_ignore_list(self, current_slug: str) -> List[str]:
        """
        Build MedPaper's project-isolation patterns (WHITELIST approach).

        1. ALWAYS_IGNORE: Root-level exclusions (src, docs, *.md, etc.)
        2. PROJECT_INTERNAL_IGNORE: Within current project, exclude non-note files
        3. Other projects: Entirely excluded
        """
        ignore_list = list(self.ALWAYS_IGNORE)
        ignore_list.extend(
            f"projects/{current_slug}/{pattern}" for pattern in self.PROJECT_INTERNAL_IGNORE
        )
        if self.projects_dir.exists():
            for project_dir in sorted(self.projects_dir.iterdir()):
                if project_dir.is_dir() and project_dir.name != current_slug:
                    ignore_list.append(f"projects/{project_dir.name}/**")
        return ignore_list

    def _build_exclude_list(self, isolation: List[str], settings: Dict[str, Any]) -> List[str]:
        """Merge Foam defaults, user-owned patterns and MedPaper isolation.

        Patterns under ``projects/`` and the fixed isolation set are MedPaper-owned
        and recomputed on every switch; anything else the user added (in either
        the current or the deprecated key) is preserved.
        """
        managed = set(self.ALWAYS_IGNORE)
        user_patterns: List[str] = []
        for key in (EXCLUDE_KEY, LEGACY_IGNORE_KEY):
            existing = settings.get(key)
            for pattern in existing if isinstance(existing, list) else []:
                if isinstance(pattern, str) and pattern not in managed:
                    if not pattern.startswith("projects/"):
                        user_patterns.append(pattern)
        return _unique([*FOAM_DEFAULT_FILES_EXCLUDE, *user_patterns, *isolation])

    def _parse_jsonc(self, text: str) -> Dict[str, Any]:
        """Parse JSONC (JSON with comments) settings into a dictionary."""
        parsed = loads_jsonc(text)
        if not isinstance(parsed, dict):
            raise ValueError("Foam settings must contain a JSON object")
        return parsed

    def _write_settings(self, settings: Dict[str, Any]) -> None:
        content = json.dumps(settings, indent=4, ensure_ascii=False)
        self.settings_path.write_text(content, encoding="utf-8")
