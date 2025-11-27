"""
Infrastructure Layer - External services, persistence, and technical concerns.

This layer contains:
- persistence/: Data storage and retrieval
- services/: Business logic implementations
- external/: External service integrations (PubMed, etc.)
- config.py: Application configuration
- logging.py: Logging setup
"""

from .config import AppConfig, get_project_root
from .logging import setup_logger
from .persistence import (
    ProjectRepository,
    ReferenceRepository,
    FileStorage,
    ReferenceManager,
    ProjectManager,
    get_project_manager,
)
from .external import PubMedClient
from .services import (
    Analyzer,
    Drafter,
    CitationStyle,
    JOURNAL_CITATION_CONFIGS,
    Formatter,
    TemplateReader,
    WordWriter,
    StrategyManager,
    SECTION_PROMPTS,
    WordExporter,
)

__all__ = [
    # Config
    "AppConfig",
    "get_project_root",
    "setup_logger",
    # Persistence
    "ProjectRepository",
    "ReferenceRepository",
    "FileStorage",
    "ReferenceManager",
    "ProjectManager",
    "get_project_manager",
    # External
    "PubMedClient",
    # Services
    "Analyzer",
    "Drafter",
    "CitationStyle",
    "JOURNAL_CITATION_CONFIGS",
    "Formatter",
    "TemplateReader",
    "WordWriter",
    "StrategyManager",
    "SECTION_PROMPTS",
    "WordExporter",
]
