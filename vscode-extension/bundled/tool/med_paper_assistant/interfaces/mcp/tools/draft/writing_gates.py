"""
Draft Writing Gates

Project/workflow guard, concept validation gate, reference sufficiency gate
and writing-order advisory shared by the draft writing tools.
"""

import os
import re
from pathlib import Path
from typing import Any, Optional

from med_paper_assistant.domain.paper_types import check_writing_prerequisites
from med_paper_assistant.infrastructure.persistence.writing_hooks._constants import (
    DEFAULT_MIN_REFERENCES,
    DEFAULT_MINIMUM_REFERENCES,
)
from med_paper_assistant.infrastructure.services.concept_validator import ConceptValidator

from .._shared import (
    get_concept_path,
    log_tool_result,
)

# Global validator instance
_concept_validator = ConceptValidator()

_NO_CONCEPT_MESSAGE = (
    "❌ **VALIDATION REQUIRED**\n\n"
    "No concept.md found for current project.\n"
    "You must create and validate a concept file first:\n\n"
    "1. Use `/mdpaper.concept` to develop your research concept\n"
    "2. Fill in 🔒 NOVELTY STATEMENT\n"
    "3. Fill in 🔒 KEY SELLING POINTS (at least 3)\n"
    "4. Run `validate_concept` to verify\n\n"
    "Draft writing is blocked until concept.md exists."
)


def _missing_section_message(novelty_section: Any, selling_section: Any) -> Optional[str]:
    if not novelty_section or not novelty_section.has_content:
        return (
            "❌ **MISSING REQUIRED SECTION**\n\n"
            "🔒 NOVELTY STATEMENT is empty.\n"
            "Please fill in your research novelty before writing drafts."
        )

    if not selling_section or not selling_section.has_content:
        return (
            "❌ **MISSING REQUIRED SECTION**\n\n"
            "🔒 KEY SELLING POINTS is empty.\n"
            "Please add at least 3 key selling points before writing drafts."
        )
    return None


def _novelty_outcome(novelty_average: float, protected_content: dict) -> tuple:
    # Novelty score is ADVISORY, not blocking
    if novelty_average < 75:
        return (
            True,  # Allow proceeding!
            f"💡 Novelty score: {novelty_average:.1f}/100 (reference: 75)\n"
            f"這是參考指標，您可以選擇直接寫或補充後再寫。",
            protected_content,
        )

    return (
        True,
        f"✅ Concept validation passed (Novelty score: {novelty_average:.1f}/100)",
        protected_content,
    )


def _enforce_concept_validation(require_novelty: bool = True) -> tuple:
    """
    Check concept validation status (advisory, not blocking).

    Returns:
        Tuple of (can_proceed: bool, message: str, protected_content: dict)

    Note: Novelty score is advisory. Low score returns warning, not block.
    """
    concept_path = get_concept_path()

    if not concept_path or not os.path.exists(concept_path):
        return (False, _NO_CONCEPT_MESSAGE, {})

    result = _concept_validator.validate(
        concept_path,
        run_novelty_check=require_novelty,
        run_consistency_check=True,
        force_refresh=False,
    )

    # Extract protected content regardless of score
    novelty_section = result.sections.get("novelty_statement")
    selling_section = result.sections.get("selling_points")

    protected_content = {
        "novelty_statement": novelty_section.content if novelty_section else "",
        "selling_points": selling_section.content if selling_section else "",
        "novelty_score": result.novelty_average,
    }

    # Check structural requirements (these ARE blocking)
    missing_message = _missing_section_message(novelty_section, selling_section)
    if missing_message is not None:
        return (False, missing_message, {})

    return _novelty_outcome(result.novelty_average, protected_content)


def _count_saved_references(project_dir: Path) -> int:
    """Count references (same logic as A7 hook and pipeline gate)."""
    refs_dir = project_dir / "references"
    ref_count = 0
    if refs_dir.is_dir():
        ref_count = len(list(refs_dir.glob("*/metadata.json")))
        if ref_count == 0:
            ref_count = len(list(refs_dir.glob("*.md")))
    return ref_count


def _minimum_references(project_dir: Path, paper_type: str) -> tuple[str, int]:
    """Resolve (paper type, minimum references), honouring journal-profile.yaml."""
    min_refs = None
    jp_path = project_dir / "journal-profile.yaml"
    if jp_path.is_file():
        try:
            import yaml

            with open(jp_path, encoding="utf-8") as f:
                profile = yaml.safe_load(f) or {}
            paper_type_from_profile = profile.get("paper", {}).get("type")
            if paper_type_from_profile:
                paper_type = paper_type_from_profile
            min_limits = profile.get("references", {}).get("minimum_reference_limits", {})
            if isinstance(min_limits, dict):
                val = min_limits.get(paper_type)
                if val is not None:
                    min_refs = int(val)
        except Exception:  # nosec B110 - fallback to defaults below
            pass

    if min_refs is None:
        min_refs = DEFAULT_MINIMUM_REFERENCES.get(paper_type, DEFAULT_MIN_REFERENCES)
    return paper_type, min_refs


def _concept_topic_hint() -> str:
    """Extract research topic from concept.md for search query suggestion."""
    topic_hint = ""
    concept_path = get_concept_path()
    if concept_path and os.path.exists(concept_path):
        try:
            with open(concept_path, "r", encoding="utf-8") as f:
                concept_text = f.read(2000)  # Read first 2000 chars for topic extraction
            # Look for title or first heading
            title_match = re.search(r"^#\s+(.+)$", concept_text, re.MULTILINE)
            if title_match:
                topic_hint = title_match.group(1).strip()
        except Exception:  # nosec B110 - topic hint is optional
            pass
    return topic_hint


def _remediation_message(
    ref_count: int, min_refs: int, paper_type: str, search_query_example: str
) -> str:
    deficit = min_refs - ref_count
    return (
        f"❌ **WRITING BLOCKED — Insufficient References (Hook A7)**\n\n"
        f"📊 Current: **{ref_count}/{min_refs}** references "
        f"(paper type: {paper_type}, need **{deficit}** more)\n\n"
        f"---\n\n"
        f"## 🔧 REMEDIATION REQUIRED\n\n"
        f"Complete these steps before retrying `write_draft` or `draft_section`:\n\n"
        f"### Step 1: Search for more literature\n"
        f"```\n"
        f'unified_search(query="{search_query_example}", limit=20)\n'
        f"```\n\n"
        f"### Step 2: Save at least {deficit} references\n"
        f"```\n"
        f'save_reference_mcp(pmid="<PMID from search results>")\n'
        f"```\n"
        f"Repeat for each relevant article until you have ≥{min_refs} references.\n\n"
        f"### Step 3: Retry writing\n"
        f"Call `write_draft` or `draft_section` again after saving enough references.\n\n"
        f"---\n"
        f"⚠️ This is a **Code-Enforced** hard gate. Writing cannot proceed "
        f"until reference count ≥ {min_refs}."
    )


def _enforce_reference_sufficiency() -> tuple[bool, str]:
    """
    Hard gate: Block writing when saved references are below paper-type minimum.

    Cross-MCP enforcement: mdpaper cannot invoke pubmed-search directly,
    so this returns structured REMEDIATION_REQUIRED directives with exact
    tool calls the agent MUST execute before retrying.

    Returns:
        Tuple of (can_proceed: bool, message: str).
        When can_proceed is False, message contains blocking error + remediation steps.
        When can_proceed is True, message is empty or informational.
    """
    from med_paper_assistant.infrastructure.persistence import get_project_manager

    pm = get_project_manager()
    current_info = pm.get_project_info()
    if not current_info or not current_info.get("project_path"):
        # No project context — let other validators handle this
        return True, ""

    project_dir = Path(str(current_info["project_path"]))
    ref_count = _count_saved_references(project_dir)

    # Determine paper type and minimum (journal-profile.yaml overrides first)
    paper_type = current_info.get("paper_type", "original-research")
    paper_type, min_refs = _minimum_references(project_dir, paper_type)

    if ref_count >= min_refs:
        return True, ""

    project_name = current_info.get("name", "")
    topic_hint = _concept_topic_hint()
    search_query_example = topic_hint if topic_hint else project_name

    return False, _remediation_message(ref_count, min_refs, paper_type, search_query_example)


def _write_gate_error(skip_validation: bool, is_concept_file: bool) -> Optional[str]:
    if not skip_validation and not is_concept_file:
        can_proceed, message, protected = _enforce_concept_validation()
        if not can_proceed:
            log_tool_result("write_draft", "concept validation failed", success=False)
            return message

    # Enforce Reference Sufficiency (A7 hard gate)
    if not skip_validation and not is_concept_file:
        refs_ok, refs_msg = _enforce_reference_sufficiency()
        if not refs_ok:
            log_tool_result("write_draft", "reference sufficiency failed", success=False)
            return refs_msg
    return None


def _section_gate_error(skip_validation: bool) -> tuple[Optional[str], dict]:
    """Run draft_section gates; return (error, protected content)."""
    if skip_validation:
        return None, {}

    can_proceed, message, protected = _enforce_concept_validation()
    if not can_proceed:
        log_tool_result("draft_section", "concept validation failed", success=False)
        return message, {}

    # Enforce Reference Sufficiency (A7 hard gate)
    refs_ok, refs_msg = _enforce_reference_sufficiency()
    if not refs_ok:
        log_tool_result("draft_section", "reference sufficiency failed", success=False)
        return refs_msg, {}
    return None, protected


def _check_section_prerequisites(section_name: str) -> str:
    """
    Check writing order prerequisites for a section (advisory).

    Returns warning message if prerequisites are missing, empty string otherwise.
    """
    from med_paper_assistant.infrastructure.persistence import get_project_manager

    pm = get_project_manager()
    current_info = pm.get_project_info()
    if not current_info or not current_info.get("project_path"):
        return ""

    project_path = str(current_info["project_path"])
    paper_type = current_info.get("paper_type", "other")
    drafts_dir = os.path.join(project_path, "drafts")

    result = check_writing_prerequisites(paper_type, section_name, drafts_dir)
    return result.get("warning", "")
