"""
Domain Layer - Core business logic and entities.

This layer contains:
- entities/: Core domain entities (Project, Reference, Draft)
- value_objects/: Immutable value objects (Citation, SearchCriteria)
- services/: Domain services for complex business logic
- paper_types.py: Paper type definitions and utilities
"""

from .entities import Draft, Project, Reference
from .paper_types import (
    PAPER_TYPES,
    PaperTypeInfo,
    get_paper_type,
    get_paper_type_dict,
    is_valid_paper_type,
    list_paper_types,
)
from .value_objects import Author, CitationStyle, SearchCriteria, generate_author_block

__all__ = [
    # Entities
    "Draft",
    "Project",
    "Reference",
    # Paper types
    "PAPER_TYPES",
    "PaperTypeInfo",
    "get_paper_type",
    "get_paper_type_dict",
    "is_valid_paper_type",
    "list_paper_types",
    # Value objects
    "Author",
    "generate_author_block",
    "CitationStyle",
    "SearchCriteria",
]
