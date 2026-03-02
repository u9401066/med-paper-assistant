"""Writing Hooks — Pre-commit hooks mixin (P5: protected content, P7: ref integrity)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import structlog

from ._models import HookIssue, HookResult

logger = structlog.get_logger()


class PreCommitMixin:
    """P-series hooks that have their own implementation (not delegations)."""

    _project_dir: Path

    # ── Hook P5: Protected Content ─────────────────────────────────

    def check_protected_content(
        self,
        concept_path: Path | None = None,
    ) -> HookResult:
        """
        Hook P5: Verify 🔒-marked sections in concept.md are not empty.

        Scans concept.md for headings containing 🔒, extracts the content
        block under each, strips placeholder text, and flags empty blocks.
        """
        issues: list[HookIssue] = []

        if concept_path is None:
            concept_path = self._project_dir / "concept.md"

        if not concept_path.is_file():
            return HookResult(
                hook_id="P5",
                passed=True,
                stats={"note": "No concept.md found"},
            )

        try:
            concept_text = concept_path.read_text(encoding="utf-8")
        except Exception:
            return HookResult(
                hook_id="P5",
                passed=True,
                stats={"note": "Failed to read concept.md"},
            )

        # Find 🔒-marked headings
        protected_blocks: list[tuple[str, str]] = []
        lines = concept_text.split("\n")
        current_heading: str | None = None
        current_content: list[str] = []

        for line in lines:
            heading_match = re.match(r"^#{1,3}\s+(.+)", line)
            if heading_match:
                if current_heading is not None:
                    protected_blocks.append((current_heading, "\n".join(current_content).strip()))
                heading_text = heading_match.group(1).strip()
                if "\U0001f512" in heading_text:  # 🔒
                    current_heading = heading_text
                    current_content = []
                else:
                    current_heading = None
                    current_content = []
            elif current_heading is not None:
                current_content.append(line)

        # Don't forget last block
        if current_heading is not None:
            protected_blocks.append((current_heading, "\n".join(current_content).strip()))

        empty_blocks: list[str] = []
        for heading, block_content in protected_blocks:
            # Strip placeholder text
            stripped = re.sub(r"\[.*?\]", "", block_content).strip()
            stripped = re.sub(r">\s*\[.*?\]", "", stripped).strip()
            stripped = re.sub(r"^[-*]\s*$", "", stripped, flags=re.MULTILINE).strip()

            if not stripped:
                empty_blocks.append(heading)
                issues.append(
                    HookIssue(
                        hook_id="P5",
                        severity="CRITICAL",
                        section="concept.md",
                        message=f"Protected block '{heading}' is empty or only has placeholder text",
                        suggestion=f"Fill in the content for '{heading}' before proceeding",
                    )
                )

        passed = len(empty_blocks) == 0
        stats = {
            "protected_blocks_found": len(protected_blocks),
            "non_empty_count": len(protected_blocks) - len(empty_blocks),
            "empty_blocks": empty_blocks,
        }

        logger.info(
            "Hook P5 complete", passed=passed, blocks=len(protected_blocks), empty=len(empty_blocks)
        )
        return HookResult(hook_id="P5", passed=passed, issues=issues, stats=stats)

    # ── Hook P7: Reference Integrity ───────────────────────────────

    def check_reference_integrity(
        self,
        content: str | None = None,
    ) -> HookResult:
        """
        Hook P7: Verify saved references have VERIFIED status.

        Checks that each reference directory under references/ has valid
        metadata.json with _data_source == "pubmed_api" or verified == True.
        """
        issues: list[HookIssue] = []

        refs_dir = self._project_dir / "references"
        if not refs_dir.is_dir():
            return HookResult(
                hook_id="P7",
                passed=True,
                stats={"note": "No references directory found"},
            )

        total_refs = 0
        verified_count = 0
        unverified_refs: list[str] = []

        for ref_dir in sorted(refs_dir.iterdir()):
            if not ref_dir.is_dir():
                continue
            total_refs += 1
            metadata_path = ref_dir / "metadata.json"
            if not metadata_path.is_file():
                unverified_refs.append(ref_dir.name)
                continue
            try:
                with open(metadata_path, encoding="utf-8") as f:
                    meta = json.load(f)
                data_source = meta.get("_data_source", "")
                if data_source == "pubmed_api" or meta.get("verified", False):
                    verified_count += 1
                else:
                    unverified_refs.append(ref_dir.name)
            except Exception:
                unverified_refs.append(ref_dir.name)

        for ref_name in unverified_refs:
            issues.append(
                HookIssue(
                    hook_id="P7",
                    severity="WARNING",
                    section="references",
                    message=f"Reference '{ref_name}' is not verified (not from PubMed API)",
                    suggestion="Re-save with save_reference_mcp for verified metadata",
                )
            )

        passed = len(issues) == 0
        stats = {
            "total_refs": total_refs,
            "verified_count": verified_count,
            "unverified_count": len(unverified_refs),
            "unverified_refs": unverified_refs[:10],
        }

        logger.info("Hook P7 complete", passed=passed, verified=verified_count, total=total_refs)
        return HookResult(hook_id="P7", passed=passed, issues=issues, stats=stats)
