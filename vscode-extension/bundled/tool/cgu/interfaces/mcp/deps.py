"""What the lifespan hands to every tool."""

from __future__ import annotations

from dataclasses import dataclass

from cgu.application.ports import ArchivePort, EmbeddingPort
from cgu.application.services import Services
from cgu.infrastructure.config import Settings


@dataclass
class Deps:
    settings: Settings
    archive: ArchivePort
    embedding: EmbeddingPort
    services: Services
