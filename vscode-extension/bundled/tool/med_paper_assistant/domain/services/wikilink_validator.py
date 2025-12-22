"""
Wikilink Validator and Auto-Fixer

驗證和自動修復 markdown 文件中的 wikilink 格式。

正確格式：[[author2024_12345678]]
錯誤格式：
- [[12345678]] - 缺少 author_year 前綴
- Author 2024 [[12345678]] - 格式混亂
- [[PMID:12345678]] - 舊格式（可接受但建議轉換）
"""

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class WikilinkIssue:
    """代表一個 wikilink 格式問題"""

    line_number: int
    original: str
    issue_type: str  # "missing_prefix", "wrong_format", "not_found", "old_format"
    suggestion: Optional[str] = None
    context: str = ""  # 周圍文字


@dataclass
class WikilinkValidationResult:
    """Wikilink 驗證結果"""

    is_valid: bool
    total_wikilinks: int
    valid_count: int
    issues: List[WikilinkIssue] = field(default_factory=list)
    auto_fixed: int = 0

    def to_report(self) -> str:
        """生成人類可讀的報告"""
        if self.is_valid and not self.issues:
            return f"✅ 所有 {self.total_wikilinks} 個 wikilinks 格式正確"

        lines = [
            "⚠️ **Wikilink 格式檢查結果**",
            "",
            f"- 總數: {self.total_wikilinks}",
            f"- 正確: {self.valid_count}",
            f"- 問題: {len(self.issues)}",
        ]

        if self.auto_fixed > 0:
            lines.append(f"- 自動修復: {self.auto_fixed}")

        if self.issues:
            lines.append("")
            lines.append("| 行號 | 原始 | 問題類型 | 建議 |")
            lines.append("|------|------|----------|------|")
            for issue in self.issues:
                suggestion = issue.suggestion or "-"
                lines.append(
                    f"| {issue.line_number} | `{issue.original}` | {issue.issue_type} | `{suggestion}` |"
                )

        return "\n".join(lines)


# 正確的 wikilink 格式: [[author2024_12345678]]
VALID_WIKILINK_PATTERN = re.compile(
    r"\[\[([a-z]+\d{4}_\d{7,8})\]\]",  # author2024_12345678
    re.IGNORECASE,
)

# 所有 wikilink 模式（包含錯誤格式）
ALL_WIKILINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")

# PMID only 模式: [[12345678]] 或 [[PMID:12345678]]
PMID_ONLY_PATTERN = re.compile(r"\[\[(PMID:)?(\d{7,8})\]\]", re.IGNORECASE)

# 混亂格式: Author 2024 [[12345678]]
MESSY_FORMAT_PATTERN = re.compile(r"([A-Z][a-z]+)\s*(\d{4})\s*\[\[(\d{7,8})\]\]", re.IGNORECASE)


def validate_wikilink(wikilink: str) -> Tuple[bool, str]:
    """
    驗證單個 wikilink 格式

    Args:
        wikilink: 包含 [[ ]] 的完整 wikilink

    Returns:
        (is_valid, issue_type)
    """
    # 檢查是否是正確格式
    if VALID_WIKILINK_PATTERN.match(wikilink):
        return True, ""

    # 檢查是否是 PMID only
    if PMID_ONLY_PATTERN.match(wikilink):
        return False, "missing_prefix"

    # 其他錯誤格式
    return False, "wrong_format"


def find_citation_key_for_pmid(pmid: str, references_dir: str) -> Optional[str]:
    """
    根據 PMID 查找對應的 citation_key

    Args:
        pmid: PubMed ID (純數字)
        references_dir: references 目錄路徑

    Returns:
        citation_key (如 "author2024_12345678") 或 None
    """
    if not os.path.exists(references_dir):
        return None

    # 查找以 PMID 結尾的目錄
    for item in os.listdir(references_dir):
        item_path = os.path.join(references_dir, item)
        if os.path.isdir(item_path) and item.endswith(f"_{pmid}"):
            return item
        # 也檢查純 PMID 目錄
        if os.path.isdir(item_path) and item == pmid:
            # 讀取 metadata 取得正確的 citation_key
            metadata_file = os.path.join(item_path, "metadata.json")
            if os.path.exists(metadata_file):
                import json

                try:
                    with open(metadata_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                        return metadata.get("citation_key", item)
                except Exception:  # nosec B110 - intentional fallback to original value
                    pass
            return item

    # 也查找 .md 檔案
    for item in os.listdir(references_dir):
        if item.endswith(f"_{pmid}.md"):
            return item.replace(".md", "")

    return None


def validate_wikilinks_in_content(
    content: str, references_dir: Optional[str] = None, auto_fix: bool = False
) -> Tuple[WikilinkValidationResult, str]:
    """
    驗證內容中的所有 wikilinks

    Args:
        content: Markdown 內容
        references_dir: references 目錄路徑（用於查找正確的 citation_key）
        auto_fix: 是否自動修復可修復的問題

    Returns:
        (WikilinkValidationResult, fixed_content)
    """
    issues = []
    fixed_content = content
    auto_fixed_count = 0

    lines = content.split("\n")
    all_wikilinks = []
    valid_count = 0

    for line_num, line in enumerate(lines, 1):
        # 先檢查混亂格式: Author 2024 [[12345678]]
        for match in MESSY_FORMAT_PATTERN.finditer(line):
            author = match.group(1).lower()
            year = match.group(2)
            pmid = match.group(3)
            original = match.group(0)

            # 嘗試查找正確的 citation_key
            suggested = None
            if references_dir:
                suggested = find_citation_key_for_pmid(pmid, references_dir)

            if not suggested:
                suggested = f"{author}{year}_{pmid}"

            issue = WikilinkIssue(
                line_number=line_num,
                original=original,
                issue_type="messy_format",
                suggestion=f"[[{suggested}]]",
                context=line.strip()[:50],
            )
            issues.append(issue)
            all_wikilinks.append(original)

            if auto_fix:
                fixed_content = fixed_content.replace(original, f"[[{suggested}]]", 1)
                auto_fixed_count += 1

        # 檢查標準 wikilinks
        for match in ALL_WIKILINK_PATTERN.finditer(line):
            wikilink = match.group(0)
            match.group(1)

            # 跳過已處理的混亂格式
            if any(wikilink in issue.original for issue in issues):
                continue

            all_wikilinks.append(wikilink)

            is_valid, issue_type = validate_wikilink(wikilink)

            if is_valid:
                valid_count += 1
                continue

            # 處理錯誤格式
            suggested = None

            if issue_type == "missing_prefix":
                # 提取 PMID
                pmid_match = PMID_ONLY_PATTERN.match(wikilink)
                if pmid_match:
                    pmid = pmid_match.group(2)
                    if references_dir:
                        suggested = find_citation_key_for_pmid(pmid, references_dir)
                    if suggested:
                        suggested = f"[[{suggested}]]"

            issue = WikilinkIssue(
                line_number=line_num,
                original=wikilink,
                issue_type=issue_type,
                suggestion=suggested,
                context=line.strip()[:50],
            )
            issues.append(issue)

            if auto_fix and suggested:
                fixed_content = fixed_content.replace(wikilink, suggested, 1)
                auto_fixed_count += 1

    result = WikilinkValidationResult(
        is_valid=len(issues) == 0,
        total_wikilinks=len(all_wikilinks),
        valid_count=valid_count,
        issues=issues,
        auto_fixed=auto_fixed_count,
    )

    return result, fixed_content


def validate_wikilinks_in_file(
    filepath: str,
    references_dir: Optional[str] = None,
    auto_fix: bool = False,
    save_if_fixed: bool = True,
) -> WikilinkValidationResult:
    """
    驗證檔案中的 wikilinks

    Args:
        filepath: Markdown 檔案路徑
        references_dir: references 目錄路徑
        auto_fix: 是否自動修復
        save_if_fixed: 修復後是否儲存

    Returns:
        WikilinkValidationResult
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    result, fixed_content = validate_wikilinks_in_content(content, references_dir, auto_fix)

    if auto_fix and save_if_fixed and result.auto_fixed > 0:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(fixed_content)

    return result
