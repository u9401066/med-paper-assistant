"""
Citation Assistant - 智慧引用助手

核心功能：
1. 分析一段文字，理解需要什麼類型的引用支持
2. 從專案已存文獻中找出最相關的
3. 建議需要搜尋的新文獻主題
4. 支援批量引用建議（整篇 draft 掃描）

與 Foam 整合：
- 輸出使用 [[citation_key]] 格式
- 可直接貼入 markdown
- 支援 hover preview

Architecture:
    CitationAssistant (Application Service)
    ├── _analyze_text_claims() - 分析文字中的 claims
    ├── _search_local_references() - 本地搜尋
    ├── _generate_pubmed_queries() - 生成 PubMed 搜尋建議
    └── suggest_citations() - 主入口
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from med_paper_assistant.infrastructure.persistence.reference_manager import ReferenceManager


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


class CitationAssistant:
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
        import os

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
        seen_pmids = set()
        unique_suggestions = []
        for sug in sorted(all_suggestions, key=lambda x: -x.relevance_score):
            if sug.pmid not in seen_pmids:
                seen_pmids.add(sug.pmid)
                unique_suggestions.append(sug)

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

    # ─────────────────────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────────────────────

    def _extract_existing_citations(self, text: str) -> list[str]:
        """提取文字中已有的引用"""
        # [[wikilink]] 格式
        wikilinks = re.findall(r"\[\[([^\]]+)\]\]", text)
        # [PMID:xxx] 或 (PMID:xxx) 格式
        pmid_refs = re.findall(r"[\[\(]PMID:(\d+)[\]\)]", text)
        # [1], [2] 等數字引用
        # num_refs = re.findall(r'\[(\d+)\]', text)

        return wikilinks + [f"PMID:{p}" for p in pmid_refs]

    def _analyze_text_claims(self, text: str) -> list[TextClaim]:
        """
        分析文字中的聲稱。

        使用規則式方法檢測需要引用的陳述。
        """
        claims: list[TextClaim] = []

        # 將文字分成句子
        sentences = re.split(r"[.!?。！？]\s*", text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 20:
                continue

            claim = self._classify_sentence(sentence)
            if claim:
                claims.append(claim)

        return claims

    def _classify_sentence(self, sentence: str) -> Optional[TextClaim]:
        """分類單一句子"""
        sentence_lower = sentence.lower()

        # 跳過已有引用的句子
        if re.search(r"\[\[|\[PMID:|[\(\[]\d+[\)\]]", sentence):
            return None

        # 統計數據模式
        if re.search(
            r"\d+\.?\d*\s*%|\d+/\d+|發生率|死亡率|盛行率|prevalence|incidence|mortality",
            sentence_lower,
        ):
            return TextClaim(
                text=sentence,
                claim_type=ClaimType.STATISTICAL,
                key_terms=self._extract_key_terms(sentence),
                needs_citation=True,
                reason="Statistical claim requires source",
                suggested_search=self._generate_search_term(sentence, "epidemiology"),
            )

        # 比較聲稱
        if re.search(
            r"比.*更|優於|劣於|better|worse|superior|inferior|compared to|versus|vs\.?",
            sentence_lower,
        ):
            return TextClaim(
                text=sentence,
                claim_type=ClaimType.COMPARISON,
                key_terms=self._extract_key_terms(sentence),
                needs_citation=True,
                reason="Comparison claim requires evidence",
                suggested_search=self._generate_search_term(sentence, "comparison"),
            )

        # 指引/共識
        if re.search(r"guideline|指引|建議|recommends?|consensus|共識", sentence_lower):
            return TextClaim(
                text=sentence,
                claim_type=ClaimType.GUIDELINE,
                key_terms=self._extract_key_terms(sentence),
                needs_citation=True,
                reason="Guideline reference required",
                suggested_search=self._generate_search_term(sentence, "guideline"),
            )

        # 機制說明
        if re.search(r"透過|藉由|mechanism|through|via|pathway|mediated", sentence_lower):
            return TextClaim(
                text=sentence,
                claim_type=ClaimType.MECHANISM,
                key_terms=self._extract_key_terms(sentence),
                needs_citation=True,
                reason="Mechanism claim needs supporting evidence",
                suggested_search=self._generate_search_term(sentence, "mechanism"),
            )

        # 研究顯示類
        if re.search(
            r"studies?|research|研究|報告|report|evidence|suggests?|shows?|demonstrates?",
            sentence_lower,
        ):
            return TextClaim(
                text=sentence,
                claim_type=ClaimType.GENERAL,
                key_terms=self._extract_key_terms(sentence),
                needs_citation=True,
                reason="Claim about studies needs citation",
                suggested_search=self._generate_search_term(sentence, ""),
            )

        # 定義
        if re.search(r"定義為|defined as|is defined|refers to", sentence_lower):
            return TextClaim(
                text=sentence,
                claim_type=ClaimType.DEFINITION,
                key_terms=self._extract_key_terms(sentence),
                needs_citation=True,
                reason="Definition should be cited",
                suggested_search=self._generate_search_term(sentence, "definition"),
            )

        return None

    def _extract_key_terms(self, text: str) -> list[str]:
        """提取關鍵詞"""
        # 簡單版：提取英文專有名詞和醫學術語
        # 未來可整合 NER 或 MeSH 術語庫

        # 移除常見停用詞
        stopwords = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "need",
            "dare",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "under",
            "and",
            "but",
            "or",
            "nor",
            "so",
            "yet",
            "both",
            "either",
            "neither",
            "not",
            "only",
            "than",
            "that",
            "this",
            "these",
            "those",
            "such",
            "no",
            "very",
            "just",
            "also",
            "more",
            "most",
            "other",
        }

        # 提取詞彙
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        key_terms = [w for w in words if w not in stopwords]

        # 取前 5 個最長的（可能是專有名詞）
        return sorted(set(key_terms), key=len, reverse=True)[:5]

    def _generate_search_term(self, sentence: str, suffix: str = "") -> str:
        """根據句子生成搜尋詞"""
        terms = self._extract_key_terms(sentence)
        base_query = " ".join(terms[:3])
        if suffix:
            return f"{base_query} {suffix}"
        return base_query

    def _search_local_for_claims(self, claims: list[TextClaim]) -> list[CitationSuggestion]:
        """在本地文獻庫中搜尋與聲稱相關的文獻"""
        suggestions: list[CitationSuggestion] = []

        # 收集所有關鍵詞
        all_terms: set[str] = set()
        for claim in claims:
            all_terms.update(claim.key_terms)

        if not all_terms:
            return suggestions

        # 搜尋本地文獻
        for term in list(all_terms)[:10]:  # 限制搜尋次數
            results = self.ref_manager.search_local(term)

            for meta in results:
                pmid = meta.get("pmid", "")
                if not pmid:
                    continue

                # 計算相關性
                title = meta.get("title", "").lower()
                abstract = meta.get("abstract", "").lower()
                matching_terms = [t for t in all_terms if t in title or t in abstract]

                if not matching_terms:
                    continue

                relevance_score = min(len(matching_terms) / len(all_terms), 1.0) if all_terms else 0

                suggestions.append(
                    CitationSuggestion(
                        pmid=pmid,
                        citation_key=meta.get("citation_key", pmid),
                        title=meta.get("title", "Unknown"),
                        relevance_score=relevance_score,
                        relevance_reason=f"Matches {len(matching_terms)} key terms",
                        matching_terms=matching_terms[:5],
                        source="local",
                    )
                )

        # 去重並按相關性排序
        seen: set[str] = set()
        unique: list[CitationSuggestion] = []
        for sug in sorted(suggestions, key=lambda x: -x.relevance_score):
            if sug.pmid not in seen:
                seen.add(sug.pmid)
                unique.append(sug)

        return unique

    def _generate_pubmed_queries(
        self, claims: list[TextClaim], local_suggestions: list[CitationSuggestion]
    ) -> list[str]:
        """生成 PubMed 搜尋建議"""
        queries: list[str] = []

        # 從需要引用的聲稱中提取搜尋詞
        for claim in claims:
            if claim.needs_citation and claim.suggested_search:
                queries.append(claim.suggested_search)

        # 如果本地找不到足夠的文獻，強化搜尋建議
        if len(local_suggestions) < 3:
            # 合併所有關鍵詞做一個綜合搜尋
            all_terms = set()
            for claim in claims:
                all_terms.update(claim.key_terms[:3])
            if all_terms:
                queries.insert(0, " ".join(list(all_terms)[:5]))

        # 去重
        seen: set[str] = set()
        unique: list[str] = []
        for q in queries:
            q_lower = q.lower().strip()
            if q_lower and q_lower not in seen:
                seen.add(q_lower)
                unique.append(q)

        return unique[:5]  # 最多 5 個建議

    def _generate_summary(
        self,
        claims: list[TextClaim],
        local_suggestions: list[CitationSuggestion],
        pubmed_queries: list[str],
    ) -> str:
        """生成總結"""
        needs_citation = sum(1 for c in claims if c.needs_citation)

        parts = []

        if needs_citation == 0:
            parts.append("✅ No statements found that require citations.")
        else:
            parts.append(f"📝 Found **{needs_citation}** statements that may need citations.")

        if local_suggestions:
            high_relevance = sum(1 for s in local_suggestions if s.relevance_score > 0.5)
            parts.append(
                f"📚 **{len(local_suggestions)}** potential matches in local library ({high_relevance} highly relevant)."
            )
        else:
            parts.append("📚 No matches in local library.")

        if pubmed_queries:
            parts.append(f"🔎 **{len(pubmed_queries)}** suggested PubMed searches generated.")

        return " ".join(parts)
