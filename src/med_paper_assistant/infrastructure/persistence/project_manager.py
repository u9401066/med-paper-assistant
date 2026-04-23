"""
Project Manager - Multi-project support for MedPaper Assistant

Manages separate workspaces for different research papers, each with its own:
- concept.md
- drafts/
- references/
- data/
- results/
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from ...domain.paper_types import (
    PAPER_TYPES,
    get_paper_type_dict,
    is_valid_paper_type,
    list_paper_types,
)
from ...shared.constants import DEFAULT_WORKFLOW_MODE, WORKFLOW_MODES, PROJECT_DIRECTORIES, LIBRARY_DIRECTORIES
from ...shared.path_guard import normalize_relative_filename, resolve_child_path
from ..services.concept_template_reader import ConceptTemplateReader
from .project_memory_manager import ProjectMemoryManager

logger = structlog.get_logger()


class ProjectManager:
    """
    Manages multiple research paper projects with isolated directory structures.

    Each project has:
    - project.json: metadata and settings
    - concept.md: research concept
    - .memory/: project-specific AI memory (activeContext.md, progress.md)
    - drafts/: paper drafts
    - references/: saved references (by PMID)
    - data/: analysis data files
    - results/: exported documents

    Special project:
    - temp_project: A temporary workspace for literature exploration before
                    committing to a formal project. Can be converted to a
                    real project with all saved references preserved.
    """

    # Subdirectories for each project

    # Current project state file
    STATE_FILE = ".current_project"

    # Valid project statuses
    VALID_STATUSES = ["concept", "drafting", "review", "submitted", "published"]

    # Temporary project for exploration
    TEMP_PROJECT_SLUG = "temp-exploration"

    def __init__(self, base_path: str | None = None):
        """
        Initialize ProjectManager.

        Args:
            base_path: Base directory for the med-paper-assistant workspace.
                       Falls back to MEDPAPER_BASE_DIR env var, then CWD.
        """
        if base_path is None:
            base_path = os.environ.get("MEDPAPER_BASE_DIR", ".")
        self.base_path = Path(base_path).resolve()
        self.projects_dir = self.base_path / "projects"
        self.state_file = self.base_path / self.STATE_FILE

        # Initialize helpers
        self.template_reader = ConceptTemplateReader()

        # Ensure projects directory exists
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def _directories_for_workflow(self, workflow_mode: str) -> List[str]:
        """Return the directory layout for a workflow mode."""
        return LIBRARY_DIRECTORIES if workflow_mode == "library-wiki" else PROJECT_DIRECTORIES

    def _build_structure_paths(self, project_path: Path, workflow_mode: str) -> Dict[str, str]:
        """Build mode-aware path mappings for a project."""
        paths = {
            "root": str(project_path),
            "concept": str(project_path / "concept.md"),
            "memory": str(project_path / ".memory"),
            "references": str(project_path / "references"),
            "config": str(project_path / "project.json"),
        }

        if workflow_mode == "library-wiki":
            paths.update(
                {
                    "inbox": str(project_path / "inbox"),
                    "concepts": str(project_path / "concepts"),
                    "projects": str(project_path / "projects"),
                    "review": str(project_path / "review"),
                    "daily": str(project_path / "daily"),
                }
            )
        else:
            paths.update(
                {
                    "drafts": str(project_path / "drafts"),
                    "data": str(project_path / "data"),
                    "results": str(project_path / "results"),
                }
            )

        return paths

    def _normalize_project_slug(self, slug: str) -> str:
        return normalize_relative_filename(slug, field_name="project slug")

    def _project_path_for_slug(self, slug: str) -> tuple[str, Path]:
        safe_slug = self._normalize_project_slug(slug)
        return safe_slug, resolve_child_path(self.projects_dir, safe_slug, field_name="project slug")

    # =========================================================================
    # Project CRUD Operations
    # =========================================================================

    def create_project(
        self,
        name: str,
        description: str = "",
        authors: Optional[List[Any]] = None,
        target_journal: str = "",
        paper_type: str = "",
        workflow_mode: str = DEFAULT_WORKFLOW_MODE,
        interaction_preferences: Optional[Dict[str, Any]] = None,
        memo: str = "",
    ) -> Dict[str, Any]:
        """
        Create a new research paper project.

        Args:
            name: Human-readable project name.
            description: Brief description of the research.
            authors: List of author names.
            target_journal: Target journal for submission.
            paper_type: Type of paper (original-research, meta-analysis, etc.)
            workflow_mode: Workflow mode (manuscript or library-wiki).
            interaction_preferences: User preferences for AI interaction.
            memo: Additional notes and reminders.

        Returns:
            Project info dictionary.
        """
        slug = self._make_unique_slug(name)
        slug, project_path = self._project_path_for_slug(slug)

        if paper_type and not is_valid_paper_type(paper_type):
            return {
                "success": False,
                "error": f"Invalid paper type '{paper_type}'. Valid types: {list_paper_types()}",
            }

        if workflow_mode not in WORKFLOW_MODES:
            return {
                "success": False,
                "error": f"Invalid workflow mode '{workflow_mode}'. Valid modes: {list(WORKFLOW_MODES)}",
            }

        # Create directory structure
        project_path.mkdir(parents=True)
        for subdir in self._directories_for_workflow(workflow_mode):
            (project_path / subdir).mkdir()

        # Create project config
        project_config = self._create_project_config(
            name,
            slug,
            description,
            authors,
            target_journal,
            paper_type,
            workflow_mode,
            interaction_preferences,
            memo,
        )
        self._save_config(project_path, project_config)

        # Create concept.md or library workspace seed
        seed_content = self._build_workspace_seed_document(
            project_name=name,
            paper_type=paper_type,
            target_journal=target_journal,
            memo=memo,
            workflow_mode=workflow_mode,
        )
        (project_path / "concept.md").write_text(seed_content, encoding="utf-8")

        # Create memory files
        memory_manager = ProjectMemoryManager(project_path)
        memory_manager.create_memory_files(
            project_name=name,
            paper_type=paper_type,
            workflow_mode=workflow_mode,
            interaction_preferences=interaction_preferences,
            memo=memo,
        )

        # Set as current project
        self._save_current_project(slug)

        # Update Foam settings immediately so named views and graph scope exist
        self._update_foam_settings(slug)
        self._refresh_foam_graph()

        return {
            "success": True,
            "message": f"Project '{name}' created successfully!",
            "slug": slug,
            "path": str(project_path),
            "workflow_mode": workflow_mode,
            "structure": self._build_structure_paths(project_path, workflow_mode),
        }

    def switch_project(self, slug: str) -> Dict[str, Any]:
        """
        Switch to an existing project.

        Also updates Foam settings to isolate this project's references
        from other projects.

        Args:
            slug: Project slug (directory name).

        Returns:
            Project info or error.
        """
        return self.set_current_project(slug, refresh_foam=True)

    def set_current_project(self, slug: str, *, refresh_foam: bool = False) -> Dict[str, Any]:
        """Set the active project and optionally refresh Foam integration."""
        try:
            slug, project_path = self._project_path_for_slug(slug)
        except ValueError as exc:
            return {"success": False, "error": f"Invalid project slug: {exc}"}

        if not project_path.exists():
            available = self.list_projects()
            return {
                "success": False,
                "error": f"Project '{slug}' not found.",
                "available_projects": [p["slug"] for p in available.get("projects", [])],
            }

        self._save_current_project(slug)

        project_info = self.get_project_info(slug)

        if not refresh_foam:
            return project_info

        # Update Foam settings for project isolation
        foam_result = self._update_foam_settings(slug)
        graph_result = self._refresh_foam_graph()

        # Add Foam update info
        if foam_result.get("success"):
            project_info["foam_isolation"] = {
                "enabled": True,
                "ignored_projects": foam_result.get("ignored_projects", []),
            }
            project_info["foam_views"] = foam_result.get("graph_views", [])

        if graph_result.get("success"):
            project_info["foam_graph"] = graph_result

        return project_info

    def _update_foam_settings(self, slug: str) -> Dict[str, Any]:
        """
        Update Foam VS Code settings for project isolation.

        Args:
            slug: Current project slug.

        Returns:
            Result of Foam settings update.
        """
        try:
            from ..services.foam_settings import FoamSettingsManager

            # workspace_root is parent of projects_dir
            workspace_root = self.projects_dir.parent
            foam_manager = FoamSettingsManager(workspace_root)
            return foam_manager.update_for_project(slug)
        except Exception as e:
            # Non-fatal: log but don't fail the switch
            logger.warning("Foam settings update failed", error=str(e))
            return {"success": False, "error": str(e)}

    def _refresh_foam_graph(self) -> Dict[str, Any]:
        """Refresh Foam-facing graph nodes and index for the active project."""
        try:
            from .reference_manager import ReferenceManager

            ref_manager = ReferenceManager(project_manager=self)
            stats = ref_manager.refresh_foam_graph()
            return {"success": True, **stats}
        except Exception as e:
            logger.warning("Foam graph refresh failed", error=str(e))
            return {"success": False, "error": str(e)}

    def delete_project(self, slug: str, confirm: bool = False) -> Dict[str, Any]:
        """
        Delete a project (requires confirmation).

        Args:
            slug: Project slug to delete.
            confirm: Must be True to actually delete.

        Returns:
            Result of deletion.
        """
        if not confirm:
            return {
                "success": False,
                "error": "Deletion requires confirm=True. This will permanently delete all project data!",
            }

        try:
            slug, project_path = self._project_path_for_slug(slug)
        except ValueError as exc:
            return {"success": False, "error": f"Invalid project slug: {exc}"}

        if not project_path.exists():
            return {"success": False, "error": f"Project '{slug}' not found"}
        if not (project_path / "project.json").exists():
            return {"success": False, "error": f"Project '{slug}' is missing project.json; refusing deletion."}

        import shutil

        shutil.rmtree(project_path)

        # Clear current if this was the current project
        if self.get_current_project() == slug:
            if self.state_file.exists():
                self.state_file.unlink()

        return {"success": True, "message": f"Project '{slug}' deleted permanently."}

    # =========================================================================
    # Project Query Operations
    # =========================================================================

    def get_current_project(self) -> Optional[str]:
        """Get the slug of the currently active project."""
        if not self.state_file.exists():
            return None

        try:
            return self.state_file.read_text().strip() or None
        except Exception:
            logger.debug("Failed to read current project state", exc_info=True)
            return None

    def get_project_info(self, slug: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed info about a project.

        Args:
            slug: Project slug. If None, uses current project.

        Returns:
            Project info dictionary.
        """
        if slug is None:
            slug = self.get_current_project()
            if slug is None:
                return {
                    "success": False,
                    "error": "No project selected. Use create_project or switch_project first.",
                }

        try:
            slug, project_path = self._project_path_for_slug(slug)
        except ValueError as exc:
            return {"success": False, "error": f"Invalid project slug: {exc}"}
        config = self._load_config(project_path)

        if config is None:
            return {"success": False, "error": f"Project '{slug}' not found or corrupted."}

        # Count contents
        stats = self._get_project_stats(project_path)

        return {
            "success": True,
            "slug": slug,
            "is_current": slug == self.get_current_project(),
            **config,
            "project_path": str(project_path),
            "paths": self.get_project_paths(slug),
            "stats": stats,
        }

    def get_project_paths(self, slug: Optional[str] = None) -> Dict[str, str]:
        """
        Get all paths for a project.

        Args:
            slug: Project slug. If None, uses current project.

        Returns:
            Dictionary of path names to absolute paths.
        """
        if slug is None:
            slug = self.get_current_project()
            if slug is None:
                raise ValueError("No project selected")

        slug, project_path = self._project_path_for_slug(slug)
        config = self._load_config(project_path) or {}
        workflow_mode = config.get("workflow_mode", DEFAULT_WORKFLOW_MODE)

        return self._build_structure_paths(project_path, workflow_mode)

    def list_projects(self) -> Dict[str, Any]:
        """List all projects."""
        projects = []
        current = self.get_current_project()

        if not self.projects_dir.exists():
            return {"projects": [], "current": None, "count": 0}

        for project_dir in sorted(self.projects_dir.iterdir()):
            if not project_dir.is_dir():
                continue

            config = self._load_config(project_dir)
            if config is None:
                projects.append(
                    {
                        "slug": project_dir.name,
                        "name": project_dir.name,
                        "status": "error",
                        "is_current": project_dir.name == current,
                    }
                )
            else:
                projects.append(
                    {
                        "slug": project_dir.name,
                        "name": config.get("name", project_dir.name),
                        "status": config.get("status", "unknown"),
                        "paper_type": config.get("paper_type", ""),
                        "workflow_mode": config.get("workflow_mode", DEFAULT_WORKFLOW_MODE),
                        "created_at": config.get("created_at", ""),
                        "is_current": project_dir.name == current,
                    }
                )

        return {"projects": projects, "current": current, "count": len(projects)}

    # =========================================================================
    # Project Update Operations
    # =========================================================================

    def update_project_status(self, status: str, slug: Optional[str] = None) -> Dict[str, Any]:
        """
        Update project status.

        Args:
            status: New status (concept, drafting, review, submitted, published).
            slug: Project slug. If None, uses current project.

        Returns:
            Updated project info.
        """
        if slug is None:
            slug = self.get_current_project()
            if slug is None:
                return {"success": False, "error": "No project selected"}

        if status not in self.VALID_STATUSES:
            return {
                "success": False,
                "error": f"Invalid status. Must be one of: {self.VALID_STATUSES}",
            }

        try:
            slug, project_path = self._project_path_for_slug(slug)
        except ValueError as exc:
            return {"success": False, "error": f"Invalid project slug: {exc}"}
        config = self._load_config(project_path)

        if config is None:
            return {"success": False, "error": f"Project '{slug}' not found"}

        config["status"] = status
        config["updated_at"] = datetime.now().isoformat()
        self._save_config(project_path, config)

        return {"success": True, "message": f"Project status updated to '{status}'", "slug": slug}

    def update_project_settings(
        self,
        slug: Optional[str] = None,
        paper_type: Optional[str] = None,
        workflow_mode: Optional[str] = None,
        target_journal: Optional[str] = None,
        interaction_preferences: Optional[Dict[str, Any]] = None,
        memo: Optional[str] = None,
        authors: Optional[List[str]] = None,
        description: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Update project settings.

        Args:
            slug: Project slug. If None, uses current project.
            paper_type: Type of paper.
            workflow_mode: Project workflow mode.
            target_journal: Target journal.
            interaction_preferences: User preferences for AI interaction.
            memo: Additional notes.
            authors: Author list.
            description: Project description.
            settings: Additional settings dict (e.g., citation_style).

        Returns:
            Updated project info.
        """
        if slug is None:
            slug = self.get_current_project()
            if slug is None:
                return {"success": False, "error": "No project selected"}

        try:
            slug, project_path = self._project_path_for_slug(slug)
        except ValueError as exc:
            return {"success": False, "error": f"Invalid project slug: {exc}"}
        config = self._load_config(project_path)

        if config is None:
            return {"success": False, "error": f"Project '{slug}' not found"}

        # Track updated fields
        updated_fields = []

        # Validate and update paper type
        if paper_type is not None:
            if not is_valid_paper_type(paper_type):
                return {
                    "success": False,
                    "error": f"Invalid paper type '{paper_type}'. Valid types: {list_paper_types()}",
                }
            config["paper_type"] = paper_type
            config["paper_type_info"] = get_paper_type_dict(paper_type)
            updated_fields.append("paper_type")

        if workflow_mode is not None:
            if workflow_mode not in WORKFLOW_MODES:
                return {
                    "success": False,
                    "error": f"Invalid workflow mode '{workflow_mode}'. Valid modes: {list(WORKFLOW_MODES)}",
                }
            config["workflow_mode"] = workflow_mode
            config["workflow_mode_info"] = WORKFLOW_MODES[workflow_mode]
            for subdir in self._directories_for_workflow(workflow_mode):
                (project_path / subdir).mkdir(exist_ok=True)
            updated_fields.append("workflow_mode")

        # Update other fields
        if target_journal is not None:
            config["target_journal"] = target_journal
            updated_fields.append("target_journal")

        if interaction_preferences is not None:
            existing_prefs = config.get("interaction_preferences", {})
            existing_prefs.update(interaction_preferences)
            config["interaction_preferences"] = existing_prefs
            updated_fields.append("interaction_preferences")

        if memo is not None:
            config["memo"] = memo
            updated_fields.append("memo")

        if authors is not None:
            config["authors"] = authors
            updated_fields.append("authors")

        if description is not None:
            config["description"] = description
            updated_fields.append("description")

        # Update generic settings dict (e.g., citation_style)
        if settings is not None:
            existing_settings = config.get("settings", {})
            existing_settings.update(settings)
            config["settings"] = existing_settings
            updated_fields.append("settings")

        config["updated_at"] = datetime.now().isoformat()
        self._save_config(project_path, config)

        # Update memory files if needed
        if workflow_mode is not None or paper_type is not None:
            memory_manager = ProjectMemoryManager(project_path)
            memory_manager.create_memory_files(
                project_name=config.get("name", slug),
                paper_type=config.get("paper_type", ""),
                workflow_mode=config.get("workflow_mode", DEFAULT_WORKFLOW_MODE),
                interaction_preferences=config.get("interaction_preferences", {}),
                memo=config.get("memo", ""),
            )
        elif interaction_preferences is not None or memo is not None:
            memory_manager = ProjectMemoryManager(project_path)
            memory_manager.update_preferences(
                config.get("interaction_preferences", {}), config.get("memo", "")
            )

        foam_result = None
        if slug == self.get_current_project():
            foam_result = self._update_foam_settings(slug)

        result = {
            "success": True,
            "message": "Project settings updated successfully",
            "slug": slug,
            "updated_fields": updated_fields,
        }
        if foam_result and foam_result.get("success"):
            result["foam_views"] = foam_result.get("graph_views", [])
        return result

    # =========================================================================
    # Paper Types (delegated to domain)
    # =========================================================================

    def get_paper_types(self) -> Dict[str, Dict[str, Any]]:
        """Return available paper types and their info."""
        return {k: v.to_dict() for k, v in PAPER_TYPES.items()}

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _slugify(self, name: str) -> str:
        """Convert project name to URL-safe slug."""
        import re

        slug = name.lower().strip()
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"[^a-z0-9\-]", "", slug)
        slug = re.sub(r"-+", "-", slug)
        slug = slug.strip("-")
        return slug or "untitled"

    def _make_unique_slug(self, name: str) -> str:
        """Generate a unique slug by appending a counter when needed."""
        slug = self._slugify(name)
        candidate = slug
        counter = 1

        while (self.projects_dir / candidate).exists():
            candidate = f"{slug}-{counter}"
            counter += 1

        return candidate

    def _save_current_project(self, slug: str) -> None:
        """Save current project to .current_project file."""
        self.state_file.write_text(slug)

    def _create_project_config(
        self,
        name: str,
        slug: str,
        description: str,
        authors: Optional[List[Any]],
        target_journal: str,
        paper_type: str,
        workflow_mode: str,
        interaction_preferences: Optional[Dict[str, Any]],
        memo: str,
    ) -> Dict[str, Any]:
        """Create project configuration dictionary.

        Authors can be:
        - List of strings (legacy): ["Name1", "Name2"]
        - List of dicts (structured): [{"name": "...", "affiliations": [...], ...}]
        """
        # Normalize authors to structured format
        normalized_authors = self._normalize_authors(authors or [])

        return {
            "name": name,
            "slug": slug,
            "description": description,
            "authors": normalized_authors,
            "target_journal": target_journal,
            "paper_type": paper_type,
            "paper_type_info": get_paper_type_dict(paper_type) if paper_type else {},
            "workflow_mode": workflow_mode,
            "workflow_mode_info": WORKFLOW_MODES.get(workflow_mode, {}),
            "interaction_preferences": interaction_preferences or {},
            "memo": memo,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "concept",
        }

    def _build_workspace_seed_document(
        self,
        project_name: str,
        paper_type: str,
        target_journal: str,
        memo: str,
        workflow_mode: str,
    ) -> str:
        """Create the initial concept/library workspace document."""
        if workflow_mode == "library-wiki":
            return self._build_library_workspace_seed(project_name, memo)

        return self.template_reader.get_concept_template(
            project_name=project_name,
            paper_type=paper_type,
            target_journal=target_journal,
            memo=memo,
        )

    def _build_library_workspace_seed(self, project_name: str, memo: str) -> str:
        """Create the initial library/wiki workspace document."""
        notes_block = memo.strip() if memo.strip() else "[No memo yet]"
        return f"""# Library Workspace: {project_name}

## Scope
<!-- What literature domain, corpus, or topic family should this workspace cover? -->

## Intake Priorities
<!-- Which papers, feeds, or local sources should be ingested first? -->

## Reading Queues
- Inbox
- Active reading
- Review worklists
- Synthesis targets

## Daily Capture
<!-- Use daily/ for journal-style capture pages and short-lived intake notes -->

## Knowledge Threads
<!-- Themes, methods, interventions, datasets, or claims to connect -->

## Open Questions
<!-- Questions the agent should answer from this library -->

## Optional Manuscript Paths
<!-- If a paper idea emerges later, outline it here before switching workflow_mode -->

## Author Notes
{notes_block}
"""

    def _build_conversion_message(self, workflow_mode: str, stats: Dict[str, int]) -> str:
        """Build a workflow-aware conversion summary for exploration workspaces."""
        if workflow_mode == "library-wiki":
            lines = [
                f"   - References: {stats.get('references', 0)}",
                f"   - Inbox notes: {stats.get('inbox', 0)}",
                f"   - Concept notes: {stats.get('concepts', 0)}",
                f"   - Synthesis projects: {stats.get('projects', 0)}",
                f"   - Review notes: {stats.get('review', 0)}",
                f"   - Daily notes: {stats.get('daily', 0)}",
            ]
        else:
            lines = [
                f"   - References: {stats.get('references', 0)}",
                f"   - Drafts: {stats.get('drafts', 0)}",
                f"   - Data files: {stats.get('data_files', 0)}",
            ]

        return "\n".join(lines)

    @staticmethod
    def _normalize_authors(authors: List[Any]) -> List[Dict[str, Any]]:
        """Normalize authors to structured format.

        Handles both legacy string entries and structured dicts.

        Args:
            authors: List of author names (str) or author dicts.

        Returns:
            List of structured author dicts.
        """
        from med_paper_assistant.domain.value_objects.author import Author

        result = []
        for i, entry in enumerate(authors):
            author = Author.from_dict(entry)
            # Assign order if not set
            if author.order == 0:
                author = Author(
                    name=author.name,
                    affiliations=list(author.affiliations),
                    orcid=author.orcid,
                    email=author.email,
                    is_corresponding=author.is_corresponding,
                    order=i + 1,
                )
            result.append(author.to_dict())
        return result

    def update_authors(self, authors: List[Any], slug: Optional[str] = None) -> Dict[str, Any]:
        """Update the authors list for a project.

        Args:
            authors: List of author dicts or strings.
            slug: Project slug (uses current if None).

        Returns:
            Success/error dict.
        """
        if slug is None:
            slug = self.get_current_project()
            if slug is None:
                return {"success": False, "error": "No project selected."}

        try:
            slug, project_path = self._project_path_for_slug(slug)
        except ValueError as exc:
            return {"success": False, "error": f"Invalid project slug: {exc}"}
        config = self._load_config(project_path)
        if config is None:
            return {"success": False, "error": f"Project '{slug}' not found."}

        config["authors"] = self._normalize_authors(authors)
        config["updated_at"] = datetime.now().isoformat()
        self._save_config(project_path, config)

        return {
            "success": True,
            "authors": config["authors"],
            "message": f"Updated {len(config['authors'])} author(s).",
        }

    def _save_config(self, project_path: Path, config: Dict[str, Any]) -> None:
        """Save project config to JSON file."""
        config_path = project_path / "project.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def _load_config(self, project_path: Path) -> Optional[Dict[str, Any]]:
        """Load project config from JSON file."""
        config_path = project_path / "project.json"
        if not config_path.exists():
            return None

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.debug("Failed to load config: %s", config_path, exc_info=True)
            return None

    def _get_project_stats(self, project_path: Path) -> Dict[str, int]:
        """Get project content statistics."""
        stats = {}

        # Manuscript mode stats
        if (project_path / "drafts").exists():
            stats["drafts"] = len(list((project_path / "drafts").glob("*.md")))
        if (project_path / "data").exists():
            stats["data_files"] = len(list((project_path / "data").glob("*.*")))

        # Library mode stats
        if (project_path / "inbox").exists():
            stats["inbox"] = len(list((project_path / "inbox").glob("*.md")))
        if (project_path / "concepts").exists():
            stats["concepts"] = len(list((project_path / "concepts").glob("*.md")))
        if (project_path / "projects").exists():
            stats["projects"] = len(list((project_path / "projects").glob("*.md")))
        if (project_path / "review").exists():
            stats["review"] = len(list((project_path / "review").glob("*.md")))
        if (project_path / "daily").exists():
            stats["daily"] = len(list((project_path / "daily").glob("*.md")))

        # Common stats
        if (project_path / "references").exists():
            stats["references"] = len(
                [d for d in (project_path / "references").iterdir() if d.is_dir()]
            )
        else:
            stats["references"] = 0

        return stats

    # =========================================================================
    # Temporary Project Operations (for literature exploration)
    # =========================================================================

    def get_or_create_temp_project(self) -> Dict[str, Any]:
        """
        Get or create the temporary exploration project.

        This project is for users who want to explore literature before
        committing to a formal research project. All saved references and
        notes are preserved and can be converted to a real project.

        Returns:
            Temp project info dictionary.
        """
        temp_path = self.projects_dir / self.TEMP_PROJECT_SLUG

        if temp_path.exists():
            # Return existing temp project info
            config = self._load_config(temp_path)
            if config:
                stats = self._get_project_stats(temp_path)
                return {
                    "success": True,
                    "slug": self.TEMP_PROJECT_SLUG,
                    "is_temp": True,
                    "message": "Using existing exploration workspace",
                    "paths": self.get_project_paths(self.TEMP_PROJECT_SLUG),
                    "stats": stats,
                    **config,
                }

        # Create new temp project
        temp_path.mkdir(parents=True)
        for subdir in self._directories_for_workflow("library-wiki"):
            (temp_path / subdir).mkdir(exist_ok=True)

        # Create minimal config
        config = {
            "name": "Literature Exploration",
            "slug": self.TEMP_PROJECT_SLUG,
            "description": "臨時工作區 - 用於探索文獻，尋找研究靈感。找到有興趣的主題後可轉換為正式專案。",
            "authors": [],
            "target_journal": "",
            "paper_type": "",
            "paper_type_info": {},
            "workflow_mode": "library-wiki",
            "workflow_mode_info": WORKFLOW_MODES["library-wiki"],
            "interaction_preferences": {},
            "memo": "這是一個暫存專案，用於文獻探索。使用 convert_temp_to_project 可將內容轉移到正式專案。",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "exploration",
            "is_temp": True,
        }
        self._save_config(temp_path, config)

        # Create library-oriented workspace seed
        concept_content = self._build_library_workspace_seed(
            "Literature Exploration",
            "這是一個暫存專案，用於文獻探索與 wiki 整理。",
        )
        (temp_path / "concept.md").write_text(concept_content, encoding="utf-8")

        # Set as current project
        self._save_current_project(self.TEMP_PROJECT_SLUG)

        return {
            "success": True,
            "slug": self.TEMP_PROJECT_SLUG,
            "is_temp": True,
            "message": "✅ 已建立文獻探索工作區！\n\n現在可以自由搜尋和保存文獻。找到研究方向後，使用 convert_temp_to_project 將內容轉移到正式專案。",
            "paths": self.get_project_paths(self.TEMP_PROJECT_SLUG),
            "stats": {
                "references": 0,
                "inbox": 0,
                "concepts": 0,
                "projects": 0,
                "review": 0,
                "daily": 0,
            },
        }

    def is_temp_project_active(self) -> bool:
        """Check if the temp project is currently active."""
        return self.get_current_project() == self.TEMP_PROJECT_SLUG

    def convert_temp_to_project(
        self,
        name: str,
        description: str = "",
        paper_type: str = "",
        workflow_mode: str = "",
        target_journal: str = "",
        keep_temp: bool = False,
    ) -> Dict[str, Any]:
        """
        Convert the temporary exploration project to a formal project.

        All references, drafts, data, and notes are moved to the new project.

        Args:
            name: Name for the new project (in English for slug generation).
            description: Project description.
            paper_type: Type of paper.
            workflow_mode: Workflow mode for the converted project.
            target_journal: Target journal.
            keep_temp: If True, copy instead of move (keep temp project).

        Returns:
            New project info or error.
        """
        temp_path = self.projects_dir / self.TEMP_PROJECT_SLUG

        if not temp_path.exists():
            return {
                "success": False,
                "error": "No temporary exploration project found. Use get_or_create_temp_project first.",
            }

        # Get temp project stats before conversion
        temp_stats = self._get_project_stats(temp_path)

        # Create the new project
        new_slug = self._slugify(name)
        new_path = self.projects_dir / new_slug

        if new_path.exists():
            return {
                "success": False,
                "error": f"Project '{new_slug}' already exists. Choose a different name.",
            }

        # Validate paper_type if provided
        if paper_type and not is_valid_paper_type(paper_type):
            return {
                "success": False,
                "error": f"Invalid paper type '{paper_type}'. Valid types: {list_paper_types()}",
            }

        resolved_workflow_mode = workflow_mode or ("manuscript" if paper_type else "library-wiki")
        if resolved_workflow_mode not in WORKFLOW_MODES:
            return {
                "success": False,
                "error": f"Invalid workflow mode '{resolved_workflow_mode}'. Valid modes: {list(WORKFLOW_MODES)}",
            }

        import shutil

        if keep_temp:
            # Copy everything
            shutil.copytree(temp_path, new_path)
        else:
            # Move (rename)
            shutil.move(str(temp_path), str(new_path))

        # Update the config for the new project
        config = self._create_project_config(
            name=name,
            slug=new_slug,
            description=description
            or f"Converted from exploration workspace with {temp_stats['references']} references",
            authors=None,
            target_journal=target_journal,
            paper_type=paper_type,
            workflow_mode=resolved_workflow_mode,
            interaction_preferences=None,
            memo=f"Originally explored as temp project. Converted on {datetime.now().strftime('%Y-%m-%d')}.",
        )
        self._save_config(new_path, config)

        # Ensure the target workflow layout exists even when the source exploration
        # workspace was created with a different directory shape.
        for subdir in self._directories_for_workflow(resolved_workflow_mode):
            (new_path / subdir).mkdir(exist_ok=True)

        # Update concept.md or library workspace seed
        concept_content = self._build_workspace_seed_document(
            project_name=name,
            paper_type=paper_type,
            target_journal=target_journal,
            memo=f"Converted from exploration workspace.\nReferences: {temp_stats['references']}",
            workflow_mode=resolved_workflow_mode,
        )
        (new_path / "concept.md").write_text(concept_content, encoding="utf-8")

        # Update memory files
        memory_manager = ProjectMemoryManager(new_path)
        memory_manager.create_memory_files(
            project_name=name,
            paper_type=paper_type,
            workflow_mode=resolved_workflow_mode,
            interaction_preferences=None,
            memo=f"Converted from temp exploration project with {temp_stats['references']} references.",
        )

        # Switch to new project
        self._save_current_project(new_slug)

        # Keep Foam project isolation and graph nodes aligned with the converted project.
        self._update_foam_settings(new_slug)
        self._refresh_foam_graph()

        converted_stats = self._get_project_stats(new_path)
        conversion_summary = self._build_conversion_message(resolved_workflow_mode, converted_stats)

        return {
            "success": True,
            "message": f"✅ 成功將探索工作區轉換為正式專案！\n\n"
            f"📁 新專案: **{name}**\n"
            f"📚 轉移內容:\n"
            f"{conversion_summary}",
            "slug": new_slug,
            "path": str(new_path),
            "workflow_mode": resolved_workflow_mode,
            "stats": converted_stats,
            "paths": self.get_project_paths(new_slug),
        }

    def ensure_project_for_references(self) -> Dict[str, Any]:
        """
        Ensure there's a project available for saving references.

        If no project is active, automatically creates/activates the temp project.
        This allows users to explore literature without first creating a formal project.

        Returns:
            Current project info (either existing or newly created temp).
        """
        current = self.get_current_project()

        if current:
            # Project already active
            return self.get_project_info(current)

        # No project active - use temp project
        return self.get_or_create_temp_project()


# Singleton instance for global access
_project_manager: Optional[ProjectManager] = None


def get_project_manager(base_path: str | None = None) -> ProjectManager:
    """Get or create the global ProjectManager instance.

    Args:
        base_path: Base directory. When None (default), delegates to
                   ProjectManager.__init__ which reads MEDPAPER_BASE_DIR
                   env var then falls back to CWD.  Previous default of "."
                   bypassed the env-var check, causing a dual-instance
                   state bug when MEDPAPER_BASE_DIR != CWD (e.g. VSX).
    """
    global _project_manager
    if _project_manager is None:
        _project_manager = ProjectManager(base_path)
    return _project_manager


def _reset_project_manager() -> None:
    """Reset the singleton (for testing only)."""
    global _project_manager
    _project_manager = None
