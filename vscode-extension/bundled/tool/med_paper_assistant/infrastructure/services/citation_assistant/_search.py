"""Local-library search, PubMed query suggestions and summary generation."""

from ._models import CitationSuggestion, TextClaim


def unique_by_pmid(suggestions: list[CitationSuggestion]) -> list[CitationSuggestion]:
    """Sort by relevance (high to low) and keep the first suggestion per PMID."""
    seen: set[str] = set()
    unique: list[CitationSuggestion] = []
    for sug in sorted(suggestions, key=lambda x: -x.relevance_score):
        if sug.pmid not in seen:
            seen.add(sug.pmid)
            unique.append(sug)
    return unique


class ReferenceSearchMixin:
    """Searches the local library for claims and builds suggestions/summary text.

    Relies on ``self.ref_manager`` set by ``CitationAssistant``; no class-level annotation
    is declared so ``dir(CitationAssistant)`` is unchanged.
    """

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
        return unique_by_pmid(suggestions)

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
