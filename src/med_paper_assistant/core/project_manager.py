"""
Project Manager - Multi-project support for MedPaper Assistant

Manages separate workspaces for different research papers, each with its own:
- concept.md
- drafts/
- references/
- data/
- results/
"""

import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime


class ProjectManager:
    """
    Manages multiple research paper projects with isolated directory structures.
    
    Each project has:
    - project.json: metadata and settings
    - concept.md: research concept
    - drafts/: paper drafts
    - references/: saved references (by PMID)
    - data/: analysis data files
    - results/: exported documents
    """
    
    # Subdirectories for each project
    PROJECT_DIRS = ["drafts", "references", "data", "results"]
    
    # Current project state file
    STATE_FILE = ".current_project"
    
    def __init__(self, base_path: str = "."):
        """
        Initialize ProjectManager.
        
        Args:
            base_path: Base directory for the med-paper-assistant workspace.
        """
        self.base_path = Path(base_path).resolve()
        self.projects_dir = self.base_path / "projects"
        self.state_file = self.base_path / self.STATE_FILE
        
        # Ensure projects directory exists (create parent dirs if needed)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        
    def _slugify(self, name: str) -> str:
        """Convert project name to URL-safe slug."""
        import re
        # Convert to lowercase, replace spaces/underscores with hyphens
        slug = name.lower().strip()
        slug = re.sub(r'[\s_]+', '-', slug)
        # Remove non-alphanumeric characters except hyphens
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        # Remove multiple consecutive hyphens
        slug = re.sub(r'-+', '-', slug)
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        return slug or "untitled"
    
    def create_project(
        self, 
        name: str, 
        description: str = "",
        authors: Optional[List[str]] = None,
        target_journal: str = ""
    ) -> Dict[str, Any]:
        """
        Create a new research paper project.
        
        Args:
            name: Human-readable project name.
            description: Brief description of the research.
            authors: List of author names.
            target_journal: Target journal for submission.
            
        Returns:
            Project info dictionary.
        """
        slug = self._slugify(name)
        project_path = self.projects_dir / slug
        
        if project_path.exists():
            return {
                "success": False,
                "error": f"Project '{slug}' already exists. Use switch_project to switch to it.",
                "slug": slug
            }
        
        # Create project directory structure
        project_path.mkdir(parents=True)
        for subdir in self.PROJECT_DIRS:
            (project_path / subdir).mkdir()
        
        # Create project.json
        project_config = {
            "name": name,
            "slug": slug,
            "description": description,
            "authors": authors or [],
            "target_journal": target_journal,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "concept"  # concept → drafting → review → submitted
        }
        
        config_path = project_path / "project.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(project_config, f, indent=2, ensure_ascii=False)
        
        # Create empty concept.md with template
        concept_template = self._get_concept_template(name)
        concept_path = project_path / "concept.md"
        with open(concept_path, 'w', encoding='utf-8') as f:
            f.write(concept_template)
        
        # Set as current project
        self._save_current_project(slug)
        
        return {
            "success": True,
            "message": f"Project '{name}' created successfully!",
            "slug": slug,
            "path": str(project_path),
            "structure": {
                "concept": str(concept_path),
                "drafts": str(project_path / "drafts"),
                "references": str(project_path / "references"),
                "data": str(project_path / "data"),
                "results": str(project_path / "results")
            }
        }
    
    def _get_concept_template(self, project_name: str) -> str:
        """Get concept template with project name filled in."""
        return f"""# Research Concept: {project_name}

## 🔒 NOVELTY STATEMENT
<!-- Protected: Agent must ask before modifying -->

[Define the unique contribution of this research]

## 🔒 KEY SELLING POINTS
<!-- Protected: User-defined, Agent must preserve -->

1. 
2. 
3. 

## 📝 Background

[Research background and context]

## 📝 Research Gap

[Gap identified from literature review]

**Literature Evidence:**
- 

## 📝 Research Question / Hypothesis

[Primary research question]

## 📝 Methods Overview

[Brief methods description]

## 📝 Expected Outcomes

[Expected results and impact]

## 📝 Target Journal

[Target journal and rationale]

---
*Created: {datetime.now().strftime('%Y-%m-%d')}*
"""
    
    def switch_project(self, slug: str) -> Dict[str, Any]:
        """
        Switch to an existing project.
        
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
                "available_projects": [p["slug"] for p in available.get("projects", [])]
            }
        
        self._save_current_project(slug)
        
        return self.get_project_info(slug)
    
    def get_current_project(self) -> Optional[str]:
        """
        Get the slug of the currently active project.
        
        Returns:
            Current project slug or None if not set.
        """
        if not self.state_file.exists():
            return None
        
        try:
            with open(self.state_file, 'r') as f:
                return f.read().strip() or None
        except Exception:
            return None
    
    def _save_current_project(self, slug: str) -> None:
        """Save current project to state file."""
        with open(self.state_file, 'w') as f:
            f.write(slug)
    
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
                    "error": "No project selected. Use create_project or switch_project first."
                }
        
        project_path = self.projects_dir / slug
        config_path = project_path / "project.json"
        
        if not config_path.exists():
            return {
                "success": False,
                "error": f"Project '{slug}' not found or corrupted."
            }
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Count contents
        drafts_count = len(list((project_path / "drafts").glob("*.md")))
        refs_count = len([d for d in (project_path / "references").iterdir() if d.is_dir()])
        data_count = len(list((project_path / "data").glob("*.*")))
        
        return {
            "success": True,
            "slug": slug,
            "is_current": slug == self.get_current_project(),
            **config,
            "paths": self.get_project_paths(slug),
            "stats": {
                "drafts": drafts_count,
                "references": refs_count,
                "data_files": data_count
            }
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
            "drafts": str(project_path / "drafts"),
            "references": str(project_path / "references"),
            "data": str(project_path / "data"),
            "results": str(project_path / "results"),
            "config": str(project_path / "project.json")
        }
    
    def list_projects(self) -> Dict[str, Any]:
        """
        List all projects.
        
        Returns:
            Dictionary with list of projects and current project.
        """
        projects = []
        current = self.get_current_project()
        
        if not self.projects_dir.exists():
            return {"projects": [], "current": None}
        
        for project_dir in sorted(self.projects_dir.iterdir()):
            if not project_dir.is_dir():
                continue
            
            config_path = project_dir / "project.json"
            if not config_path.exists():
                continue
            
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                projects.append({
                    "slug": project_dir.name,
                    "name": config.get("name", project_dir.name),
                    "status": config.get("status", "unknown"),
                    "created_at": config.get("created_at", ""),
                    "is_current": project_dir.name == current
                })
            except Exception:
                projects.append({
                    "slug": project_dir.name,
                    "name": project_dir.name,
                    "status": "error",
                    "is_current": project_dir.name == current
                })
        
        return {
            "projects": projects,
            "current": current,
            "count": len(projects)
        }
    
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
        
        config_path = self.projects_dir / slug / "project.json"
        
        if not config_path.exists():
            return {"success": False, "error": f"Project '{slug}' not found"}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        valid_statuses = ["concept", "drafting", "review", "submitted", "published"]
        if status not in valid_statuses:
            return {
                "success": False,
                "error": f"Invalid status. Must be one of: {valid_statuses}"
            }
        
        config["status"] = status
        config["updated_at"] = datetime.now().isoformat()
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return {
            "success": True,
            "message": f"Project status updated to '{status}'",
            "slug": slug
        }
    
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
                "error": "Deletion requires confirm=True. This will permanently delete all project data!"
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
        
        return {
            "success": True,
            "message": f"Project '{slug}' deleted permanently."
        }


# Singleton instance for global access
_project_manager: Optional[ProjectManager] = None


def get_project_manager(base_path: str = ".") -> ProjectManager:
    """Get or create the global ProjectManager instance."""
    global _project_manager
    if _project_manager is None:
        _project_manager = ProjectManager(base_path)
    return _project_manager
