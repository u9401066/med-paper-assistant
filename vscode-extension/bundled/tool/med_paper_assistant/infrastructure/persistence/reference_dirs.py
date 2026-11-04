"""Helpers for enumerating saved reference directories."""

from __future__ import annotations

import os
from typing import List


def list_reference_ids(base_dir: str) -> List[str]:
    """Return IDs of directories under ``base_dir`` that hold a ``metadata.json``.

    Hidden directories (e.g. ``.pdf_cache``) and stray folders are ignored so they
    are never reported as references.
    """
    if not os.path.isdir(base_dir):
        return []
    return [
        d
        for d in os.listdir(base_dir)
        if not d.startswith(".") and os.path.isfile(os.path.join(base_dir, d, "metadata.json"))
    ]
