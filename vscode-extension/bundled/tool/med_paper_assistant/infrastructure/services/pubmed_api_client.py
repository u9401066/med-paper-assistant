"""
HTTP Client for MCP-to-MCP communication.

This module provides a client for mdpaper to communicate directly
with pubmed-search MCP via HTTP API, bypassing the Agent.

Author: u9401066@gap.kmu.edu.tw
"""

import hashlib
import json
import os
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
import structlog

logger = structlog.get_logger()

# Default configuration
DEFAULT_PUBMED_API_URL = "http://127.0.0.1:8765"


class PubMedVerificationError(ValueError):
    """Raised when the PubMed HTTP API violates the verified-data contract."""


def _canonical_payload_hash(article: Dict[str, Any]) -> str:
    """Hash strict canonical JSON so the audit anchor is reproducible."""
    try:
        canonical_payload = json.dumps(
            article,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PubMedVerificationError("PubMed transport payload is not canonical JSON.") from exc
    return hashlib.sha256(canonical_payload).hexdigest()


@dataclass(frozen=True)
class VerifiedArticlePayload:
    """Article metadata that passed the trusted PubMed transport boundary.

    Callers cannot construct a verified reference by adding a boolean to an
    arbitrary article dictionary.  Only ``PubMedAPIClient`` creates this
    payload after validating the response envelope, PMID identity, and source
    provenance and after computing a canonical payload hash.
    """

    article: Dict[str, Any]
    data_source: str
    retrieved_at: str
    source_url: str
    payload_hash: str
    provenance: tuple[Dict[str, Any], ...]

    def to_reference_dict(self, *, agent_notes: str = "") -> Dict[str, Any]:
        """Return the canonical persistence payload with layered trust data.

        Integrity is checked again here so a mutated or manually constructed
        transport object cannot cross the persistence boundary as VERIFIED.
        """
        actual_hash = _canonical_payload_hash(self.article)
        article_pmid = str(self.article.get("pmid") or "").strip()
        title = self.article.get("title")
        try:
            retrieval_time = datetime.fromisoformat(self.retrieved_at)
            parsed_source_url = httpx.URL(self.source_url)
            valid_transport_coordinates = bool(
                retrieval_time.tzinfo is not None
                and parsed_source_url.scheme in {"http", "https"}
                and parsed_source_url.host
            )
        except (TypeError, ValueError, httpx.InvalidURL):
            valid_transport_coordinates = False
        matching_provenance = any(
            isinstance(entry, dict)
            and entry.get("event") == "pubmed_mcp_fetch"
            and entry.get("source") == "pubmed"
            and entry.get("data_source") == self.data_source
            and str(entry.get("requested_pmid") or "") == article_pmid
            and entry.get("source_url") == self.source_url
            and entry.get("retrieved_at") == self.retrieved_at
            and entry.get("payload_hash") == self.payload_hash
            for entry in self.provenance
        )
        if (
            self.data_source != "pubmed_mcp_api"
            or not article_pmid.isdigit()
            or not isinstance(title, str)
            or not title.strip()
            or actual_hash != self.payload_hash
            or not valid_transport_coordinates
            or not matching_provenance
        ):
            raise PubMedVerificationError(
                "PubMed transport attestation is incomplete or no longer matches its payload."
            )

        payload = deepcopy(self.article)
        payload.update(
            {
                "verified": True,
                "data_source": self.data_source,
                "retrieved_at": self.retrieved_at,
                "source_url": self.source_url,
                "payload_hash": self.payload_hash,
                "provenance": [deepcopy(entry) for entry in self.provenance],
                "agent_notes": agent_notes,
                "trust_level": "verified",
            }
        )
        return payload


def _resolve_base_url(base_url: Optional[str] = None) -> str:
    candidate = base_url or os.environ.get("PUBMED_MCP_API_URL", DEFAULT_PUBMED_API_URL)
    normalized = str(candidate).strip().rstrip("/")
    if not normalized:
        return DEFAULT_PUBMED_API_URL
    return normalized


class PubMedAPIClient:
    """
    HTTP client for communicating with pubmed-search MCP's HTTP API.

    This enables MCP-to-MCP direct communication for verified data:
    - mdpaper only receives PMID from Agent
    - mdpaper fetches verified metadata directly from pubmed-search
    - Prevents Agent from modifying/hallucinating bibliographic data
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        """
        Initialize the API client.

        Args:
            base_url: pubmed-search API URL (default from env or localhost:8765)
            timeout: Request timeout in seconds
        """
        self.base_url = _resolve_base_url(base_url)
        self.timeout = timeout
        logger.info(f"PubMedAPIClient initialized with URL: {self.base_url}")

    @staticmethod
    def _validate_article_response(
        envelope: Any,
        *,
        requested_pmid: str,
        source_url: str,
    ) -> VerifiedArticlePayload:
        """Validate and normalize one verified PubMed response envelope."""
        if not isinstance(envelope, dict):
            raise PubMedVerificationError("Malformed PubMed response: expected a JSON object.")

        if envelope.get("verified") is not True:
            raise PubMedVerificationError("PubMed response is not explicitly verified.")

        # ``source`` is the upstream API's minimum provenance assertion.  The
        # current pubmed-search auxiliary API does not emit a separate
        # provenance object, so a missing or non-PubMed source must fail closed.
        upstream_source = envelope.get("source")
        if not isinstance(upstream_source, str) or upstream_source.strip().lower() != "pubmed":
            raise PubMedVerificationError("PubMed response is missing trusted source provenance.")

        article = envelope.get("data")
        if not isinstance(article, dict):
            raise PubMedVerificationError(
                "Malformed PubMed response: 'data' must be a JSON object."
            )

        response_pmid = str(article.get("pmid") or "").strip()
        if not response_pmid:
            raise PubMedVerificationError("Malformed PubMed response: article PMID is missing.")
        if response_pmid != requested_pmid:
            raise PubMedVerificationError(
                f"PubMed identity mismatch: requested PMID {requested_pmid}, "
                f"received PMID {response_pmid}."
            )
        if not isinstance(article.get("title"), str) or not article["title"].strip():
            raise PubMedVerificationError("Malformed PubMed response: article title is missing.")

        payload_hash = _canonical_payload_hash(article)
        retrieved_at = datetime.now(timezone.utc).isoformat()
        provenance = (
            {
                "event": "pubmed_mcp_fetch",
                "source": upstream_source.strip().lower(),
                "data_source": "pubmed_mcp_api",
                "requested_pmid": requested_pmid,
                "source_url": source_url,
                "retrieved_at": retrieved_at,
                "payload_hash": payload_hash,
            },
        )

        return VerifiedArticlePayload(
            article=deepcopy(article),
            data_source="pubmed_mcp_api",
            retrieved_at=retrieved_at,
            source_url=source_url,
            payload_hash=payload_hash,
            provenance=provenance,
        )

    def get_cached_article(
        self, pmid: str, fetch_if_missing: bool = True
    ) -> Optional[VerifiedArticlePayload]:
        """
        Get article metadata from pubmed-search cache.

        This is the primary method for MCP-to-MCP data retrieval.

        Args:
            pmid: PubMed ID
            fetch_if_missing: If True, pubmed-search will fetch from NCBI if not cached

        Returns:
            Validated article payload, or None if not found/unavailable.

        Raises:
            PubMedVerificationError: If a successful response is unverified,
                malformed, lacks source provenance, or contains another PMID.
        """
        requested_pmid = str(pmid).strip()
        if not requested_pmid.isdigit():
            raise PubMedVerificationError("PMID must contain digits only.")

        try:
            url = f"{self.base_url}/api/cached_article/{requested_pmid}"
            params = {"fetch_if_missing": str(fetch_if_missing).lower()}

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=params)

                if response.status_code == 200:
                    try:
                        envelope = response.json()
                    except (TypeError, ValueError) as exc:
                        raise PubMedVerificationError(
                            "Malformed PubMed response: invalid JSON."
                        ) from exc

                    verified = self._validate_article_response(
                        envelope,
                        requested_pmid=requested_pmid,
                        source_url=str(response.request.url),
                    )
                    logger.info(f"[MCP-to-MCP] Retrieved verified article PMID:{requested_pmid}")
                    return verified

                elif response.status_code == 404:
                    logger.warning(f"[MCP-to-MCP] Article not found: PMID:{requested_pmid}")
                    return None

                else:
                    logger.error(f"[MCP-to-MCP] HTTP error {response.status_code}: {response.text}")
                    return None

        except PubMedVerificationError:
            logger.warning(
                "[MCP-to-MCP] Rejected untrusted PubMed response",
                pmid=requested_pmid,
                exc_info=True,
            )
            raise
        except httpx.RequestError:
            logger.error(
                f"[MCP-to-MCP] Cannot connect to pubmed-search API at {self.base_url}. "
                f"Is pubmed-search MCP running?"
            )
            return None
        except Exception as e:
            logger.error(f"[MCP-to-MCP] Error fetching article: {e}")
            return None

    def get_multiple_articles(
        self, pmids: List[str], fetch_if_missing: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get multiple articles from pubmed-search cache.

        Args:
            pmids: List of PubMed IDs
            fetch_if_missing: If True, fetch missing articles from NCBI

        Returns:
            Dict mapping PMID to article metadata
        """
        try:
            url = f"{self.base_url}/api/cached_articles"
            params = {"pmids": ",".join(pmids), "fetch_if_missing": str(fetch_if_missing).lower()}

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    found = data.get("found", {})
                    missing = data.get("missing", [])

                    if missing:
                        logger.warning(f"[MCP-to-MCP] Missing articles: {missing}")

                    logger.info(f"[MCP-to-MCP] Retrieved {len(found)}/{len(pmids)} articles")
                    return found
                else:
                    logger.error(f"[MCP-to-MCP] HTTP error {response.status_code}")
                    return {}

        except httpx.ConnectError:
            logger.error("[MCP-to-MCP] Cannot connect to pubmed-search API")
            return {}
        except Exception as e:
            logger.error(f"[MCP-to-MCP] Error: {e}")
            return {}

    def check_health(self) -> bool:
        """
        Check if pubmed-search API is available.

        Returns:
            True if API is healthy
        """
        try:
            url = f"{self.base_url}/health"
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
                return response.status_code == 200
        except Exception:
            logger.debug("PubMed API health check failed", exc_info=True)
            return False

    def get_session_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get pubmed-search session summary.

        Returns:
            Session summary dict or None
        """
        try:
            url = f"{self.base_url}/api/session/summary"
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url)
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception:
            logger.debug("Failed to get session summary", exc_info=True)
            return None


# Singleton instance for convenience
_client: Optional[PubMedAPIClient] = None


def get_pubmed_api_client(
    base_url: Optional[str] = None, force_new: bool = False
) -> PubMedAPIClient:
    """
    Get or create the PubMed API client singleton.

    Args:
        base_url: Optional custom API URL
        force_new: If True, create a new instance

    Returns:
        PubMedAPIClient instance
    """
    global _client

    resolved_base_url = _resolve_base_url(base_url)
    if _client is None or force_new or _client.base_url != resolved_base_url:
        _client = PubMedAPIClient(base_url=resolved_base_url)

    return _client
