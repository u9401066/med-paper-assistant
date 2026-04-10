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

    # ── Hook P6: Memory Sync Gate ──────────────────────────────────

    def check_memory_sync(self) -> HookResult:
        """Hook P6: Verify memory files were updated before commit.

        Code-Enforced pre-commit check. Verifies that project .memory/
        or workspace memory-bank/ files have been modified recently
        (within the last 2 hours), indicating the Agent synced context.

        Previously Agent-Driven (relied on Agent reading git-precommit SKILL.md).
        Now Code-Enforced for weak model resilience.
        """
        import time

        issues: list[HookIssue] = []
        staleness_threshold = 7200  # 2 hours in seconds

        # Check project-level memory
        memory_dir = self._project_dir / ".memory"
        # Also check workspace-level memory-bank
        workspace_root = self._project_dir
        for _ in range(5):
            if (workspace_root / ".git").is_dir():
                break
            parent = workspace_root.parent
            if parent == workspace_root:
                break
            workspace_root = parent
        memory_bank_dir = workspace_root / "memory-bank"

        memory_files_checked = 0
        stale_files: list[str] = []
        fresh_files: list[str] = []
        now = time.time()

        # Check key memory files
        files_to_check = []
        if memory_dir.is_dir():
            files_to_check.append(memory_dir / "activeContext.md")
        if memory_bank_dir.is_dir():
            files_to_check.append(memory_bank_dir / "activeContext.md")
            files_to_check.append(memory_bank_dir / "progress.md")

        for fpath in files_to_check:
            if not fpath.is_file():
                continue
            memory_files_checked += 1
            try:
                mtime = fpath.stat().st_mtime
                age = now - mtime
                if age > staleness_threshold:
                    stale_files.append(f"{fpath.name} (age: {age / 3600:.1f}h)")
                else:
                    fresh_files.append(fpath.name)
            except OSError:
                stale_files.append(f"{fpath.name} (unreadable)")

        if memory_files_checked == 0:
            return HookResult(
                hook_id="P6",
                passed=True,
                stats={"note": "No memory files found to check"},
            )

        if stale_files and not fresh_files:
            issues.append(
                HookIssue(
                    hook_id="P6",
                    severity="WARNING",
                    section="memory",
                    message=f"Memory files appear stale: {', '.join(stale_files)}",
                    suggestion=(
                        "Run sync_workspace_state() or update memory-bank/ "
                        "before committing to preserve session context"
                    ),
                )
            )

        passed = len(issues) == 0
        stats = {
            "files_checked": memory_files_checked,
            "fresh_files": fresh_files,
            "stale_files": stale_files,
        }

        logger.info(
            "Hook P6 complete", passed=passed, fresh=len(fresh_files), stale=len(stale_files)
        )
        return HookResult(hook_id="P6", passed=passed, issues=issues, stats=stats)
