"""
Figure & Table Review Helpers

Validation, integrity-gate messaging and receipt recording behind
review_asset_for_insertion.
"""

import os
from pathlib import Path
from typing import Any, Literal, cast

from med_paper_assistant.infrastructure.persistence import DataArtifactTracker
from med_paper_assistant.shared.path_guard import normalize_relative_filename, resolve_child_path

from .._shared import log_tool_result
from .figure_assets import FIGURE_EXTENSIONS, TABLE_EXTENSIONS


def _normalize_review_filename(asset_type: str, filename: str) -> tuple[str, str]:
    """Validate asset_type and filename for a review; return (filename, error)."""
    if asset_type not in {"figure", "table"}:
        return filename, "❌ asset_type must be `figure` or `table`."

    try:
        filename = normalize_relative_filename(
            filename,
            field_name=f"{asset_type.title()} filename",
            allowed_suffixes=FIGURE_EXTENSIONS if asset_type == "figure" else TABLE_EXTENSIONS,
        )
    except ValueError as e:
        return filename, f"❌ Invalid {asset_type} filename: {e}"
    return filename, ""


def _locate_review_asset(project_path: str, asset_type: str, filename: str) -> tuple[str, str]:
    """Resolve the asset file for a review; return (asset_path, error)."""
    folder = "figures" if asset_type == "figure" else "tables"
    asset_path = str(
        resolve_child_path(
            Path(project_path) / "results" / folder,
            filename,
            field_name=f"{asset_type.title()} filename",
            allowed_suffixes=FIGURE_EXTENSIONS if asset_type == "figure" else TABLE_EXTENSIONS,
        )
    )
    if not os.path.isfile(asset_path):
        return asset_path, f"❌ File '{filename}' not found in results/{folder}/."
    return asset_path, ""


def _blocked_integrity_message(integrity: Any, integrity_receipt: dict) -> str:
    reason = "; ".join(integrity.gate_reasons)
    log_tool_result("review_asset_for_insertion", reason, success=False)
    return (
        "❌ **Asset Integrity Gate Blocked**\n\n"
        f"- **Integrity Receipt:** {integrity_receipt['id']}\n"
        f"- **C2PA:** {integrity.provenance.status.value}\n"
        "- **Removal-package check:** "
        f"{integrity.removal_package_check.status.value}\n"
        f"- **Reason:** {reason}\n"
        "- **Original preserved:** "
        f"{'yes' if integrity.original_preserved else 'no'}\n"
        "- **Automated removal:** disabled\n\n"
        "Do not insert or alter this asset. If the removal-package check is unavailable, "
        "install `med-paper-assistant[provenance,watermark]`; otherwise re-acquire the "
        "asset from an authorized source or resolve the provenance failure first."
    )


def _human_review_message(integrity: Any, integrity_receipt: dict) -> str:
    signals = list(integrity.visible_watermark.signals)
    signals.extend(integrity.removal_package_check.signal_names)
    signal_summary = ", ".join(signals) or "inconclusive screening"
    log_tool_result(
        "review_asset_for_insertion",
        "visible-watermark human review required",
        success=False,
    )
    return (
        "⚠️ **Visible-Watermark Human Review Required**\n\n"
        f"- **Integrity Receipt:** {integrity_receipt['id']}\n"
        f"- **Signals:** {signal_summary}\n"
        "- **Removal-package check:** "
        f"{integrity.removal_package_check.status.value}\n"
        "- **Automated removal:** disabled\n\n"
        "Inspect the original asset and call this tool again with "
        "`visible_watermark_review` documenting the reviewer conclusion. This field is "
        "self-attested; it does not cryptographically verify reviewer identity or rights."
    )


def _integrity_gate_message(
    integrity: Any, integrity_receipt: dict, visible_watermark_review: str
) -> str:
    """Return the gate message when the integrity gate stops the review, else ""."""
    if integrity.gate_status.value == "BLOCK":
        return _blocked_integrity_message(integrity, integrity_receipt)

    if integrity.gate_status.value == "HUMAN_REVIEW" and not visible_watermark_review.strip():
        return _human_review_message(integrity, integrity_receipt)
    return ""


def _render_review_recorded(
    receipt: dict,
    asset_type: str,
    filename: str,
    proposed_caption: str,
    integrity_receipt: dict,
    integrity: Any,
) -> str:
    folder = "figures" if asset_type == "figure" else "tables"
    return (
        f"✅ **Asset Review Recorded**\n\n"
        f"- **Receipt:** {receipt['id']}\n"
        f"- **Type:** {asset_type}\n"
        f"- **File:** results/{folder}/{filename}\n"
        f"- **Caption:** {proposed_caption}\n"
        f"- **Observations:** {len(receipt['observations'])}\n\n"
        f"- **Integrity Receipt:** {integrity_receipt['id']}\n"
        f"- **SHA-256:** {integrity.sha256}\n"
        f"- **MIME:** {integrity.mime_type}\n"
        f"- **C2PA:** {integrity.provenance.status.value}\n"
        f"- **Visible Watermark:** {integrity.visible_watermark.status.value}\n"
        "- **Removal-package check:** "
        f"{integrity.removal_package_check.status.value}\n"
        f"- **Integrity Gate:** {integrity.gate_status.value}\n"
        "- **Automated removal:** disabled\n\n"
        "You can now call `insert_figure` or `insert_table` with the same caption."
    )


def _record_review(
    tracker: DataArtifactTracker,
    asset_type: str,
    filename: str,
    asset_rel: str,
    review: dict[str, str],
    integrity: Any,
    integrity_receipt: dict,
) -> str:
    """Apply the integrity gate, record the asset review receipt and render the result."""
    gate_message = _integrity_gate_message(
        integrity, integrity_receipt, review["visible_watermark_review"]
    )
    if gate_message:
        return gate_message

    observation_items = [o.strip() for o in review["observations"].split("|") if o.strip()]
    receipt = tracker.record_asset_review(
        asset_type=cast(Literal["figure", "table"], asset_type),
        asset_path=asset_rel,
        observations=observation_items,
        rationale=review["rationale"],
        proposed_caption=review["proposed_caption"],
        evidence_excerpt=review["evidence_excerpt"],
        content_integrity_receipt_id=integrity_receipt["id"],
        visible_watermark_review=review["visible_watermark_review"],
    )

    result = _render_review_recorded(
        receipt, asset_type, filename, review["proposed_caption"], integrity_receipt, integrity
    )
    log_tool_result("review_asset_for_insertion", receipt["id"], success=True)
    return result
