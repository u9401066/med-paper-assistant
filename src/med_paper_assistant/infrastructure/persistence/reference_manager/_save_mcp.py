"""MCP-to-MCP save path: fetch PubMed-verified metadata and persist it."""

from copy import deepcopy
from typing import Any, Dict, Optional, Tuple

import structlog

logger = structlog.get_logger()


class VerifiedSaveMixin:
    """Save references from verified PubMed payloads fetched by PMID."""

    def save_reference_mcp(
        self, pmid: str, agent_notes: str = "", fetch_if_missing: bool = True
    ) -> str:
        """
        Save reference using MCP-to-MCP direct communication.

        This is the NEW preferred method that ensures data integrity:
        1. Agent only passes PMID and optional notes
        2. mdpaper fetches verified metadata directly from pubmed-search HTTP API
        3. Prevents Agent from modifying/hallucinating bibliographic data

        Reference file structure (Layered Trust):
        ```
        ---
        # 🔒 VERIFIED (PubMed, immutable)
        source: pubmed
        pmid: "12345678"
        title: "Original Title from PubMed"
        ...

        # 🤖 AGENT (AI-generated)
        agent_notes: "Notes from AI assistant"

        # ✏️ USER (Human edits)
        user_tags: []
        user_notes: ""
        ---
        ```

        Args:
            pmid: PubMed ID (the ONLY required input from Agent)
            agent_notes: Optional notes from Agent about this reference
            fetch_if_missing: If True, fetch from PubMed if not in cache

        Returns:
            Status message with Foam citation key.
        """
        verified_article, error_message = self._fetch_verified_article(
            pmid, agent_notes, fetch_if_missing
        )
        if verified_article is None:
            return error_message
        return self._save_reference_article(verified_article)

    def _fetch_verified_article(
        self, pmid: str, agent_notes: str, fetch_if_missing: bool
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """Return ``(verified_article, "")`` or ``(None, user_facing_error)``."""
        # Import here to avoid circular dependency
        from med_paper_assistant.infrastructure.services.pubmed_api_client import (
            PubMedVerificationError,
            get_pubmed_api_client,
        )

        # Get the API client
        client = get_pubmed_api_client(base_url=self._pubmed_api_url)

        # Check if pubmed-search API is available
        if not client.check_health():
            logger.warning(
                "[MCP-to-MCP] pubmed-search API not available, "
                "falling back to Agent-provided data requirement"
            )
            return None, self._pubmed_unavailable_message(pmid)

        # Fetch verified data directly from pubmed-search
        logger.info(f"[MCP-to-MCP] Fetching PMID:{pmid} from pubmed-search")
        try:
            article: object = client.get_cached_article(
                pmid,
                fetch_if_missing=fetch_if_missing,
            )
        except PubMedVerificationError as exc:
            self._log_pubmed_rejection(pmid, str(exc))
            return None, f"❌ PubMed verification rejected for PMID:{pmid}: {exc}"

        if article is None:
            return None, self._pubmed_not_found_message(pmid)

        return self._reference_from_verified_payload(pmid, article, agent_notes)

    def _reference_from_verified_payload(
        self, pmid: str, article: object, agent_notes: str
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        from med_paper_assistant.infrastructure.services.pubmed_api_client import (
            PubMedVerificationError,
            VerifiedArticlePayload,
        )

        if not isinstance(article, VerifiedArticlePayload):
            self._log_pubmed_rejection(pmid, "client returned an unattested payload")
            return None, (
                f"❌ PubMed verification rejected for PMID:{pmid}: "
                "client returned an unattested payload."
            )

        # Trust fields are minted by PubMedAPIClient, never by this consumer.
        try:
            verified_article = article.to_reference_dict(agent_notes=agent_notes)
        except PubMedVerificationError as exc:
            self._log_pubmed_rejection(pmid, str(exc))
            return None, f"❌ PubMed verification rejected for PMID:{pmid}: {exc}"
        verified_article["_pubmed_transport_payload"] = deepcopy(article.article)
        return verified_article, ""

    def _log_pubmed_rejection(self, pmid: str, reason: str) -> None:
        logger.warning(
            "reference_manager.pubmed_verification_rejected",
            pmid=str(pmid),
            reason=reason,
        )

    def _pubmed_unavailable_message(self, pmid: str) -> str:
        return (
            f"⚠️ pubmed-search MCP HTTP API is not available.\n"
            f"Please ensure pubmed-search is running with HTTP API enabled.\n\n"
            f"Alternative: Use the traditional workflow:\n"
            f"1. pubmed-search: fetch_article_details(pmid='{pmid}')\n"
            f"2. mdpaper: save_reference(article=<metadata>)"
        )

    def _pubmed_not_found_message(self, pmid: str) -> str:
        return (
            f"❌ Article PMID:{pmid} not found.\n\n"
            f"Please search for it first using pubmed-search MCP, then try again.\n"
            f"Example: unified_search(query='{pmid}[pmid]')"
        )
