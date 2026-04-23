"""
Shared module - Common utilities, constants, and exceptions.
"""

from .constants import (
    CITATION_STYLES,
    DEFAULT_WORD_LIMITS,
    PAPER_TYPES,
    PROJECT_DIRECTORIES,
)
from .exceptions import (
    ApplicationError,
    DomainError,
    DraftError,
    ExportError,
    FileStorageError,
    InfrastructureError,
    InvalidPaperTypeError,
    MedPaperError,
    PDFDownloadError,
    ProjectAlreadyExistsError,
    ProjectError,
    ProjectNotFoundError,
    PubMedAPIError,
    ReferenceError,
    ReferenceNotFoundError,
    SearchError,
    ValidationError,
)
from .path_guard import PathGuardError, normalize_relative_filename, resolve_child_path

__all__ = [
    # Constants
    "CITATION_STYLES",
    "DEFAULT_WORD_LIMITS",
    "PAPER_TYPES",
    "PROJECT_DIRECTORIES",
    # Exceptions
    "ApplicationError",
    "DomainError",
    "DraftError",
    "ExportError",
    "FileStorageError",
    "InfrastructureError",
    "InvalidPaperTypeError",
    "MedPaperError",
    "PDFDownloadError",
    "ProjectAlreadyExistsError",
    "ProjectError",
    "ProjectNotFoundError",
    "PubMedAPIError",
    "ReferenceError",
    "ReferenceNotFoundError",
    "SearchError",
    "ValidationError",
    "PathGuardError",
    "normalize_relative_filename",
    "resolve_child_path",
]
