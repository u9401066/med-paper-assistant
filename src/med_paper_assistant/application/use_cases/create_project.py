"""Create Project Use Case."""

from dataclasses import dataclass
from datetime import datetime

from med_paper_assistant.domain.entities.project import Project, ProjectStatus
from med_paper_assistant.infrastructure.persistence import ProjectRepository
from med_paper_assistant.shared.constants import DEFAULT_WORKFLOW_MODE
from med_paper_assistant.shared.path_guard import resolve_child_path


@dataclass
class CreateProjectInput:
    """Input data for creating a project."""

    name: str
    description: str = ""
    paper_type: str = ""
    workflow_mode: str = DEFAULT_WORKFLOW_MODE
    target_journal: str = ""
    memo: str = ""


@dataclass
class CreateProjectOutput:
    """Output data after creating a project."""

    slug: str
    name: str
    path: str
    message: str


class CreateProjectUseCase:
    """
    Use case for creating a new research paper project.

    This use case:
    1. Generates a slug from the project name
    2. Creates the project directory structure
    3. Initializes concept.md and memory files
    4. Sets the project as current
    """

    def __init__(self, repository: ProjectRepository):
        self.repository = repository

    def execute(self, input_data: CreateProjectInput) -> CreateProjectOutput:
        """
        Execute the create project use case.

        Args:
            input_data: Input data containing project details.

        Returns:
            CreateProjectOutput with project details.

        Raises:
            ProjectAlreadyExistsError: If project slug already exists.
        """
        # Build a project entity, but delegate creation semantics to the
        # repository's runtime lifecycle owner.
        slug = Project.generate_slug(input_data.name)

        # Create project entity
        project = Project(
            slug=slug,
            name=input_data.name,
            description=input_data.description,
            paper_type=input_data.paper_type,
            workflow_mode=input_data.workflow_mode,
            target_journal=input_data.target_journal,
            status=ProjectStatus.CONCEPT.value,  # Use .value to get string
            memo=input_data.memo,
            path=resolve_child_path(self.repository.projects_dir, slug, field_name="project slug"),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Persist
        created = self.repository.create(project)

        return CreateProjectOutput(
            slug=created.slug,
            name=created.name,
            path=str(created.path),
            message=f"Project '{created.name}' created successfully.",
        )
