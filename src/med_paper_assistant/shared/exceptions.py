"""
Custom exceptions for the application.
"""


class MedPaperError(Exception):
    """Base exception for all MedPaper errors."""
    pass


# Domain Errors
class DomainError(MedPaperError):
    """Base exception for domain layer errors."""
    pass


class ProjectNotFoundError(DomainError):
    """Raised when a project is not found."""
    pass


class ProjectAlreadyExistsError(DomainError):
    """Raised when trying to create a project that already exists."""
    pass


class ReferenceNotFoundError(DomainError):
    """Raised when a reference is not found."""
    pass


class InvalidPaperTypeError(DomainError):
    """Raised when an invalid paper type is specified."""
    pass


# Backward compatibility aliases
ProjectError = ProjectNotFoundError
ReferenceError = ReferenceNotFoundError
DraftError = DomainError
SearchError = DomainError


# Infrastructure Errors
class InfrastructureError(MedPaperError):
    """Base exception for infrastructure layer errors."""
    pass


class PubMedAPIError(InfrastructureError):
    """Raised when PubMed API call fails."""
    pass


class FileStorageError(InfrastructureError):
    """Raised when file storage operations fail."""
    pass


class PDFDownloadError(InfrastructureError):
    """Raised when PDF download fails."""
    pass


# Application Errors
class ApplicationError(MedPaperError):
    """Base exception for application layer errors."""
    pass


class ValidationError(ApplicationError):
    """Raised when validation fails."""
    pass


class ExportError(ApplicationError):
    """Raised when document export fails."""
    pass
