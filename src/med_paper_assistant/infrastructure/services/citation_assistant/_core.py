"""CitationAssistant: entry points for analysing text and scanning drafts."""

import os
import re
from typing import TYPE_CHECKING

from ._claims import ClaimAnalysisMixin
from ._models import CitationAnalysisResult, CitationSuggestion, TextClaim
from ._search import ReferenceSearchMixin, unique_by_pmid

if TYPE_CHECKING:
    from med_paper_assistant.infrastructure.persistence.reference_manager import ReferenceManager


class CitationAssistant(ReferenceSearchMixin, ClaimAnalysisMixin):
    """智慧引用助手"""

    def __init__(self, reference_manager: "ReferenceManager"):
        self.ref_manager = reference_manager

    def analyze_text(
        self,
        text: str,
        context: str = "",
        search_local: bool = True,
        generate_queries: bool = True,
    ) -> CitationAnalysisResult:
        """
        分析一段文字，提供引用建議。

        Args:
            text: 要分析的文字
            context: 額外上下文（如章節標題）
            search_local: 是否搜尋本地文獻庫
            generate_queries: 是否生成 PubMed 搜尋建議

        Returns:
            CitationAnalysisResult 包含完整分析
        """
        # 1. 檢查現有引用
        existing = self._extract_existing_citations(text)

        # 2. 分析文字中的聲稱
        claims = self._analyze_text_claims(text)

        # 3. 本地搜尋
        local_suggestions = []
        if search_local:
            local_suggestions = self._search_local_for_claims(claims)

        # 4. 生成 PubMed 搜尋建議
        pubmed_queries = []
        if generate_queries:
            pubmed_queries = self._generate_pubmed_queries(claims, local_suggestions)

        # 5. 生成總結
        summary = self._generate_summary(claims, local_suggestions, pubmed_queries)

        return CitationAnalysisResult(
            original_text=text,
            claims=claims,
            local_suggestions=local_suggestions,
            pubmed_search_queries=pubmed_queries,
            has_existing_citations=len(existing) > 0,
            existing_citations=existing,
            summary=summary,
        )

    def suggest_for_selection(
        self,
        selected_text: str,
        draft_content: str = "",
        section: str = "",
    ) -> str:
        """
        為用戶選取的文字提供引用建議。

        這是主要的用戶介面方法。

        Args:
            selected_text: 用戶選取的文字
            draft_content: 完整的草稿內容（用於上下文）
            section: 所在章節（Introduction/Methods/Results/Discussion）

        Returns:
            Markdown 格式的建議報告
        """
        context = f"Section: {section}" if section else ""
        result = self.analyze_text(selected_text, context=context)
        return result.to_markdown()

    def scan_draft_for_citations(self, draft_path: str) -> str:
        """
        掃描整篇草稿，找出所有需要引用的地方。

        Args:
            draft_path: 草稿檔案路徑

        Returns:
            完整的引用建議報告
        """
        if not os.path.exists(draft_path):
            return f"❌ File not found: {draft_path}"

        with open(draft_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 按段落分析
        paragraphs = re.split(r"\n\n+", content)
        all_claims: list[TextClaim] = []
        all_suggestions: list[CitationSuggestion] = []

        for para in paragraphs:
            if not para.strip() or para.startswith("#"):
                continue
            result = self.analyze_text(para, search_local=True, generate_queries=False)
            all_claims.extend([c for c in result.claims if c.needs_citation])
            all_suggestions.extend(result.local_suggestions)

        # 去重
        unique_suggestions = unique_by_pmid(all_suggestions)

        # 生成 PubMed 搜尋建議
        pubmed_queries = self._generate_pubmed_queries(all_claims, unique_suggestions)

        final_result = CitationAnalysisResult(
            original_text=f"[Full draft: {draft_path}]",
            claims=all_claims,
            local_suggestions=unique_suggestions[:10],  # Top 10
            pubmed_search_queries=pubmed_queries,
            has_existing_citations=bool(self._extract_existing_citations(content)),
            existing_citations=self._extract_existing_citations(content),
            summary=f"Found {len(all_claims)} statements that may need citations.",
        )

        return final_result.to_markdown()
