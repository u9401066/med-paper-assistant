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
    FileStorage,
    ProjectManager,
    ProjectRepository,
    ReferenceManager,
    ReferenceRepository,
    get_project_manager,
)

# Note: PubMedClient removed - use pubmed-search MCP instead
from .services import (
    JOURNAL_CITATION_CONFIGS,
    SECTION_PROMPTS,
    Analyzer,
    CitationStyle,
    Drafter,
    Formatter,
    TemplateReader,
    WordExporter,
    WordWriter,
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
    # Services
    "Analyzer",
    "Drafter",
    "CitationStyle",
    "JOURNAL_CITATION_CONFIGS",
    "Formatter",
    "TemplateReader",
    "WordWriter",
    "SECTION_PROMPTS",
    "WordExporter",
]
