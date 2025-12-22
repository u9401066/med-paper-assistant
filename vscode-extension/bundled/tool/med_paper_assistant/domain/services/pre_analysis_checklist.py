"""
Pre-Analysis Checklist Service

驗證 concept.md 是否已準備好進入數據分析階段。
檢查所有必要區塊是否已填寫，並提供缺漏建議。

依據 CONSTITUTION 第八章，Agent 必須在開始分析前確認 checklist。
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class CheckStatus(Enum):
    """檢查狀態"""

    PASSED = "✅"
    FAILED = "❌"
    WARNING = "⚠️"
    SKIPPED = "⏭️"


@dataclass
class CheckItem:
    """單一檢查項目"""

    name: str
    status: CheckStatus
    message: str
    suggestion: Optional[str] = None


@dataclass
class ChecklistResult:
    """Checklist 檢查結果"""

    ready_for_analysis: bool
    score: int  # 0-100
    total_checks: int
    passed_checks: int
    failed_checks: int
    warning_checks: int
    items: list[CheckItem] = field(default_factory=list)

    def to_markdown(self) -> str:
        """轉換為 Markdown 報告"""
        lines = [
            "# 📋 Pre-Analysis Checklist Report",
            "",
            f"**Status**: {'✅ Ready for Analysis' if self.ready_for_analysis else '❌ Not Ready'}",
            f"**Score**: {self.score}/100",
            f"**Passed**: {self.passed_checks}/{self.total_checks}",
            "",
            "## Check Items",
            "",
            "| Status | Item | Message |",
            "|--------|------|---------|",
        ]

        for item in self.items:
            lines.append(f"| {item.status.value} | {item.name} | {item.message} |")

        # 加入建議
        suggestions = [item for item in self.items if item.suggestion]
        if suggestions:
            lines.extend(
                [
                    "",
                    "## 💡 Suggestions",
                    "",
                ]
            )
            for item in suggestions:
                lines.append(f"- **{item.name}**: {item.suggestion}")

        return "\n".join(lines)


class PreAnalysisChecker:
    """Pre-Analysis Checklist 檢查器"""

    # 必要區塊 (must pass)
    REQUIRED_SECTIONS = {
        "NOVELTY STATEMENT": {
            "pattern": r"##\s*🔒?\s*NOVELTY STATEMENT",
            "content_check": r"What is new\?.*?>.+",
            "suggestion": "填寫研究的創新點，說明這是「首次」做什麼",
        },
        "KEY SELLING POINTS": {
            "pattern": r"##\s*🔒?\s*KEY SELLING POINTS",
            "content_check": r"1\.\s*\*\*.+\*\*",
            "suggestion": "列出 3-5 個核心賣點，每個都要有文獻支持",
        },
        "Study Design": {
            "pattern": r"##\s*📝?\s*Study Design",
            "content_check": r"Design Type.*?:\s*\[?(RCT|Cohort|Cross-sectional|Case-control|Retrospective)",
            "suggestion": "選擇研究設計類型：RCT, Retrospective Cohort, Cross-sectional 等",
        },
        "Participants": {
            "pattern": r"##\s*📝?\s*Participants",
            "content_check": r"Inclusion Criteria.*?-\s*\S+",
            "suggestion": "定義納入/排除條件",
        },
        "Sample Size": {
            "pattern": r"Sample Size",
            "content_check": r"Target N.*?:\s*\d+",
            "suggestion": "計算樣本數，需要預期發生率和 power",
        },
        "Outcomes": {
            "pattern": r"##\s*📝?\s*Outcomes",
            "content_check": r"Primary Outcome.*?Variable.*?:\s*\S+",
            "suggestion": "定義主要和次要結果指標的操作型定義",
        },
    }

    # 建議區塊 (warning if missing)
    RECOMMENDED_SECTIONS = {
        "Statistical Analysis": {
            "pattern": r"##\s*📝?\s*Statistical Analysis",
            "content_check": r"Primary Analysis.*?>.+",
            "suggestion": "描述主要統計分析方法",
        },
        "Ethical Considerations": {
            "pattern": r"##\s*📝?\s*Ethical Considerations",
            "content_check": r"IRB Approval.*?:\s*\[?\w+",
            "suggestion": "填寫 IRB 審查狀態",
        },
        "Target Journal": {
            "pattern": r"##\s*📝?\s*Target Journal",
            "content_check": r"Journal Name.*?:\s*\[?[A-Z]",
            "suggestion": "選擇目標期刊以確定格式要求",
        },
    }

    def check_concept(self, content: str) -> ChecklistResult:
        """
        檢查 concept.md 內容的完整度

        Args:
            content: concept.md 的完整內容

        Returns:
            ChecklistResult 包含所有檢查結果
        """
        items = []
        passed = 0
        failed = 0
        warnings = 0

        # 檢查必要區塊
        for name, config in self.REQUIRED_SECTIONS.items():
            item = self._check_section(content, name, config, required=True)
            items.append(item)
            if item.status == CheckStatus.PASSED:
                passed += 1
            else:
                failed += 1

        # 檢查建議區塊
        for name, config in self.RECOMMENDED_SECTIONS.items():
            item = self._check_section(content, name, config, required=False)
            items.append(item)
            if item.status == CheckStatus.PASSED:
                passed += 1
            elif item.status == CheckStatus.WARNING:
                warnings += 1

        # 計算分數
        total = len(self.REQUIRED_SECTIONS) + len(self.RECOMMENDED_SECTIONS)
        # 必要項目權重 70%，建議項目權重 30%
        required_score = (
            (passed / len(self.REQUIRED_SECTIONS)) * 70
            if failed < len(self.REQUIRED_SECTIONS)
            else 0
        )
        optional_passed = passed - (len(self.REQUIRED_SECTIONS) - failed)
        optional_score = (
            (optional_passed / len(self.RECOMMENDED_SECTIONS)) * 30
            if len(self.RECOMMENDED_SECTIONS) > 0
            else 0
        )

        score = int(required_score + optional_score)
        ready = failed == 0  # 所有必要項目都通過才算 ready

        return ChecklistResult(
            ready_for_analysis=ready,
            score=score,
            total_checks=total,
            passed_checks=passed,
            failed_checks=failed,
            warning_checks=warnings,
            items=items,
        )

    def _check_section(self, content: str, name: str, config: dict, required: bool) -> CheckItem:
        """檢查單一區塊"""
        pattern = config["pattern"]
        content_check = config.get("content_check")
        suggestion = config.get("suggestion")

        # 檢查區塊是否存在
        if not re.search(pattern, content, re.IGNORECASE):
            return CheckItem(
                name=name,
                status=CheckStatus.FAILED if required else CheckStatus.WARNING,
                message="Section not found",
                suggestion=suggestion,
            )

        # 檢查內容是否已填寫
        if content_check:
            if re.search(content_check, content, re.IGNORECASE | re.DOTALL):
                return CheckItem(
                    name=name,
                    status=CheckStatus.PASSED,
                    message="Completed",
                )
            else:
                return CheckItem(
                    name=name,
                    status=CheckStatus.FAILED if required else CheckStatus.WARNING,
                    message="Section exists but content not filled",
                    suggestion=suggestion,
                )

        return CheckItem(
            name=name,
            status=CheckStatus.PASSED,
            message="Section exists",
        )

    def check_file(self, file_path: Path) -> ChecklistResult:
        """
        檢查 concept.md 檔案

        Args:
            file_path: concept.md 檔案路徑

        Returns:
            ChecklistResult
        """
        if not file_path.exists():
            return ChecklistResult(
                ready_for_analysis=False,
                score=0,
                total_checks=len(self.REQUIRED_SECTIONS) + len(self.RECOMMENDED_SECTIONS),
                passed_checks=0,
                failed_checks=len(self.REQUIRED_SECTIONS),
                warning_checks=len(self.RECOMMENDED_SECTIONS),
                items=[
                    CheckItem(
                        name="concept.md",
                        status=CheckStatus.FAILED,
                        message="File not found",
                        suggestion="Run concept-development skill first",
                    )
                ],
            )

        content = file_path.read_text(encoding="utf-8")
        return self.check_concept(content)


# 單例 instance
_checker = PreAnalysisChecker()


def check_pre_analysis_readiness(content: str) -> ChecklistResult:
    """
    檢查 concept.md 是否已準備好進入分析階段

    Args:
        content: concept.md 內容

    Returns:
        ChecklistResult 包含完整檢查報告
    """
    return _checker.check_concept(content)


def check_pre_analysis_file(file_path: Path) -> ChecklistResult:
    """
    檢查 concept.md 檔案是否已準備好

    Args:
        file_path: concept.md 路徑

    Returns:
        ChecklistResult
    """
    return _checker.check_file(file_path)
