"""Value objects shared by the figure/table note materialization helpers."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class AssetNoteRun:
    project_root: Path
    project_slug: str
    tracker: Any
    contexts: List[Dict[str, Any]]
    aliases: Dict[str, Dict[str, str]]
    expected_paths: Dict[str, List[str]]


@dataclass
class AssetEntryContext:
    asset_type: str
    number: int
    filename: str
    slug: str
    alias: str
    note_path: str
    relative_asset_path: str
    asset_path: Path
    review: Any
    review_state: str
    caption: Any
    title: str
    source_fragment: Dict[str, Any]
