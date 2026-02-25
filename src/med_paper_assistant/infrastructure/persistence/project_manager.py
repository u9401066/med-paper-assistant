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
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...domain.paper_types import (
    PAPER_TYPES,
    get_paper_type_dict,
    is_valid_paper_type,
    list_paper_types,
)
from ..services.concept_template_reader import ConceptTemplateReader
from .project_memory_manager import ProjectMemoryManager


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
    PROJECT_DIRS = ["drafts", "references", "data", "results", ".memory"]

    # Current project state file
    STATE_FILE = ".current_project"

    # Valid project statuses
    VALID_STATUSES = ["concept", "drafting", "review", "submitted", "published"]

    # Temporary project for exploration
    TEMP_PROJECT_SLUG = "temp-exploration"

    def __init__(self, base_path: str = "."):
        """
        Initialize ProjectManager.

        Args:
            base_path: Base directory for the med-paper-assistant workspace.
        """
        self.base_path = Path(base_path).resolve()
        self.projects_dir = self.base_path / "projects"
        self.state_file = self.base_path / self.STATE_FILE

        # Initialize helpers
        self.template_reader = ConceptTemplateReader()

        # Ensure projects directory exists
        self.projects_dir.mkdir(parents=True, exist_ok=True)

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
            interaction_preferences: User preferences for AI interaction.
            memo: Additional notes and reminders.

        Returns:
            Project info dictionary.
        """
        slug = self._slugify(name)
        project_path = self.projects_dir / slug

        # Validation
        if project_path.exists():
            return {
                "success": False,
                "error": f"Project '{slug}' already exists. Use switch_project to switch to it.",
                "slug": slug,
            }

        if paper_type and not is_valid_paper_type(paper_type):
            return {
                "success": False,
                "error": f"Invalid paper type '{paper_type}'. Valid types: {list_paper_types()}",
            }

        # Create directory structure
        project_path.mkdir(parents=True)
        for subdir in self.PROJECT_DIRS:
            (project_path / subdir).mkdir()

        # Create project config
        project_config = self._create_project_config(
            name,
            slug,
            description,
            authors,
            target_journal,
            paper_type,
            interaction_preferences,
            memo,
        )
        self._save_config(project_path, project_config)

        # Create concept.md
        concept_content = self.template_reader.get_concept_template(
            project_name=name, paper_type=paper_type, target_journal=target_journal, memo=memo
        )
        (project_path / "concept.md").write_text(concept_content, encoding="utf-8")

        # Create memory files
        memory_manager = ProjectMemoryManager(project_path)
        memory_manager.create_memory_files(
            project_name=name,
            paper_type=paper_type,
            interaction_preferences=interaction_preferences,
            memo=memo,
        )

        # Set as current project
        self._save_current_project(slug)

        return {
            "success": True,
            "message": f"Project '{name}' created successfully!",
            "slug": slug,
            "path": str(project_path),
            "structure": {
                "concept": str(project_path / "concept.md"),
                "memory": str(project_path / ".memory"),
                "drafts": str(project_path / "drafts"),
                "references": str(project_path / "references"),
                "data": str(project_path / "data"),
                "results": str(project_path / "results"),
            },
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
        project_path = self.projects_dir / slug

        if not project_path.exists():
            available = self.list_projects()
            return {
                "success": False,
                "error": f"Project '{slug}' not found.",
                "available_projects": [p["slug"] for p in available.get("projects", [])],
            }

        self._save_current_project(slug)

        # Update Foam settings for project isolation
        foam_result = self._update_foam_settings(slug)

        project_info = self.get_project_info(slug)

        # Add Foam update info
        if foam_result.get("success"):
            project_info["foam_isolation"] = {
                "enabled": True,
                "ignored_projects": foam_result.get("ignored_projects", []),
            }

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
            import logging

            logging.getLogger(__name__).warning(f"Foam settings update failed: {e}")
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

        project_path = self.projects_dir / slug

        if not project_path.exists():
            return {"success": False, "error": f"Project '{slug}' not found"}

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

        project_path = self.projects_dir / slug
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

        project_path = self.projects_dir / slug

        return {
            "root": str(project_path),
            "concept": str(project_path / "concept.md"),
            "memory": str(project_path / ".memory"),
            "drafts": str(project_path / "drafts"),
            "references": str(project_path / "references"),
            "data": str(project_path / "data"),
            "results": str(project_path / "results"),
            "config": str(project_path / "project.json"),
        }

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

        project_path = self.projects_dir / slug
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

        project_path = self.projects_dir / slug
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
        if interaction_preferences is not None or memo is not None:
            memory_manager = ProjectMemoryManager(project_path)
            memory_manager.update_preferences(
                config.get("interaction_preferences", {}), config.get("memo", "")
            )

        return {
            "success": True,
            "message": "Project settings updated successfully",
            "slug": slug,
            "updated_fields": updated_fields,
        }

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
            "interaction_preferences": interaction_preferences or {},
            "memo": memo,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "concept",
        }

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

        project_path = self.projects_dir / slug
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
            return None

    def _get_project_stats(self, project_path: Path) -> Dict[str, int]:
        """Get project content statistics."""
        return {
            "drafts": len(list((project_path / "drafts").glob("*.md"))),
            "references": len([d for d in (project_path / "references").iterdir() if d.is_dir()])
            if (project_path / "references").exists()
            else 0,
            "data_files": len(list((project_path / "data").glob("*.*")))
            if (project_path / "data").exists()
            else 0,
        }

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
        for subdir in self.PROJECT_DIRS:
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
            "interaction_preferences": {},
            "memo": "這是一個暫存專案，用於文獻探索。使用 convert_temp_to_project 可將內容轉移到正式專案。",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "exploration",
            "is_temp": True,
        }
        self._save_config(temp_path, config)

        # Create simple concept.md
        concept_content = """# Literature Exploration Workspace

這是一個臨時探索空間，用於：
- 🔍 搜尋和保存有興趣的文獻
- 📝 記錄初步想法和筆記
- 💡 尋找研究靈感

## Saved References

使用 `save_reference` 保存的文獻會存在這裡。

## Notes

（在這裡記錄你的想法）

---

**當你找到研究方向後**，使用 `convert_temp_to_project` 將這些內容轉移到正式專案！
"""
        (temp_path / "concept.md").write_text(concept_content, encoding="utf-8")

        # Set as current project
        self._save_current_project(self.TEMP_PROJECT_SLUG)

        return {
            "success": True,
            "slug": self.TEMP_PROJECT_SLUG,
            "is_temp": True,
            "message": "✅ 已建立文獻探索工作區！\n\n現在可以自由搜尋和保存文獻。找到研究方向後，使用 convert_temp_to_project 將內容轉移到正式專案。",
            "paths": self.get_project_paths(self.TEMP_PROJECT_SLUG),
            "stats": {"drafts": 0, "references": 0, "data_files": 0},
        }

    def is_temp_project_active(self) -> bool:
        """Check if the temp project is currently active."""
        return self.get_current_project() == self.TEMP_PROJECT_SLUG

    def convert_temp_to_project(
        self,
        name: str,
        description: str = "",
        paper_type: str = "",
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
            interaction_preferences=None,
            memo=f"Originally explored as temp project. Converted on {datetime.now().strftime('%Y-%m-%d')}.",
        )
        self._save_config(new_path, config)

        # Update concept.md
        concept_content = self.template_reader.get_concept_template(
            project_name=name,
            paper_type=paper_type,
            target_journal=target_journal,
            memo=f"Converted from exploration workspace.\nReferences: {temp_stats['references']}",
        )
        (new_path / "concept.md").write_text(concept_content, encoding="utf-8")

        # Update memory files
        memory_manager = ProjectMemoryManager(new_path)
        memory_manager.create_memory_files(
            project_name=name,
            paper_type=paper_type,
            interaction_preferences=None,
            memo=f"Converted from temp exploration project with {temp_stats['references']} references.",
        )

        # Switch to new project
        self._save_current_project(new_slug)

        return {
            "success": True,
            "message": f"✅ 成功將探索工作區轉換為正式專案！\n\n"
            f"📁 新專案: **{name}**\n"
            f"📚 轉移內容:\n"
            f"   - References: {temp_stats['references']}\n"
            f"   - Drafts: {temp_stats['drafts']}\n"
            f"   - Data files: {temp_stats['data_files']}",
            "slug": new_slug,
            "path": str(new_path),
            "stats": temp_stats,
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


def get_project_manager(base_path: str = ".") -> ProjectManager:
    """Get or create the global ProjectManager instance."""
    global _project_manager
    if _project_manager is None:
        _project_manager = ProjectManager(base_path)
    return _project_manager
