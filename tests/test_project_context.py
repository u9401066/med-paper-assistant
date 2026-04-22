from med_paper_assistant.interfaces.mcp.tools._shared import project_context


def test_validate_project_for_workflow_accepts_matching_mode(monkeypatch):
    monkeypatch.setattr(
        project_context,
        "validate_project_for_tool",
        lambda project=None: (True, ""),
    )
    monkeypatch.setattr(
        project_context,
        "ensure_project_context",
        lambda project=None: (True, "ok", {"workflow_mode": "manuscript"}),
    )

    is_valid, error_msg = project_context.validate_project_for_workflow(
        required_mode="manuscript"
    )

    assert is_valid is True
    assert error_msg == ""


def test_validate_project_for_workflow_rejects_mismatched_mode(monkeypatch):
    monkeypatch.setattr(
        project_context,
        "validate_project_for_tool",
        lambda project=None: (True, ""),
    )
    monkeypatch.setattr(
        project_context,
        "ensure_project_context",
        lambda project=None: (True, "ok", {"workflow_mode": "library-wiki"}),
    )

    is_valid, error_msg = project_context.validate_project_for_workflow(
        required_mode="manuscript"
    )

    assert is_valid is False
    assert "Current workflow: Library Wiki Path" in error_msg
    assert "workflow_mode=\"manuscript\"" in error_msg