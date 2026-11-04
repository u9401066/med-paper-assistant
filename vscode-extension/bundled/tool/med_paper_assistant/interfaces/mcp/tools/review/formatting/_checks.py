"""Journal formatting checks (word limits, abstract, references, tables, figures, structure)."""

import re
from typing import Any


def check_word_count_and_abstract(
    all_content: str,
    reqs: dict[str, Any],
    issues: list[dict[str, str]],
    passes: list[str],
) -> None:
    """Checks 1-2: total word count and abstract length."""
    # 1. Word count
    word_count = len(all_content.split())
    word_limit = int(reqs["word_limit"].get("original", 4000))
    if word_count > word_limit:
        issues.append(
            {
                "severity": "error",
                "item": "Word count",
                "detail": f"{word_count} words (limit: {word_limit}, excess: {word_count - word_limit})",
            }
        )
    else:
        passes.append(f"Word count: {word_count}/{word_limit}")

    # 2. Abstract check
    abstract_match = re.search(
        r"(?:^#{1,3}\s*abstract\s*\n)(.*?)(?=\n#{1,3}\s|\Z)",
        all_content,
        re.IGNORECASE | re.DOTALL | re.MULTILINE,
    )
    if abstract_match:
        abstract_text = abstract_match.group(1)
        abstract_words = len(abstract_text.split())
        abstract_limit = int(reqs.get("abstract_limit", 300))
        if abstract_words > abstract_limit:
            issues.append(
                {
                    "severity": "error",
                    "item": "Abstract word count",
                    "detail": f"{abstract_words} words (limit: {abstract_limit})",
                }
            )
        else:
            passes.append(f"Abstract: {abstract_words}/{abstract_limit} words")
    else:
        issues.append(
            {
                "severity": "info",
                "item": "Abstract",
                "detail": "No abstract section detected (may be in a separate file)",
            }
        )


def check_reference_table_figure_counts(
    all_content: str,
    reqs: dict[str, Any],
    issues: list[dict[str, str]],
    passes: list[str],
) -> None:
    """Checks 3-5: reference, table and figure counts."""
    # 3. Reference count
    wikilink_refs = set(re.findall(r"\[\[([^\]]+)\]\]", all_content))
    ref_limit = int(reqs.get("references_limit", 50))
    if len(wikilink_refs) > ref_limit:
        issues.append(
            {
                "severity": "warning",
                "item": "Reference count",
                "detail": f"{len(wikilink_refs)} citations (limit: {ref_limit})",
            }
        )
    else:
        passes.append(f"References: {len(wikilink_refs)}/{ref_limit}")

    # 4. Table count
    table_refs = set(re.findall(r"Table\s+(\d+)", all_content, re.IGNORECASE))
    table_limit = int(reqs.get("tables_limit", 5))
    if len(table_refs) > table_limit:
        issues.append(
            {
                "severity": "warning",
                "item": "Table count",
                "detail": f"{len(table_refs)} tables (limit: {table_limit})",
            }
        )
    else:
        passes.append(f"Tables: {len(table_refs)}/{table_limit}")

    # 5. Figure count
    fig_refs = set(re.findall(r"(?:Figure|Fig\.?)\s+(\d+)", all_content, re.IGNORECASE))
    fig_limit = int(reqs.get("figures_limit", 6))
    if len(fig_refs) > fig_limit:
        issues.append(
            {
                "severity": "warning",
                "item": "Figure count",
                "detail": f"{len(fig_refs)} figures (limit: {fig_limit})",
            }
        )
    else:
        passes.append(f"Figures: {len(fig_refs)}/{fig_limit}")


def check_keywords_and_headings(
    all_content: str,
    reqs: dict[str, Any],
    issues: list[dict[str, str]],
    passes: list[str],
) -> None:
    """Checks 6-7: keywords section and heading hierarchy."""
    # 6. Keywords
    if reqs.get("keywords"):
        has_kw = bool(re.search(r"(?:keywords?|key\s+words)\s*:", all_content, re.IGNORECASE))
        if not has_kw:
            issues.append(
                {
                    "severity": "warning",
                    "item": "Keywords",
                    "detail": f"Not found (required: {reqs['keywords']})",
                }
            )
        else:
            passes.append("Keywords section present")

    # 7. Heading hierarchy
    headings = re.findall(r"^(#{1,6})\s+(.+)", all_content, re.MULTILINE)
    if headings:
        levels = [len(h[0]) for h in headings]
        for i in range(1, len(levels)):
            if levels[i] - levels[i - 1] > 1:
                issues.append(
                    {
                        "severity": "info",
                        "item": "Heading hierarchy",
                        "detail": f"Skipped heading level: {'#' * levels[i - 1]} → {'#' * levels[i]} ('{headings[i][1]}')",
                    }
                )
                break
        else:
            passes.append("Heading hierarchy consistent")


def check_sections_and_characters(
    all_content: str,
    issues: list[dict[str, str]],
) -> None:
    """Checks 8-9: standard sections and unusual Unicode characters."""
    # 8. Required sections check
    content_lower = all_content.lower()
    required_sections = ["introduction", "methods", "results", "discussion"]
    missing_sections = [
        s
        for s in required_sections
        if not re.search(rf"^#{{1,3}}\s+{s}", content_lower, re.MULTILINE)  # fmt: skip
    ]
    if missing_sections:
        issues.append(
            {
                "severity": "info",
                "item": "Standard sections",
                "detail": f"Not detected: {', '.join(s.title() for s in missing_sections)} (may be in separate files)",
            }
        )

    # 9. Special characters / encoding
    non_ascii = re.findall(r"[^\x00-\x7F]", all_content)
    unusual = [c for c in non_ascii if ord(c) > 0x2000 and c not in "–—''…±×÷≤≥≠αβγδ"]
    if unusual:
        issues.append(
            {
                "severity": "info",
                "item": "Special characters",
                "detail": f"Found {len(unusual)} unusual Unicode characters — verify they display correctly",
            }
        )
