"""Dependency binding shared by the project tool handlers."""

from med_paper_assistant.infrastructure.persistence import ProjectManager

from .._binding import DepsBinding

PROJECT_MANAGER: DepsBinding[ProjectManager] = DepsBinding("project_manager")
