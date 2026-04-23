from med_paper_assistant.interfaces.mcp.tools._shared import project_context


def test_validate_project_for_workflow_accepts_matching_mode(monkeypatch):
    monkeypatch.setattr(
        project_context,
        "resolve_project_context",
        lambda project=None, required_mode=None, project_manager=None: (
            {"workflow_mode": "manuscript"},
            None,
        ),
    )

    is_valid, error_msg = project_context.validate_project_for_workflow(
        required_mode="manuscript"
    )

    assert is_valid is True
    assert error_msg == ""


def test_validate_project_for_workflow_rejects_mismatched_mode(monkeypatch):
    monkeypatch.setattr(
        project_context,
        "resolve_project_context",
        lambda project=None, required_mode=None, project_manager=None: (
            None,
            project_context._format_workflow_mode_error("library-wiki", "manuscript"),
        ),
    )

    is_valid, error_msg = project_context.validate_project_for_workflow(
        required_mode="manuscript"
    )

    assert is_valid is False
    assert "Current workflow: Library Wiki Path" in error_msg
    assert "workflow_mode=\"manuscript\"" in error_msg


def test_resolve_project_context_calls_ensure_once(monkeypatch):
    calls = []

    def fake_ensure(project=None):
        calls.append(project)
        return True, "ok", {"slug": "paper", "workflow_mode": "manuscript"}

    monkeypatch.setattr(project_context, "ensure_project_context", fake_ensure)

    project_info, error_msg = project_context.resolve_project_context(
        required_mode="manuscript"
    )

    assert error_msg is None
    assert project_info == {"slug": "paper", "workflow_mode": "manuscript"}
    assert calls == [None]


def test_resolve_project_context_with_project_manager_switches_and_checks_mode():
    class FakeProjectManager:
        def __init__(self):
            self.current = "alpha"
            self.switched = []

        def get_current_project(self):
            return self.current

        def list_projects(self):
            return {"projects": [{"slug": "alpha"}, {"slug": "beta"}]}

        def switch_project(self, slug):
            self.current = slug
            self.switched.append(slug)
            return {"success": True}

        def get_project_info(self, slug):
            return {
                "success": True,
                "slug": slug,
                "workflow_mode": "library-wiki",
            }

    pm = FakeProjectManager()

    project_info, error_msg = project_context.resolve_project_context(
        "beta",
        required_mode="manuscript",
        project_manager=pm,
    )

    assert project_info is None
    assert error_msg == project_context._format_workflow_mode_error(
        "library-wiki",
        "manuscript",
    )
    assert pm.switched == ["beta"]


def test_resolve_project_context_with_project_manager_without_success_key():
    class FakeProjectManager:
        def __init__(self):
            self.current = "alpha"

        def get_current_project(self):
            return self.current

        def list_projects(self):
            return {"projects": [{"slug": "alpha"}]}

        def get_project_info(self, slug):
            return {"slug": slug, "workflow_mode": "manuscript"}

    pm = FakeProjectManager()

    project_info, error_msg = project_context.resolve_project_context(
        required_mode="manuscript",
        project_manager=pm,
    )

    assert error_msg is None
    assert project_info["slug"] == "alpha"