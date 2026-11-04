"""Optional local LLM, used only when CGU_PROVIDER=ollama."""

from __future__ import annotations

import httpx

from cgu.application.ports import LLMUnavailableError


class OllamaLLM:
    def __init__(
        self,
        url: str,
        model: str,
        client: httpx.AsyncClient | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._url = url
        self.model = model
        self._timeout = timeout
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._owns_client = client is None

    async def complete(self, prompt: str, *, seed: int | None = None) -> str:
        options: dict[str, int | float] = {"temperature": 0.8}
        if seed is not None:
            options["seed"] = seed
        try:
            response = await self._client.post(
                f"{self._url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": options,
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            return str(response.json()["response"])
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise LLMUnavailableError(f"ollama generation failed: {exc}") from exc

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
