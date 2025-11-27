"""
MedPaper Assistant - Medical Paper Writing Assistant

A comprehensive tool for medical research paper writing, providing:
- Literature search and reference management
- Draft creation and editing
- Data analysis and visualization
- Word document export with templates

Architecture (DDD):
    domain/         - Core business logic and entities
    application/    - Use cases and application services
    infrastructure/ - External services and persistence
    interfaces/     - MCP server and other interfaces
    shared/         - Shared constants and utilities
    core/           - Legacy modules (being migrated)
    mcp_server/     - Legacy MCP server (being migrated)
"""

__version__ = "0.1.0"

# Domain exports
from med_paper_assistant.domain.entities import Project, Reference, Draft
from med_paper_assistant.domain.value_objects import CitationStyle, CitationFormat

# Application exports
from med_paper_assistant.application import (
    CreateProjectUseCase,
    SearchLiteratureUseCase,
    SaveReferenceUseCase,
)

# Infrastructure exports
from med_paper_assistant.infrastructure import (
    AppConfig,
    ProjectRepository,
    ReferenceRepository,
    PubMedClient,
)

# Interface exports
from med_paper_assistant.interfaces.mcp import create_server, run_server

__all__ = [
    # Version
    "__version__",
    # Domain
    "Project",
    "Reference",
    "Draft",
    "CitationStyle",
    "CitationFormat",
    # Application
    "CreateProjectUseCase",
    "SearchLiteratureUseCase",
    "SaveReferenceUseCase",
    # Infrastructure
    "AppConfig",
    "ProjectRepository",
    "ReferenceRepository",
    "PubMedClient",
    # Interface
    "create_server",
    "run_server",
]
