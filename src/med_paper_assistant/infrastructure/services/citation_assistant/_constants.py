"""Rule table and stopwords for rule-based claim detection."""

import re
from typing import NamedTuple

from ._models import ClaimType

# 已有引用的句子（[[wikilink]]、[PMID:x]、[1] / (1)）不再需要引用
EXISTING_CITATION_PATTERN = re.compile(r"\[\[|\[PMID:|[\(\[]\d+[\)\]]")


class ClaimRule(NamedTuple):
    """One detection rule; rules are tried in order and the first match wins."""

    pattern: re.Pattern[str]
    claim_type: ClaimType
    reason: str
    search_suffix: str


CLAIM_RULES: tuple[ClaimRule, ...] = (
    # 統計數據模式
    ClaimRule(
        re.compile(
            r"\d+\.?\d*\s*%|\d+/\d+|發生率|死亡率|盛行率|prevalence|incidence|mortality",
        ),
        ClaimType.STATISTICAL,
        "Statistical claim requires source",
        "epidemiology",
    ),
    # 比較聲稱
    ClaimRule(
        re.compile(
            r"比.*更|優於|劣於|better|worse|superior|inferior|compared to|versus|vs\.?",
        ),
        ClaimType.COMPARISON,
        "Comparison claim requires evidence",
        "comparison",
    ),
    # 指引/共識
    ClaimRule(
        re.compile(r"guideline|指引|建議|recommends?|consensus|共識"),
        ClaimType.GUIDELINE,
        "Guideline reference required",
        "guideline",
    ),
    # 機制說明
    ClaimRule(
        re.compile(r"透過|藉由|mechanism|through|via|pathway|mediated"),
        ClaimType.MECHANISM,
        "Mechanism claim needs supporting evidence",
        "mechanism",
    ),
    # 研究顯示類
    ClaimRule(
        re.compile(
            r"studies?|research|研究|報告|report|evidence|suggests?|shows?|demonstrates?",
        ),
        ClaimType.GENERAL,
        "Claim about studies needs citation",
        "",
    ),
    # 定義
    ClaimRule(
        re.compile(r"定義為|defined as|is defined|refers to"),
        ClaimType.DEFINITION,
        "Definition should be cited",
        "definition",
    ),
)

# 移除常見停用詞
STOPWORDS = frozenset(
    {
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
)
