"""Writing Hooks — C7d cross-references and C7b planned-asset coverage."""

from __future__ import annotations

import re
from typing import Any

import structlog

from .._asset_manifest import (
    asset_issue,
    cross_reference_issues,
    is_asset_placed,
    manifest_numbers,
)
from .._models import HookIssue, HookResult

logger = structlog.get_logger()


def _text_asset_refs(content: str) -> tuple[set[str], set[str]]:
    fig_refs = set(re.findall(r"Figure\s+(\d+)", content, re.IGNORECASE))
    tbl_refs = set(re.findall(r"Table\s+(\d+)", content, re.IGNORECASE))
    return fig_refs, tbl_refs


def _cross_ref_early_result(
    passed: bool,
    note: str,
    fig_refs: set[str],
    tbl_refs: set[str],
    issues: list[HookIssue],
) -> HookResult:
    return HookResult(
        hook_id="C7d",
        passed=passed,
        issues=issues,
        stats={
            "note": note,
            "text_figure_refs": sorted(fig_refs),
            "text_table_refs": sorted(tbl_refs),
        },
    )


def _plan_note_result(passed: bool, note: str, issues: list[HookIssue]) -> HookResult:
    return HookResult(
        hook_id="C7b",
        passed=passed,
        issues=issues,
        stats={"required_assets": 0, "note": note},
    )


class AssetCoverageHooksMixin:
    """C7d / C7b: figure/table cross-references and planned-asset coverage."""

    # ── Hook C7d: Orphan/Phantom Cross-References ──────────────────

    def check_cross_references(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook C7d: Detect orphan and phantom figure/table cross-references.

        - Phantom: referenced in text but not in manifest (CRITICAL)
        - Orphan: in manifest but not referenced in text (WARNING)
        """
        fig_refs, tbl_refs = _text_asset_refs(content)

        manifest_entries, manifest_error = self._load_manifest_entries_checked()
        if manifest_error:
            error_issue = self._parse_error_issue("C7d", "results/manifest.json", manifest_error)
            return _cross_ref_early_result(
                False, "manifest.json could not be parsed", fig_refs, tbl_refs, [error_issue]
            )
        if not manifest_entries:
            return _cross_ref_early_result(True, "No manifest.json found", fig_refs, tbl_refs, [])

        manifest_figs = manifest_numbers(manifest_entries, "figure")
        manifest_tbls = manifest_numbers(manifest_entries, "table")

        phantom_figs, orphan_figs = cross_reference_issues("Figure", fig_refs, manifest_figs)
        phantom_tbls, orphan_tbls = cross_reference_issues("Table", tbl_refs, manifest_tbls)
        issues = phantom_figs + phantom_tbls + orphan_figs + orphan_tbls

        passed = not any(i.severity == "CRITICAL" for i in issues)
        stats = {
            "phantom_count": len(phantom_figs) + len(phantom_tbls),
            "orphan_count": len(orphan_figs) + len(orphan_tbls),
            "text_figure_refs": sorted(fig_refs),
            "text_table_refs": sorted(tbl_refs),
            "manifest_figures": sorted(manifest_figs),
            "manifest_tables": sorted(manifest_tbls),
        }

        logger.info(
            "Hook C7d complete",
            passed=passed,
            phantoms=stats["phantom_count"],
            orphans=stats["orphan_count"],
        )
        return HookResult(hook_id="C7d", passed=passed, issues=issues, stats=stats)

    # ── Hook C7b: Planned Asset Coverage ───────────────────────────

    def _check_planned_asset(
        self,
        asset: dict[str, Any],
        manifest_entries: list[dict[str, Any]],
        sections: dict[str, str],
        issues: list[HookIssue],
    ) -> tuple[int, int, int]:
        """Return (matched, placed, exportable) increments for one planned asset."""
        entry = self._match_planned_asset_to_manifest(asset, manifest_entries)
        if entry is None:
            issues.append(
                asset_issue(
                    asset,
                    f"Planned {asset['kind']} '{asset['id']}' is missing from manifest.json",
                    "Run insert_figure/insert_table for this planned asset",
                )
            )
            return 0, 0, 0

        placed = 0
        section_content = sections.get(asset["section"].strip().lower(), "").lower()
        if is_asset_placed(asset["kind"], entry, section_content):
            placed = 1
        else:
            number = entry.get("number", "")
            label = f"{asset['kind'].title()} {number}" if number else asset["kind"].title()
            issues.append(
                asset_issue(
                    asset,
                    f"Planned {asset['kind']} '{asset['id']}' is not referenced or embedded in {asset['section']}",
                    f"Insert or cite {label} inside the {asset['section']} section",
                )
            )

        if asset["kind"] != "figure":
            return 1, placed, 0
        if self._has_exportable_figure_asset(entry.get("filename", "")):
            return 1, placed, 1
        issues.append(
            asset_issue(
                asset,
                f"Planned figure '{asset['id']}' lacks an exportable rendered asset",
                "Save a PNG/SVG/JPG/TIFF companion before export",
            )
        )
        return 1, placed, 0

    def check_asset_plan_coverage(
        self,
        content: str,
    ) -> HookResult:
        """Hook C7b: verify required planned assets are registered, placed, and exportable."""
        issues: list[HookIssue] = []

        planned_assets, plan_error = self._load_required_visual_assets_checked()
        if plan_error:
            error_issue = self._parse_error_issue("C7b", "manuscript-plan.yaml", plan_error)
            return _plan_note_result(
                False, "manuscript-plan.yaml could not be parsed", [error_issue]
            )
        if not planned_assets:
            return _plan_note_result(True, "No required visual assets in manuscript-plan.yaml", [])

        manifest_entries, manifest_error = self._load_manifest_entries_checked()
        if manifest_error:
            issues.append(self._parse_error_issue("C7b", "results/manifest.json", manifest_error))
        sections = {name.lower(): text for name, text in self._parse_sections_full(content).items()}

        tallies = [
            self._check_planned_asset(asset, manifest_entries, sections, issues)
            for asset in planned_assets
        ]

        passed = not any(issue.severity == "CRITICAL" for issue in issues)
        stats = {
            "required_assets": len(planned_assets),
            "manifest_matches": sum(t[0] for t in tallies),
            "placed_assets": sum(t[1] for t in tallies),
            "exportable_figures": sum(t[2] for t in tallies),
        }

        logger.info(
            "Hook C7b complete",
            passed=passed,
            required_assets=len(planned_assets),
            issues=len(issues),
        )
        return HookResult(hook_id="C7b", passed=passed, issues=issues, stats=stats)
