from __future__ import annotations

import pytest

from med_paper_assistant.infrastructure.persistence.file_storage import FileStorage


def test_file_storage_delete_refuses_storage_root(tmp_path):
    storage = FileStorage(tmp_path)
    (tmp_path / "keep.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError):
        storage.delete(".")

    assert tmp_path.exists()
    assert (tmp_path / "keep.txt").exists()


@pytest.mark.parametrize(
    "src,dst", [("../outside.txt", "inside.txt"), ("inside.txt", "../outside.txt")]
)
def test_file_storage_move_uses_safe_paths(tmp_path, src, dst):
    storage = FileStorage(tmp_path)
    (tmp_path / "inside.txt").write_text("content", encoding="utf-8")

    with pytest.raises(ValueError):
        storage.move(src, dst)


def test_file_storage_list_files_rejects_traversal_glob(tmp_path):
    storage = FileStorage(tmp_path)

    with pytest.raises(ValueError):
        storage.list_files("../*")
