"""Rule-based claim analysis: which sentences need a citation and what to search for."""

import re
from typing import Optional

from ._constants import CLAIM_RULES, EXISTING_CITATION_PATTERN, STOPWORDS
from ._models import TextClaim


class ClaimAnalysisMixin:
    """Detects existing citations and sentences that need citations."""

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
        if EXISTING_CITATION_PATTERN.search(sentence):
            return None

        for rule in CLAIM_RULES:
            if rule.pattern.search(sentence_lower):
                return TextClaim(
                    text=sentence,
                    claim_type=rule.claim_type,
                    key_terms=self._extract_key_terms(sentence),
                    needs_citation=True,
                    reason=rule.reason,
                    suggested_search=self._generate_search_term(sentence, rule.search_suffix),
                )

        return None

    def _extract_key_terms(self, text: str) -> list[str]:
        """提取關鍵詞"""
        # 簡單版：提取英文專有名詞和醫學術語
        # 未來可整合 NER 或 MeSH 術語庫

        # 提取詞彙
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        key_terms = [w for w in words if w not in STOPWORDS]

        # 取前 5 個最長的（可能是專有名詞）
        return sorted(set(key_terms), key=len, reverse=True)[:5]

    def _generate_search_term(self, sentence: str, suffix: str = "") -> str:
        """根據句子生成搜尋詞"""
        terms = self._extract_key_terms(sentence)
        base_query = " ".join(terms[:3])
        if suffix:
            return f"{base_query} {suffix}"
        return base_query
