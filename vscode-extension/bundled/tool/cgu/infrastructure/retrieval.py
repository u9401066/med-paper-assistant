"""Wikipedia retrieval over httpx. Everything it returns is untrusted."""

from __future__ import annotations

import re

import httpx

from cgu import __version__
from cgu.application.ports import RetrievalUnavailableError, RetrievedDoc

_LANG_RE = re.compile(r"^[a-z]{2,3}(-[a-z]{2,8})?$")
USER_AGENT = f"cgu/{__version__} (https://github.com/u9401066/creativity-generation-unit)"


class WikipediaRetrieval:
    def __init__(self, client: httpx.AsyncClient | None = None, timeout: float = 10.0) -> None:
        self._timeout = timeout
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._owns_client = client is None

    async def search(self, query: str, *, lang: str, limit: int) -> list[RetrievedDoc]:
        if not _LANG_RE.match(lang):
            raise RetrievalUnavailableError(f"invalid wikipedia language code {lang!r}")
        params: dict[str, str | int] = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrlimit": limit,
            "prop": "extracts|info",
            "exintro": 1,
            "explaintext": 1,
            "exlimit": "max",
            "inprop": "url",
            "format": "json",
            "formatversion": 2,
        }
        try:
            response = await self._client.get(
                f"https://{lang}.wikipedia.org/w/api.php",
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RetrievalUnavailableError(f"wikipedia search failed: {exc}") from exc
        pages = payload.get("query", {}).get("pages", []) if isinstance(payload, dict) else []
        pages = sorted(pages, key=lambda page: page.get("index", 0))
        return [
            RetrievedDoc(
                title=str(page.get("title", "")),
                text=str(page.get("extract") or ""),
                url=page.get("fullurl"),
                source_id=f"wikipedia:{lang}:{page.get('pageid')}",
            )
            for page in pages[:limit]
        ]

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
