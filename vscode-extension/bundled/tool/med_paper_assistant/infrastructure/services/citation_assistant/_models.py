"""Data models for citation analysis: claim types, claims, suggestions and the report."""

from dataclasses import dataclass
from enum import Enum


class ClaimType(Enum):
    """文字聲稱的類型，決定需要什麼類型的引用"""

    STATISTICAL = "statistical"  # 統計數據 (e.g., "發生率為 15%")
    COMPARISON = "comparison"  # 比較聲稱 (e.g., "A 比 B 更好")
    MECHANISM = "mechanism"  # 機制說明 (e.g., "透過...作用")
    HISTORICAL = "historical"  # 歷史/背景 (e.g., "自1990年以來...")
    GUIDELINE = "guideline"  # 指引建議 (e.g., "指引建議...")
    CONSENSUS = "consensus"  # 共識 (e.g., "普遍認為...")
    DEFINITION = "definition"  # 定義 (e.g., "...定義為...")
    GENERAL = "general"  # 一般性陳述


@dataclass
class TextClaim:
    """從文字中提取的聲稱"""

    text: str  # 原文
    claim_type: ClaimType
    key_terms: list[str]  # 關鍵詞
    needs_citation: bool  # 是否需要引用
    reason: str  # 原因說明
    suggested_search: str = ""  # 建議的 PubMed 搜尋詞


@dataclass
class CitationSuggestion:
    """引用建議"""

    pmid: str
    citation_key: str
    title: str
    relevance_score: float  # 0-1
    relevance_reason: str
    matching_terms: list[str]
    source: str  # "local" or "pubmed_suggested"


@dataclass
class CitationAnalysisResult:
    """完整的引用分析結果"""

    original_text: str
    claims: list[TextClaim]
    local_suggestions: list[CitationSuggestion]
    pubmed_search_queries: list[str]
    has_existing_citations: bool
    existing_citations: list[str]
    summary: str = ""

    def to_markdown(self) -> str:
        """輸出為 Markdown 格式報告"""
        output = "## 🔍 Citation Analysis Report\n\n"

        # 1. 現有引用
        if self.existing_citations:
            output += "### ✅ Existing Citations\n"
            for cit in self.existing_citations:
                output += f"- `[[{cit}]]`\n"
            output += "\n"

        # 2. 分析出的聲稱
        needs_citation_claims = [c for c in self.claims if c.needs_citation]
        if needs_citation_claims:
            output += "### 📝 Statements Requiring Citations\n\n"
            output += "| Statement | Type | Reason |\n"
            output += "|-----------|------|--------|\n"
            for claim in needs_citation_claims:
                text_preview = claim.text[:50] + "..." if len(claim.text) > 50 else claim.text
                output += f"| {text_preview} | {claim.claim_type.value} | {claim.reason} |\n"
            output += "\n"

        # 3. 本地文獻建議
        if self.local_suggestions:
            output += "### 📚 Suggested from Local Library\n\n"
            for sug in sorted(self.local_suggestions, key=lambda x: -x.relevance_score)[:5]:
                score_bar = "█" * int(sug.relevance_score * 5) + "░" * (
                    5 - int(sug.relevance_score * 5)
                )
                output += f"**[[{sug.citation_key}]]** [{score_bar}]\n"
                output += f"  - {sug.title[:60]}...\n"
                output += f"  - 相關性: {sug.relevance_reason}\n"
                output += f"  - 匹配詞: {', '.join(sug.matching_terms)}\n\n"
        else:
            output += "### 📚 Local Library\n"
            output += "*No relevant references found in local library.*\n\n"

        # 4. PubMed 搜尋建議
        if self.pubmed_search_queries:
            output += "### 🔎 Suggested PubMed Searches\n\n"
            output += "Use `pubmed-search` MCP to find new references:\n\n"
            for i, query in enumerate(self.pubmed_search_queries[:3], 1):
                output += f'{i}. `unified_search(query="{query}")`\n'
            output += "\n"

        # 5. 總結
        if self.summary:
            output += f"### 💡 Summary\n\n{self.summary}\n"

        return output
