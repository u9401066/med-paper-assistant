"""Save paths for verified PubMed articles and agent-provided metadata."""

import hashlib
import json
import os
from copy import deepcopy
from typing import Any, Dict

import structlog

logger = structlog.get_logger()


class SaveReferenceMixin:
    """Save paths for verified PubMed articles and agent-provided metadata."""

    def save_reference(self, article: Dict[str, Any], download_pdf: bool = False) -> str:
        """
        Save a reference with provided article metadata.

        檔案結構 (2025-12 重構):
        ```
        references/
        └── {unique_id}/
            ├── {citation_key}.md   ← 主檔案，包含 YAML frontmatter + 內容
            └── metadata.json       ← 程式用完整 metadata
        ```

        支援來源：
        - PubMed (需要 pmid 欄位)
        - Zotero (需要 key 或 zotero_key 欄位)
        - DOI (需要 doi 或 DOI 欄位)

        Args:
            article: Article metadata dictionary from any source.
                     Must contain at least one identifier: pmid, zotero_key/key, or doi/DOI.
            download_pdf: Deprecated - PDF download handled externally.

        Returns:
            Status message with Foam citation key.
        """
        # This public path is Agent-mediated.  Strip transport attestations so
        # callers cannot promote arbitrary metadata by adding ``verified=true``.
        untrusted_article = dict(article)
        untrusted_article.pop("_verified", None)
        untrusted_article.pop("_pubmed_transport_payload", None)
        untrusted_article.pop("pubmed_transport_payload", None)
        untrusted_article["verified"] = False
        untrusted_article["data_source"] = "agent"
        untrusted_article["trust_level"] = "agent"
        for field in ("retrieved_at", "source_url", "payload_hash", "provenance"):
            untrusted_article.pop(field, None)

        return self._save_reference_article(
            untrusted_article,
            download_pdf=download_pdf,
        )

    def _save_reference_article(
        self,
        article: Dict[str, Any],
        *,
        download_pdf: bool = False,
    ) -> str:
        """Persist an article after its caller has established the trust boundary."""
        if download_pdf:
            logger.warning(
                "reference_manager.download_pdf_deprecated",
                guidance="Use the asset-aware full-text ingestion pathway instead.",
            )
        # Use domain converter to standardize format
        try:
            ref = self._converter.convert(article)
        except ValueError as e:
            return f"Error: {str(e)}"

        # Check if already exists
        ref_dir = self._reference_dir(ref.unique_id)
        if os.path.exists(ref_dir):
            return f"Reference {ref.unique_id} already exists."

        # Add pre-formatted citation strings to metadata
        ref_dict = ref.to_dict()
        transport_payload = article.get("_pubmed_transport_payload")
        if ref.verified and isinstance(transport_payload, dict):
            canonical = json.dumps(
                transport_payload,
                allow_nan=False,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            if hashlib.sha256(canonical).hexdigest() != ref.payload_hash:
                return "Error: PubMed transport payload no longer matches its provenance hash."
            ref_dict["pubmed_transport_payload"] = deepcopy(transport_payload)
        ref_dict["citation"] = self._format_citation(ref_dict)
        ref_dict["saved_at"] = __import__("datetime").datetime.now().isoformat()

        persisted_dir = self._persist_reference_payload(ref_dict, log_event="save_reference")

        # No need for separate alias file - aliases are in frontmatter
        # Foam will recognize [[citation_key]] via the filename and aliases

        foam_tip = f"\n💡 Foam: Use [[{ref.citation_key}]] to link this reference."
        source_info = f" (source: {ref.source})"
        return f"Successfully saved reference {ref.unique_id} to {persisted_dir}.{source_info}{foam_tip}"

    def save_reference_by_pmid(self, pmid: str) -> str:
        """
        [DEPRECATED] 舊版接口，保留向後相容。

        新的工作流程應該是:
        1. Agent 呼叫 pubmed-search MCP 的 fetch_article_details(pmid)
        2. Agent 呼叫 mdpaper MCP 的 save_reference(article_metadata)

        或者使用新的 MCP-to-MCP 方法:
        - save_reference_mcp(pmid, agent_notes) - 自動從 pubmed-search 取得驗證資料

        Returns:
            提示訊息，指引使用者使用新的工作流程。
        """
        return (
            f"❌ save_reference_by_pmid is deprecated.\n\n"
            f"New workflows:\n\n"
            f"Option A - Agent-mediated (current):\n"
            f"1. pubmed-search: fetch_article_details(pmid='{pmid}')\n"
            f"2. mdpaper: save_reference(article=<metadata>)\n\n"
            f"Option B - MCP-to-MCP direct (recommended):\n"
            f"1. mdpaper: save_reference_mcp(pmid='{pmid}', agent_notes='...')\n"
            f"   → mdpaper fetches verified data directly from pubmed-search"
        )
