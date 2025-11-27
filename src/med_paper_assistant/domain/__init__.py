"""
Domain Layer - Core business logic and entities.

This layer contains:
- entities/: Core domain entities (Project, Reference, Draft)
- value_objects/: Immutable value objects (Citation, SearchCriteria)
- services/: Domain services for complex business logic
- paper_types.py: Paper type definitions and utilities
"""

from .entities import Project, Reference, Draft
from .value_objects import CitationStyle, SearchCriteria
from .paper_types import (
    PAPER_TYPES,
    PaperTypeInfo,
    get_paper_type,
    get_paper_type_dict,
    is_valid_paper_type,
    list_paper_types
)
