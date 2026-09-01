import pytest

from med_paper_assistant.infrastructure.services.formatter import Formatter
from med_paper_assistant.shared.path_guard import PathGuardError


def test_formatter_rejects_unsafe_relative_template_path(tmp_path):
    draft_path = tmp_path / "draft.md"
    draft_path.write_text("# Title\nContent.", encoding="utf-8")

    formatter = Formatter()
    formatter.templates_dir = str(tmp_path)

    with pytest.raises(PathGuardError):
        formatter.apply_template(
            str(draft_path),
            "../custom_template.docx",
            str(tmp_path / "output.docx"),
        )
