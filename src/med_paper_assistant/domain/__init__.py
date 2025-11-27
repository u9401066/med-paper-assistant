"""
Domain Layer - Core business logic and entities.

This layer contains:
- entities/: Core domain entities (Project, Reference, Draft)
- value_objects/: Immutable value objects (Citation, SearchCriteria)
- services/: Domain services for complex business logic
"""

from .entities import Project, Reference, Draft
from .value_objects import CitationStyle, SearchCriteria
