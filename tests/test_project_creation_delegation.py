from datetime import datetime

from med_paper_assistant.application.use_cases.create_project import (
    CreateProjectInput,
    CreateProjectUseCase,
)
from med_paper_assistant.domain.entities.project import Project
from med_paper_assistant.infrastructure.persistence.project_manager import ProjectManager
from med_paper_assistant.infrastructure.persistence.project_repository import ProjectRepository


def test_project_repository_create_delegates_to_project_manager(tmp_path, monkeypatch):
    calls = []
    original_create_project = ProjectManager.create_project

    def recording_create_project(self, *args, **kwargs):
        calls.append(kwargs.copy())
        return original_create_project(self, *args, **kwargs)

    monkeypatch.setattr(ProjectManager, "create_project", recording_create_project)

    repository = ProjectRepository(tmp_path / "projects")
    project = Project(
        name="Delegated Project",
        slug="delegated-project",
        path=tmp_path / "projects" / "delegated-project",
        description="delegation check",
        paper_type="original-research",
        workflow_mode="manuscript",
        status="concept",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        memo="keep repository thin",
    )

    created = repository.create(project)

    assert len(calls) == 1
    assert calls[0]["name"] == "Delegated Project"
    assert calls[0]["description"] == "delegation check"
    assert calls[0]["paper_type"] == "original-research"
    assert calls[0]["workflow_mode"] == "manuscript"
    assert created.slug == "delegated-project"
    assert created.path == tmp_path / "projects" / "delegated-project"
    assert (created.path / "drafts").is_dir()


def test_create_project_use_case_delegates_through_repository(tmp_path, monkeypatch):
    calls = []
    original_create_project = ProjectManager.create_project

    def recording_create_project(self, *args, **kwargs):
        calls.append(kwargs.copy())
        return original_create_project(self, *args, **kwargs)

    monkeypatch.setattr(ProjectManager, "create_project", recording_create_project)

    repository = ProjectRepository(tmp_path / "projects")
    use_case = CreateProjectUseCase(repository)

    output = use_case.execute(
        CreateProjectInput(
            name="Use Case Project",
            description="delegated through repository",
            paper_type="original-research",
            workflow_mode="library-wiki",
            memo="check lifecycle owner",
        )
    )

    assert len(calls) == 1
    assert calls[0]["name"] == "Use Case Project"
    assert calls[0]["workflow_mode"] == "library-wiki"
    assert output.slug == "use-case-project"
    assert output.path == str(tmp_path / "projects" / "use-case-project")
    assert (tmp_path / "projects" / "use-case-project" / "inbox").is_dir()


def test_create_project_use_case_deduplicates_duplicate_names(tmp_path):
    repository = ProjectRepository(tmp_path / "projects")
    use_case = CreateProjectUseCase(repository)

    first = use_case.execute(CreateProjectInput(name="Repeated Project"))
    second = use_case.execute(CreateProjectInput(name="Repeated Project"))

    assert first.slug == "repeated-project"
    assert second.slug == "repeated-project-1"
    assert (tmp_path / "projects" / "repeated-project-1").is_dir()


def test_project_repository_set_current_uses_lightweight_state_update(tmp_path, monkeypatch):
    calls = []

    def record_set_current(self, slug, refresh_foam=False):
        calls.append({"slug": slug, "refresh_foam": refresh_foam})
        return {"success": True, "slug": slug}

    monkeypatch.setattr(ProjectManager, "set_current_project", record_set_current)

    repository = ProjectRepository(tmp_path / "projects")
    repository.set_current("alpha")

    assert calls == [{"slug": "alpha", "refresh_foam": False}]
