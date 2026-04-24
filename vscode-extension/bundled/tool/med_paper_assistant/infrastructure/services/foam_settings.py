"""
Foam VS Code Settings Manager.

Manages dynamic Foam settings to ensure project isolation.
When switching projects, updates foam.files.ignore to exclude
other projects' references directories.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import structlog

logger = structlog.get_logger()


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

    MANAGED_GRAPH_VIEW_NAMES = [
        "Default",
        "Evidence",
        "Writing",
        "Assets",
        "Review",
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
            custom_views = self._load_project_custom_graph_views(current_slug)
            graph_views = self._merge_graph_views(
                settings.get("foam.graph.views"),
                self._build_graph_views(current_slug, custom_views),
            )

            # Update foam.files.ignore
            settings["foam.files.ignore"] = ignore_list
            settings["foam.graph.views"] = graph_views
            settings["foam.graph.navigateToPreview"] = True

            # Write back (preserving some formatting)
            self._write_settings(settings)

            return {
                "success": True,
                "message": f"Foam settings updated for project '{current_slug}'",
                "graph_views": [view["name"] for view in graph_views],
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

    def _merge_graph_views(
        self, existing: Any, generated: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Preserve non-MedPaper custom views while replacing managed ones."""
        preserved: List[Dict[str, Any]] = []
        generated_names = {
            str(view.get("name", "")).strip() for view in generated if isinstance(view, dict)
        }
        if isinstance(existing, list):
            for view in existing:
                if not isinstance(view, dict):
                    continue
                name = str(view.get("name", "")).strip()
                if not name or name in generated_names or name in self.MANAGED_GRAPH_VIEW_NAMES:
                    continue
                preserved.append(view)

        return generated + preserved

    def _build_graph_views(
        self,
        current_slug: str,
        custom_views: List[Dict[str, Any]] | None = None,
    ) -> List[Dict[str, Any]]:
        """Generate MedPaper-managed Foam named views for the active project."""
        groups = self._build_graph_groups(current_slug)
        default_show = {
            "tag": {"enabled": False, "color": "#f4d35e"},
            "placeholder": {"enabled": False, "color": "#c7ced6"},
            "attachment": {"enabled": False, "color": "#7d8597"},
            "image": {"enabled": False, "color": "#ff99c8"},
        }

        managed_views = [
            {
                "name": "Default",
                "colorBy": "type",
                "background": "#fbfcff",
                "lineColor": "#7a8ca5",
                "fontSize": 12,
                "show": default_show,
                "groups": groups,
            },
            {
                "name": "Evidence",
                "colorBy": "type",
                "background": "#fcfffd",
                "lineColor": "#7f9c8d",
                "fontSize": 12,
                "show": default_show,
                "groups": [
                    *groups,
                    self._group("hide-writing", "note_domain", "writing", "#d9d9d9", enabled=False),
                    self._group("hide-assets", "note_domain", "asset", "#d9d9d9", enabled=False),
                ],
            },
            {
                "name": "Writing",
                "colorBy": "type",
                "background": "#fffdf7",
                "lineColor": "#c49a5a",
                "fontSize": 12,
                "show": default_show,
                "groups": [
                    *groups,
                    self._group(
                        "hide-literature", "note_domain", "literature", "#d9d9d9", enabled=False
                    ),
                    self._group(
                        "hide-synthesis", "note_domain", "synthesis", "#d9d9d9", enabled=False
                    ),
                ],
            },
            {
                "name": "Assets",
                "colorBy": "type",
                "background": "#fffafc",
                "lineColor": "#b86c8b",
                "fontSize": 12,
                "show": {
                    **default_show,
                    "attachment": {"enabled": True, "color": "#7d8597"},
                    "image": {"enabled": True, "color": "#ff99c8"},
                },
                "groups": [
                    *groups,
                    self._group(
                        "hide-literature", "note_domain", "literature", "#d9d9d9", enabled=False
                    ),
                    self._group("hide-writing", "note_domain", "writing", "#d9d9d9", enabled=False),
                    self._group(
                        "hide-synthesis", "note_domain", "synthesis", "#d9d9d9", enabled=False
                    ),
                ],
            },
            {
                "name": "Review",
                "colorBy": "type",
                "background": "#fffdfb",
                "lineColor": "#ae7f5a",
                "fontSize": 12,
                "show": default_show,
                "groups": [
                    *groups,
                    self._group("review-pending", "review_state", "pending", "#f07167"),
                    self._group("review-reviewed", "review_state", "reviewed", "#2a9d8f"),
                    self._group("analysis-pending", "analysis_state", "pending", "#f4a261"),
                    self._group("fulltext-missing", "fulltext_state", "missing", "#e76f51"),
                ],
            },
        ]
        return managed_views + self._build_custom_graph_views(
            current_slug, groups, default_show, custom_views or []
        )

    def _build_graph_groups(self, current_slug: str) -> List[Dict[str, Any]]:
        """Define reusable graph groups for MedPaper note taxonomy."""
        return [
            self._group("project", "project", current_slug, "#1d3557"),
            self._group("reference", "type", "reference", "#2c7da0"),
            self._group("knowledge-map", "type", "knowledge-map", "#588157"),
            self._group("synthesis-page", "type", "synthesis-page", "#6a4c93"),
            self._group("library-overview", "type", "library-overview", "#457b9d"),
            self._group("library-dashboard", "type", "library-dashboard", "#5a7d9a"),
            self._group("library-review", "type", "library-review", "#c46b48"),
            self._group("library-daily", "type", "library-daily", "#6c757d"),
            self._group("publish-index", "type", "publish-index", "#264653"),
            self._group("publish-links", "type", "publish-links", "#2a9d8f"),
            self._group("draft-section", "type", "draft-section", "#ffb703"),
            self._group("figure-note", "type", "figure-note", "#e76f51"),
            self._group("table-note", "type", "table-note", "#8d99ae"),
            self._group("literature", "note_domain", "literature", "#277da1"),
            self._group("writing", "note_domain", "writing", "#f4a261"),
            self._group("asset", "note_domain", "asset", "#c9184a"),
            self._group("synthesis", "note_domain", "synthesis", "#6d597a"),
            self._group("library", "note_domain", "library", "#457b9d"),
            self._group("export", "note_domain", "export", "#2a9d8f"),
            self._group("methods", "section_kind", "methods", "#bc6c25"),
            self._group("results", "section_kind", "results", "#2a9d8f"),
            self._group("discussion", "section_kind", "discussion", "#9b5de5"),
            self._group("figure-assets", "asset_type", "figure", "#ef476f"),
            self._group("table-assets", "asset_type", "table", "#118ab2"),
        ]

    def _load_project_custom_graph_views(self, current_slug: str) -> List[Dict[str, Any]]:
        project_config_path = self.projects_dir / current_slug / "project.json"
        if not project_config_path.exists():
            return []

        try:
            config = json.loads(project_config_path.read_text(encoding="utf-8"))
        except Exception:
            logger.debug("Failed to load project config for custom graph views", exc_info=True)
            return []

        settings = config.get("settings", {}) if isinstance(config, dict) else {}
        custom_views = settings.get("custom_graph_views", []) if isinstance(settings, dict) else []
        if not isinstance(custom_views, list):
            return []
        return [view for view in custom_views if isinstance(view, dict)]

    def _build_custom_graph_views(
        self,
        current_slug: str,
        base_groups: List[Dict[str, Any]],
        default_show: Dict[str, Any],
        custom_views: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        generated: List[Dict[str, Any]] = []
        for index, spec in enumerate(custom_views, start=1):
            name = str(spec.get("name", "")).strip()
            raw_match = spec.get("match")
            match: dict[str, Any] = raw_match if isinstance(raw_match, dict) else {}
            property_name = str(match.get("property") or spec.get("property") or "").strip()
            value = str(match.get("value") or spec.get("value") or "").strip()
            if not name or not property_name or not value:
                continue

            color = str(spec.get("color") or "#457b9d")
            background = str(spec.get("background") or "#f8fbff")
            line_color = str(spec.get("lineColor") or "#7a8ca5")
            group_id = f"custom-{self._slugify(name)}-{index}"
            view_groups = [*base_groups, self._group(group_id, property_name, value, color)]

            hide_specs = spec.get("hide", []) if isinstance(spec.get("hide"), list) else []
            for hide_index, hide_spec in enumerate(hide_specs, start=1):
                if not isinstance(hide_spec, dict):
                    continue
                hide_property = str(hide_spec.get("property") or "").strip()
                hide_value = str(hide_spec.get("value") or "").strip()
                if not hide_property or not hide_value:
                    continue
                hide_color = str(hide_spec.get("color") or "#d9d9d9")
                hide_id = f"{group_id}-hide-{hide_index}"
                view_groups.append(
                    self._group(hide_id, hide_property, hide_value, hide_color, enabled=False)
                )

            generated.append(
                {
                    "name": name,
                    "colorBy": str(spec.get("colorBy") or "type"),
                    "background": background,
                    "lineColor": line_color,
                    "fontSize": int(spec.get("fontSize") or 12),
                    "show": default_show,
                    "groups": view_groups,
                }
            )

        return generated

    def _slugify(self, value: str) -> str:
        import re

        normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return normalized or "view"

    def _group(
        self,
        group_id: str,
        property_name: str,
        value: str,
        color: str,
        *,
        enabled: bool = True,
    ) -> Dict[str, Any]:
        return {
            "id": group_id,
            "label": f"{property_name}={value}",
            "color": color,
            "enabled": enabled,
            "match": {"property": property_name, "value": value},
        }

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
            logger.debug("Failed to read foam ignore list", exc_info=True)
            return []
