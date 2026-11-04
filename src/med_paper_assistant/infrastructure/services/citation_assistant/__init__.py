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

from ._core import CitationAssistant
from ._models import CitationAnalysisResult, CitationSuggestion, ClaimType, TextClaim

__all__ = [
    "CitationAnalysisResult",
    "CitationAssistant",
    "CitationSuggestion",
    "ClaimType",
    "TextClaim",
]
