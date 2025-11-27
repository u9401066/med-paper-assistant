"""
Application Configuration.

Centralized configuration for the entire application.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent.parent


@dataclass
class AppConfig:
    """
    Application configuration.
    
    Can be loaded from environment variables or defaults.
    """
    # Base paths
    base_dir: Path = field(default_factory=lambda: Path.cwd())
    projects_dir: Path = field(default_factory=lambda: Path.cwd() / "projects")
    templates_dir: Path = field(default_factory=lambda: Path.cwd() / "templates")
    
    # PubMed API
    entrez_email: str = "medpaper@example.com"
    entrez_api_key: Optional[str] = None
    entrez_tool: str = "MedPaperAssistant"
    
    # Defaults
    default_citation_style: str = "vancouver"
    
    # Word limits
    word_limits: dict = field(default_factory=lambda: {
        "Abstract": 250,
        "Introduction": 800,
        "Methods": 1500,
        "Results": 1500,
        "Discussion": 1500,
        "Conclusions": 300,
    })
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create configuration from environment variables."""
        return cls(
            base_dir=Path(os.getenv("MEDPAPER_BASE_DIR", Path.cwd())),
            projects_dir=Path(os.getenv("MEDPAPER_PROJECTS_DIR", Path.cwd() / "projects")),
            templates_dir=Path(os.getenv("MEDPAPER_TEMPLATES_DIR", Path.cwd() / "templates")),
            entrez_email=os.getenv("ENTREZ_EMAIL", "medpaper@example.com"),
            entrez_api_key=os.getenv("ENTREZ_API_KEY"),
        )
    
    def ensure_directories(self):
        """Ensure required directories exist."""
        self.projects_dir.mkdir(parents=True, exist_ok=True)


# Backward compatibility alias
Config = AppConfig


# Global config instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = AppConfig.from_env()
    return _config


def set_config(config: AppConfig):
    """Set the global configuration instance."""
    global _config
    _config = config

