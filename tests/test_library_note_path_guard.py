from __future__ import annotations

import pytest

from med_paper_assistant.interfaces.mcp.tools.project.library_notes import _resolve_note_path
from med_paper_assistant.shared.path_guard import PathGuardError


def test_library_note_path_rejects_case_insensitive_collision(tmp_path):
    (tmp_path / "Note.md").write_text("existing", encoding="utf-8")

    with pytest.raises(PathGuardError):
        _resolve_note_path(tmp_path, "note.md")
