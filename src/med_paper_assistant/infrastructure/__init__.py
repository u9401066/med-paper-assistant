"""
Infrastructure Layer - External services, persistence, and technical concerns.

This layer contains:
- persistence/: Data storage and retrieval
- external/: External service integrations (PubMed, etc.)
- config.py: Application configuration
- logging.py: Logging setup
"""

from .config import AppConfig, get_project_root
from .logging import setup_logger
from .persistence import ProjectRepository, ReferenceRepository, FileStorage
from .external import PubMedClient

__all__ = [
    "AppConfig",
    "get_project_root",
    "setup_logger",
    "ProjectRepository",
    "ReferenceRepository",
    "FileStorage",
    "PubMedClient",
]
