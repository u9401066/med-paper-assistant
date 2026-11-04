"""Settings, read explicitly from the environment (never at import time)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

Provider = Literal["passthrough", "ollama"]
EmbeddingMode = Literal["auto", "ollama", "ngram"]


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    provider: Provider = "passthrough"
    embedding: EmbeddingMode = "ngram"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    embed_model: str = "nomic-embed-text"
    network: bool = True
    log_level: str = "INFO"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "cgu.sqlite3"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        source = os.environ if env is None else env
        provider = source.get("CGU_PROVIDER", "passthrough").strip().lower()
        if provider not in ("passthrough", "ollama"):
            raise ValueError(f"CGU_PROVIDER must be passthrough or ollama, got {provider!r}")
        embedding = source.get("CGU_EMBEDDING", "ngram").strip().lower()
        if embedding not in ("auto", "ollama", "ngram"):
            raise ValueError(f"CGU_EMBEDDING must be auto, ollama or ngram, got {embedding!r}")
        network = source.get("CGU_NETWORK", "on").strip().lower()
        if network not in ("on", "off"):
            raise ValueError(f"CGU_NETWORK must be on or off, got {network!r}")
        data_dir = data_dir_from_env(source)
        url = source.get("CGU_OLLAMA_URL", "http://localhost:11434").strip().rstrip("/")
        url = url.removesuffix("/v1")
        return cls(
            data_dir=Path(data_dir).expanduser(),
            provider=cast(Provider, provider),
            embedding=cast(EmbeddingMode, embedding),
            ollama_url=url,
            ollama_model=source.get("CGU_OLLAMA_MODEL", "qwen2.5:3b"),
            embed_model=source.get("CGU_EMBED_MODEL", "nomic-embed-text"),
            network=network == "on",
            log_level=source.get("CGU_LOG_LEVEL", "INFO").strip().upper(),
        )


def data_dir_from_env(env: Mapping[str, str] | None = None) -> Path:
    """CGU_DATA_DIR, else ~/.cgu. (PLUGIN_DATA is not used: the memory outlives any one plugin.)"""
    source = os.environ if env is None else env
    return Path(source.get("CGU_DATA_DIR") or str(Path.home() / ".cgu")).expanduser()


def copilot_home(env: Mapping[str, str] | None = None) -> Path:
    """Where Copilot CLI keeps its configuration: COPILOT_HOME, else ~/.copilot."""
    source = os.environ if env is None else env
    return Path(source.get("COPILOT_HOME") or str(Path.home() / ".copilot")).expanduser()
