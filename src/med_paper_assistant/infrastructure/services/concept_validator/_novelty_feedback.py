"""Reviewer-style novelty feedback (Three Reviewers Model)."""

import re
from typing import Any, Dict, List, Optional

_LIMITATION_PATTERNS = [
    r"\blimitation\b",
    r"\blimited\b",
    r"\bdoes not\b",
    r"\bdid not\b",
    r"\bdo not\b",
    r"\bfail(s|ed|ure)?\b",
    r"\black(s|ing|ed)?\b",
    r"\bour addition\b",
    r"\bwe extend\b",
    r"\bwe (add|include|place|systematically|dedicate)\b",
    r"\bdifferentiation\b",
    r"\bunlike\b",
    r"\bin contrast\b",
    r"\bhowever\b",
    r"\bbut\b",
    r"但",
    r"不同",
    r"限制",
]

_CLINICAL_VAGUE_WORDS = ["improved", "better", "enhanced", "更好", "改善", "提升", "優於"]


def _verdict(avg_score: float) -> str:
    if avg_score >= 85:
        return "💎 High-impact potential. The novelty is clear and well-supported."
    if avg_score >= 75:
        return "✅ Novelty claim is defensible. Proceed to writing."
    if avg_score >= 60:
        return "⚠️ Novelty claim has gaps. A skeptical reviewer would challenge you."
    return "❌ Novelty claim is weak. Current statement would not survive peer review."


def _review_as_skeptic(content: str, content_lower: str, skeptic: Dict[str, Any]) -> None:
    """Reviewer 1: The Skeptic (Focus: Is it REALLY new?)."""
    if ("first" in content_lower or "首次" in content) and "pubmed" not in content_lower:
        skeptic["comment"] = (
            "You claim this is 'first', but provide no search evidence. I am skeptical."
        )
        skeptic["score"] = 50
        skeptic["questions"].append("What was your exact PubMed search strategy and date?")
    else:
        skeptic["comment"] = "The novelty claim seems grounded in existing literature."
        skeptic["score"] = 80


def _review_as_methodologist(content: str, methodologist: Dict[str, Any]) -> None:
    """Reviewer 2: The Methodologist (Focus: How does it compare?)."""
    has_citations = bool(re.search(r"\[\[.+?\]\]", content)) or "PMID" in content
    # Check for limitation/differentiation analysis (multiple patterns)
    has_limitations = sum(1 for p in _LIMITATION_PATTERNS if re.search(p, content, re.IGNORECASE))

    if not has_citations:
        methodologist["comment"] = (
            "You haven't cited the studies you are supposedly improving upon."
        )
        methodologist["score"] = 40
        methodologist["questions"].append(
            "Which specific studies are you comparing your method against?"
        )
    elif has_limitations < 2:
        methodologist["comment"] = (
            "You cited literature but didn't explain their limitations clearly."
        )
        methodologist["score"] = 60
        methodologist["questions"].append(
            "What exactly was the failure or limitation of the cited studies?"
        )
    elif has_limitations < 4:
        methodologist["comment"] = "Some differentiation provided, but could be more systematic."
        methodologist["score"] = 75
        methodologist["questions"].append("Can you provide a structured comparison table?")
    else:
        methodologist["comment"] = "Methodological differentiation is well-articulated."
        methodologist["score"] = 85


def _review_as_clinical_expert(content: str, content_lower: str, clinical: Dict[str, Any]) -> None:
    """Reviewer 3: The Clinical Impact Expert (Focus: So what?)."""
    found_vague = [w for w in _CLINICAL_VAGUE_WORDS if w.lower() in content_lower]
    if found_vague and not re.search(r"\d+%|\d+\s*倍|OR\s*[\d.]|RR\s*[\d.]", content):
        clinical["comment"] = f"You use vague terms like '{found_vague[0]}' without quantification."
        clinical["score"] = 55
        clinical["questions"].append(
            "What is the expected effect size or MCID (Minimal Clinically Important Difference)?"
        )
    else:
        clinical["comment"] = "The clinical significance and expected impact are clear."
        clinical["score"] = 80


def _critical_issues(
    skeptic: Dict[str, Any], clinical: Dict[str, Any], methodologist: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Evidence-based challenges derived from the reviewer scores."""
    issues = []

    # Issue 1: Claiming "first" without search evidence
    if skeptic["score"] <= 50:
        issues.append(
            {
                "problem": "您聲稱『首次』，但沒有提供文獻搜尋證據",
                "challenge": "Reviewer 1 (Skeptic) 會問：『你怎麼知道沒人做過？搜尋策略是什麼？』",
                "fix": '加入：『PubMed 搜尋 "X AND Y" (2024-12-17) 結果為 0 篇』',
            }
        )

    # Issue 2: Vague quantification
    if clinical["score"] <= 60:
        issues.append(
            {
                "problem": "使用模糊用語但沒有量化",
                "challenge": "Reviewer 3 (Clinical Expert) 會問：『好多少？臨床意義 (MCID) 是什麼？』",
                "fix": "改為具體數字：『預期減少 30% 的併發症』或『優於現有技術 15%』",
            }
        )

    # Issue 3: Comparison gap
    if methodologist["score"] <= 60:
        issues.append(
            {
                "problem": "未明確說明與現有研究的差異",
                "challenge": "Reviewer 2 (Methodologist) 會問：『既然 [Author 2024] 做過類似的，你的獨特性在哪？』",
                "fix": "明確寫出：『與 [Author 2024] 不同的是，我們採用了 [新方法/新族群]』",
            }
        )

    return issues


def _cgu_recommendation(content: str, avg_score: float) -> Optional[Dict[str, Any]]:
    """Suggest CGU stress-testing when the average score is below the threshold."""
    if avg_score < 75:
        return {
            "recommend": True,
            "reason": "目前的創新點在審稿人眼中仍有漏洞。建議使用 CGU 進行壓力測試。",
            "tool": "cgu_diverge(action=anti_typical) + cgu_judge",
            "prompt": f"扮演一位頂尖醫學期刊審稿人，針對以下創新聲明提出 3 個最刁鑽的質疑：\n\n{content}",
        }
    return None


class NoveltyFeedbackMixin:
    """Sharp reviewer-style feedback on a novelty statement."""

    def _generate_novelty_feedback(self, content: str, scores: List[int]) -> Dict[str, Any]:
        """
        Generate sharp, reviewer-style feedback using the Three Reviewers Model.

        1. Reviewer 1: The Skeptic (Evidence & Search)
        2. Reviewer 2: The Methodologist (Rigor & Comparison)
        3. Reviewer 3: The Clinical Impact Expert (Significance & MCID)
        """
        feedback: dict[str, Any] = {
            "verdict": "",
            "reviewers": {
                "skeptic": {"comment": "", "score": 0, "questions": []},
                "methodologist": {"comment": "", "score": 0, "questions": []},
                "clinical_expert": {"comment": "", "score": 0, "questions": []},
            },
            "critical_issues": [],
            "actionable_fixes": [],
            "cgu_recommendation": None,
        }

        content_lower = content.lower()
        avg_score = sum(scores) / len(scores)

        # === VERDICT ===
        feedback["verdict"] = _verdict(avg_score)

        skeptic = feedback["reviewers"]["skeptic"]
        _review_as_skeptic(content, content_lower, skeptic)
        methodologist = feedback["reviewers"]["methodologist"]
        _review_as_methodologist(content, methodologist)
        clinical = feedback["reviewers"]["clinical_expert"]
        _review_as_clinical_expert(content, content_lower, clinical)

        # === CRITICAL ISSUES (Evidence-based challenges) ===
        issues = _critical_issues(skeptic, clinical, methodologist)
        feedback["critical_issues"] = issues

        # === ACTIONABLE FIXES ===
        fixes = []
        for issue in issues:
            fixes.append(f"🔧 **{issue['problem']}**\n   → {issue['fix']}")
        feedback["actionable_fixes"] = fixes

        # === CGU RECOMMENDATION ===
        feedback["cgu_recommendation"] = _cgu_recommendation(content, avg_score)

        return feedback

    def _generate_novelty_suggestions(self, content: str, scores: List[int]) -> List[str]:
        """Generate improvement suggestions (legacy interface, calls new method)."""
        feedback = self._generate_novelty_feedback(content, scores)
        suggestions = []
        for fix in feedback.get("actionable_fixes", []):
            suggestions.append(fix)
        return suggestions
