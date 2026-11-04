"""Human-readable validation report rendering."""

import os
from typing import Any, Dict, List

from ._models import SectionCheck, ValidationResult
from ._novelty_feedback import NoveltyFeedbackMixin


def _header_lines(result: ValidationResult) -> List[str]:
    output = []
    output.append("📋 **Concept Validation Report**")
    output.append(f"📄 File: `{os.path.basename(result.file_path)}`")
    output.append(f"📝 Paper Type: `{result.paper_type}`")
    if result.target_section:
        output.append(f"🎯 Target Section: `{result.target_section}`")
    output.append(f"🕐 Time: {result.timestamp}")
    output.append("")
    return output


def _section_specific_lines(result: ValidationResult) -> List[str]:
    """Section-specific validation info."""
    output: List[str] = []
    if not result.target_section:
        return output

    output.append("## 📌 Section-Specific Validation")
    output.append("")
    output.append(f"Validating requirements for writing **{result.target_section}**:")
    output.append("")

    if result.missing_required:
        output.append("**❌ Missing Required:**")
        for req in result.missing_required:
            output.append(f"- {req}")
        output.append("")

    if result.missing_recommended:
        output.append("**📝 Missing Recommended (non-blocking):**")
        for rec in result.missing_recommended:
            output.append(f"- {rec}")
        output.append("")
    return output


def _structure_table_lines(result: ValidationResult) -> List[str]:
    """Structural validation tables (protected and editable sections)."""
    output: List[str] = []
    output.append("## 🔒 Protected Sections (Required)")
    output.append("")
    output.append("| Section | Found | Has Content | Status |")
    output.append("|---------|-------|-------------|--------|")

    for key in ["novelty_statement", "selling_points"]:
        if key in result.sections:
            check = result.sections[key]
            found = "✅" if check.found else "❌"
            has_content = "✅" if check.has_content else "❌"
            status = "✅ PASS" if check.found and check.has_content else "❌ MISSING"
            output.append(f"| {check.name} | {found} | {has_content} | {status} |")

    output.append("")
    output.append("## 📝 Editable Sections (Optional)")
    output.append("")
    output.append("| Section | Found | Has Content |")
    output.append("|---------|-------|-------------|")

    for key in [
        "background",
        "research_gap",
        "research_question",
        "methods",
        "expected_outcomes",
    ]:
        if key in result.sections:
            check = result.sections[key]
            found = "✅" if check.found else "⚪"
            has_content = "✅" if check.has_content else "⚪"
            output.append(f"| {check.name} | {found} | {has_content} |")
    return output


def _reviewer_panel_lines(feedback: Dict[str, Any]) -> List[str]:
    """Three reviewers' scores table."""
    output: List[str] = []
    output.append("### 👥 Reviewer Panel")
    output.append("")
    output.append("| Reviewer | Score | Feedback |")
    output.append("|----------|-------|----------|")

    revs = feedback["reviewers"]
    output.append(
        f"| 🕵️ **The Skeptic** | {revs['skeptic']['score']} | {revs['skeptic']['comment']} |"
    )
    output.append(
        f"| 📐 **The Methodologist** | {revs['methodologist']['score']} | {revs['methodologist']['comment']} |"
    )
    output.append(
        f"| 🏥 **The Clinical Expert** | {revs['clinical_expert']['score']} | {revs['clinical_expert']['comment']} |"
    )
    output.append("")
    return output


def _critical_issue_lines(feedback: Dict[str, Any]) -> List[str]:
    """Sharp, evidence-based critical issues."""
    output: List[str] = []
    output.append("### ⚠️ Critical Issues (Reviewer 會質疑)")
    output.append("")
    for issue in feedback["critical_issues"]:
        output.append(f"**❌ {issue['problem']}**")
        output.append(f"- 🎯 {issue['challenge']}")
        output.append(f"- 🔧 {issue['fix']}")
        output.append("")
    return output


def _reviewer_question_lines(feedback: Dict[str, Any]) -> List[str]:
    """Questions the reviewers would ask."""
    output: List[str] = []
    reviewer_questions = []
    if "reviewers" in feedback:
        for r in feedback["reviewers"].values():
            reviewer_questions.extend(r.get("questions", []))

    if reviewer_questions:
        output.append("### ❓ Reviewer 會問的問題")
        output.append("")
        for q in reviewer_questions:
            output.append(f"- {q}")
        output.append("")
    return output


def _cgu_lines(feedback: Dict[str, Any], avg_score: float) -> List[str]:
    """CGU recommendation (if needed)."""
    output: List[str] = []
    cgu = feedback.get("cgu_recommendation") or {}
    if cgu.get("recommend") and avg_score < 75:
        output.append("### 🤖 需要 CGU 幫忙嗎？")
        output.append("")
        output.append(f"> **工具：** `{cgu.get('tool', 'cgu_judge')}`")
        output.append(f"> **原因：** {cgu.get('reason', '')}")
        if cgu.get("prompt"):
            output.append(f"> **Prompt：** {cgu['prompt']}")
        output.append("")
    return output


def _consistency_lines(result: ValidationResult) -> List[str]:
    output: List[str] = []
    output.append("")
    output.append("## 🔗 Consistency Check")
    output.append("")
    status = "✅ PASSED" if result.consistency_passed else "⚠️ ISSUES"
    output.append(f"**Status:** {status} (Score: {result.consistency_score}/100)")
    if result.consistency_issues:
        output.append("")
        output.append("**Issues:**")
        for issue in result.consistency_issues:
            output.append(f"- {issue}")
    return output


def _issue_list_lines(result: ValidationResult) -> List[str]:
    """Errors, warnings and suggestions."""
    output: List[str] = []
    if result.errors:
        output.append("")
        output.append("## ❌ Errors")
        for error in result.errors:
            output.append(f"- {error}")

    if result.warnings:
        output.append("")
        output.append("## ⚠️ Warnings")
        for warning in result.warnings:
            output.append(f"- {warning}")

    if result.suggestions:
        output.append("")
        output.append("## 💡 Suggestions")
        for suggestion in result.suggestions:
            output.append(f"- {suggestion}")
    return output


def _target_section_verdict_lines(result: ValidationResult) -> List[str]:
    output: List[str] = []
    if result.can_write_section:
        output.append(f"## ✅ CAN WRITE {result.target_section.upper()}")
        output.append("")
        output.append(f"All required sections for **{result.target_section}** are present.")
        if result.missing_recommended:
            output.append("")
            output.append(
                "💡 **Tip:** Consider filling in the recommended sections for a stronger paper."
            )
    else:
        output.append(f"## ⚠️ MISSING SECTIONS FOR {result.target_section.upper()}")
        output.append("")
        output.append(f"Missing required sections for **{result.target_section}**.")
        output.append("Please fill in the missing sections first.")
    return output


def _passed_verdict_lines() -> List[str]:
    output: List[str] = []
    output.append("## ✅ VALIDATION PASSED")
    output.append("")
    output.append("The concept file meets all requirements.")
    output.append("You may proceed with `/mdpaper.draft` to write the paper.")
    output.append("")
    output.append("**Remember:**")
    output.append("- 🔒 Protected content must be preserved in the final paper")
    output.append("- Ask user before modifying any 🔒 sections")
    return output


def _assessment_summary_lines(result: ValidationResult) -> List[str]:
    """Sharp summary with clear options."""
    output: List[str] = []
    output.append("## 📋 Assessment Summary")
    output.append("")

    output.append(f"**Novelty Score:** {result.novelty_average:.1f}/100")
    output.append("")

    if result.novelty_average >= 60:
        output.append("您的 concept 可以過關，但有可改進之處。")
    else:
        output.append("⚠️ 目前的 novelty statement 可能無法通過 peer review。")
    output.append("")
    output.append("**您的選擇：**")
    output.append("")
    output.append("| 選項 | 行動 |")
    output.append("|------|------|")
    output.append("| ✅ 直接寫 | 『直接寫』- 我立即開始 |")
    output.append("| 🔧 修正問題 | 『幫我改 [問題]』- 我一次只改一點 |")
    output.append("| 🤖 CGU 發想 | 『用 CGU 想想』- 從 reviewer 角度找弱點 |")
    output.append("")
    output.append("> 💬 您決定，我執行。我不會自動修改 concept。")
    return output


def _final_verdict_lines(result: ValidationResult) -> List[str]:
    output: List[str] = []
    output.append("")
    output.append("---")
    output.append("")

    if result.target_section:
        output.extend(_target_section_verdict_lines(result))
    elif result.overall_passed:
        output.extend(_passed_verdict_lines())
    else:
        output.extend(_assessment_summary_lines(result))
    return output


class ReportMixin(NoveltyFeedbackMixin):
    """Markdown report for a ValidationResult."""

    def generate_report(self, result: ValidationResult) -> str:
        """Generate a human-readable validation report."""
        output: List[str] = []
        output.extend(_header_lines(result))
        output.extend(_section_specific_lines(result))
        output.extend(_structure_table_lines(result))

        if result.novelty_checked:
            output.extend(self._novelty_report_lines(result))

        if result.consistency_checked:
            output.extend(_consistency_lines(result))

        output.extend(_issue_list_lines(result))
        output.extend(_final_verdict_lines(result))

        return "\n".join(output)

    def _novelty_report_lines(self, result: ValidationResult) -> List[str]:
        """Novelty evaluation block (Three Reviewers Model)."""
        output: List[str] = []
        output.append("")
        output.append("## 🎯 Novelty Evaluation (Three Reviewers Model)")
        output.append("")

        # Get detailed feedback first
        novelty_content = result.sections.get(
            "novelty_statement", SectionCheck(name="", found=False, has_content=False)
        ).content

        feedback: Dict[str, Any] = {}
        if novelty_content:
            feedback = self._generate_novelty_feedback(novelty_content, result.novelty_scores)

        # Show verdict (one sharp line)
        avg_score = result.novelty_average
        output.append(f"**Overall Score:** {avg_score:.1f}/100")
        if feedback.get("verdict"):
            output.append(f"**Verdict:** {feedback['verdict']}")
        output.append("")

        if "reviewers" in feedback:
            output.extend(_reviewer_panel_lines(feedback))

        if feedback.get("critical_issues"):
            output.extend(_critical_issue_lines(feedback))

        output.extend(_reviewer_question_lines(feedback))
        output.extend(_cgu_lines(feedback, avg_score))

        # Note: This is advisory, not blocking
        output.append("> 📌 **這是 reviewer 視角的建議，不是硬性門檻。**")
        output.append("> 您可以選擇：(1) 直接寫 (2) 補強後再寫 (3) 用 CGU 發想")
        output.append("")
        return output
