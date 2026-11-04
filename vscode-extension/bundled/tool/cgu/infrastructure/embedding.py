"""Embedding backends. The n-gram backend is the honest fallback: lexical overlap, not meaning."""

from __future__ import annotations

import asyncio
import time
import zlib
from collections.abc import Sequence

import httpx
import numpy as np

from cgu.application.ports import Embedded, EmbeddingInfo, EmbeddingPort, EmbeddingUnavailableError
from cgu.domain.measure import normalize
from cgu.infrastructure.config import Settings

NGRAM_BACKEND = "ngram-hash"
NGRAM_DIM = 512
_MULTIPLIER = np.uint64(0x9E3779B97F4A7C15)


def _mix64(x: np.ndarray) -> np.ndarray:
    x = (x ^ (x >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
    x = (x ^ (x >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
    return np.asarray(x ^ (x >> np.uint64(31)))


def _ngram_vector(text: str) -> np.ndarray:
    folded = normalize(text)
    vector = np.zeros(NGRAM_DIM, dtype=np.float64)
    if not folded:
        return vector
    codes = np.frombuffer(folded.encode("utf-32-le"), dtype=np.uint32).astype(np.uint64)
    with np.errstate(over="ignore"):
        for n in (2, 3):
            count = len(codes) - n + 1
            if count < 1:
                continue
            h = np.full(count, n, dtype=np.uint64)
            for k in range(n):
                h = h * _MULTIPLIER + codes[k : k + count]
            h = _mix64(h)
            slots = (h % np.uint64(NGRAM_DIM)).astype(np.intp)
            signs = np.where((h >> np.uint64(16)) & np.uint64(1), 1.0, -1.0)
            vector += np.bincount(slots, weights=signs, minlength=NGRAM_DIM)
    if not vector.any():
        vector[zlib.crc32(folded.encode()) % NGRAM_DIM] = 1.0
    return vector


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return np.asarray(matrix / norms)


class NgramHashEmbedding:
    async def describe(self) -> EmbeddingInfo:
        return EmbeddingInfo(backend=NGRAM_BACKEND, semantic=False)

    async def embed(self, texts: Sequence[str]) -> Embedded:
        items = list(texts)
        vectors = await asyncio.to_thread(self._embed_sync, items)
        return Embedded(vectors=vectors, backend=NGRAM_BACKEND, semantic=False)

    @staticmethod
    def _embed_sync(texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        matrix = _normalize_rows(np.stack([_ngram_vector(t) for t in texts]))
        return [[float(x) for x in row] for row in matrix]


class OllamaEmbedding:
    def __init__(
        self,
        url: str,
        model: str,
        client: httpx.AsyncClient | None = None,
        timeout: float = 15.0,
    ) -> None:
        self._url = url
        self._model = model
        self._timeout = timeout
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._owns_client = client is None

    @property
    def backend(self) -> str:
        return f"ollama:{self._model}"

    async def describe(self) -> EmbeddingInfo:
        await self.embed(["ping"])
        return EmbeddingInfo(backend=self.backend, semantic=True)

    async def embed(self, texts: Sequence[str]) -> Embedded:
        items = list(texts)
        if not items:
            return Embedded(vectors=[], backend=self.backend, semantic=True)
        try:
            response = await self._client.post(
                f"{self._url}/api/embed",
                json={"model": self._model, "input": items},
                timeout=self._timeout,
            )
            response.raise_for_status()
            raw = response.json()["embeddings"]
            matrix = np.asarray(raw, dtype=np.float64)
            if matrix.ndim != 2 or matrix.shape[0] != len(items):
                raise ValueError("unexpected embedding shape")
        except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
            raise EmbeddingUnavailableError(f"ollama embedding failed: {exc}") from exc
        vectors = [[float(x) for x in row] for row in _normalize_rows(matrix)]
        return Embedded(vectors=vectors, backend=self.backend, semantic=True)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


class AutoEmbedding:
    """Semantic embedding when Ollama answers, otherwise n-grams with an explicit warning."""

    def __init__(
        self, ollama: OllamaEmbedding, fallback: NgramHashEmbedding, retry_after: float = 60.0
    ) -> None:
        self._ollama = ollama
        self._fallback = fallback
        self._retry_after = retry_after
        self._down_since: float | None = None

    def _should_try_ollama(self) -> bool:
        return self._down_since is None or time.monotonic() - self._down_since >= self._retry_after

    async def describe(self) -> EmbeddingInfo:
        if self._should_try_ollama():
            try:
                info = await self._ollama.describe()
                self._down_since = None
                return info
            except EmbeddingUnavailableError:
                self._down_since = time.monotonic()
        return await self._fallback.describe()

    async def embed(self, texts: Sequence[str]) -> Embedded:
        if self._should_try_ollama():
            try:
                result = await self._ollama.embed(texts)
                self._down_since = None
                return result
            except EmbeddingUnavailableError:
                self._down_since = time.monotonic()
        result = await self._fallback.embed(texts)
        result.warnings.append(
            "ollama embedding unavailable; fell back to char n-gram hashing (semantic=false)"
        )
        return result

    async def aclose(self) -> None:
        await self._ollama.aclose()


def make_embedding(settings: Settings, client: httpx.AsyncClient) -> EmbeddingPort:
    if settings.embedding == "ngram":
        return NgramHashEmbedding()
    ollama = OllamaEmbedding(settings.ollama_url, settings.embed_model, client=client)
    if settings.embedding == "ollama":
        return ollama
    return AutoEmbedding(ollama, NgramHashEmbedding())
