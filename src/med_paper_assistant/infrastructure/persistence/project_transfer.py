"""Transactional project directory transfer used by exploration conversion."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def transfer_project_tree(source: Path, target: Path, *, keep_temp: bool) -> None:
    """Move (or copy, when ``keep_temp``) ``source`` to a not-yet-existing ``target``.

    The target only ever appears fully populated: copies are staged in a sibling
    directory and renamed into place, and a failed attempt removes its staging
    directory so a retry does not hit a half-built "already exists" target.
    """
    if not keep_temp:
        try:
            os.rename(source, target)
            return
        except OSError:
            pass  # e.g. cross-device; fall back to a staged copy + delete

    stage = target.with_name(f".{target.name}.converting")
    shutil.rmtree(stage, ignore_errors=True)
    try:
        shutil.copytree(source, stage)
        os.rename(stage, target)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    if not keep_temp:
        shutil.rmtree(source, ignore_errors=True)
