from __future__ import annotations

from pathlib import Path

import pytest

from med_paper_assistant.shared.path_guard import (
    PathGuardError,
    normalize_relative_filename,
    resolve_child_directory,
    resolve_child_path,
)


@pytest.mark.parametrize(
    "filename",
    [
        "methods.md",
        "table_one.csv",
        "figure-1.png",
        "safe name.txt",
    ],
)
def test_normalize_relative_filename_accepts_plain_filenames(filename):
    assert normalize_relative_filename(filename) == filename


@pytest.mark.parametrize(
    "filename",
    [
        "",
        "   ",
        ".env",
        "../secret.md",
        "nested/secret.md",
        r"nested\secret.md",
        "/tmp/secret.md",
        r"\tmp\secret.md",
        r"\\server\share\secret.md",
        "C:/tmp/secret.md",
        r"C:\tmp\secret.md",
        "CON.md",
        "aux.txt",
        "NUL",
        "bad:name.md",
        "bad*name.md",
        "bad\nname.md",
        "bad\x1fname.md",
    ],
)
def test_normalize_relative_filename_rejects_cross_platform_unsafe_names(filename):
    with pytest.raises((PathGuardError, ValueError)):
        normalize_relative_filename(filename)


def test_resolve_child_path_stays_under_base(tmp_path):
    child = resolve_child_path(tmp_path, "methods.md")

    assert Path(child) == tmp_path.resolve() / "methods.md"


@pytest.mark.parametrize("filename", ["../escape.md", r"C:\tmp\escape.md", "CON.md"])
def test_resolve_child_path_rejects_unsafe_names(tmp_path, filename):
    with pytest.raises((PathGuardError, ValueError)):
        resolve_child_path(tmp_path, filename)


def test_resolve_child_path_rejects_case_insensitive_collisions(tmp_path):
    (tmp_path / "Report.docx").write_text("existing", encoding="utf-8")

    with pytest.raises(PathGuardError):
        resolve_child_path(tmp_path, "report.docx")

    assert resolve_child_path(tmp_path, "Report.docx") == tmp_path.resolve() / "Report.docx"


def test_resolve_child_directory_accepts_relative_segments(tmp_path):
    resolved = resolve_child_directory(tmp_path, "exports/figures")

    assert resolved == tmp_path.resolve() / "exports" / "figures"


@pytest.mark.parametrize(
    "directory",
    ["../escape", "/tmp/escape", r"C:\tmp\escape", r"nested\escape", "CON/reports", "bad\nname"],
)
def test_resolve_child_directory_rejects_cross_platform_unsafe_segments(tmp_path, directory):
    with pytest.raises(PathGuardError):
        resolve_child_directory(tmp_path, directory)
