"""
Project Entity - Represents a research paper project.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum

from med_paper_assistant.shared.constants import PAPER_TYPES, PROJECT_DIRECTORIES


class ProjectStatus(Enum):
    """Project lifecycle status."""
    CONCEPT = "concept"
    DRAFTING = "drafting"
    REVIEW = "review"
    SUBMITTED = "submitted"
    PUBLISHED = "published"


@dataclass
class Project:
    """
    Research paper project entity.
    
    A project is an isolated workspace containing all materials
    for a single research paper.
    """
    name: str
    slug: str
    path: Path
    
    # Metadata
    description: str = ""
    authors: List[str] = field(default_factory=list)
    target_journal: str = ""
    paper_type: str = ""
    
    # Status tracking
    status: str = "concept"  # concept → drafting → review → submitted → published
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # User preferences
    interaction_preferences: Dict[str, Any] = field(default_factory=dict)
    memo: str = ""
    
    @property
    def paper_type_info(self) -> Dict[str, Any]:
        """Get paper type configuration."""
        return PAPER_TYPES.get(self.paper_type, {})
    
    @property
    def sections(self) -> List[str]:
        """Get expected sections for this paper type."""
        return self.paper_type_info.get("sections", [])
    
    @property
    def drafts_dir(self) -> Path:
        return self.path / "drafts"
    
    @property
    def references_dir(self) -> Path:
        return self.path / "references"
    
    @property
    def data_dir(self) -> Path:
        return self.path / "data"
    
    @property
    def results_dir(self) -> Path:
        return self.path / "results"
    
    @property
    def memory_dir(self) -> Path:
        return self.path / ".memory"
    
    @property
    def concept_file(self) -> Path:
        return self.path / "concept.md"
    
    @property
    def config_file(self) -> Path:
        return self.path / "project.json"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "authors": self.authors,
            "target_journal": self.target_journal,
            "paper_type": self.paper_type,
            "paper_type_info": self.paper_type_info,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "interaction_preferences": self.interaction_preferences,
            "memo": self.memo,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], path: Path) -> "Project":
        """Create from dictionary."""
        return cls(
            name=data.get("name", ""),
            slug=data.get("slug", ""),
            path=path,
            description=data.get("description", ""),
            authors=data.get("authors", []),
            target_journal=data.get("target_journal", ""),
            paper_type=data.get("paper_type", ""),
            status=data.get("status", "concept"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            interaction_preferences=data.get("interaction_preferences", {}),
            memo=data.get("memo", ""),
        )
    
    @staticmethod
    def generate_slug(name: str) -> str:
        """Generate URL-safe slug from project name."""
        import re
        slug = name.lower().strip()
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')
        return slug or "untitled"
