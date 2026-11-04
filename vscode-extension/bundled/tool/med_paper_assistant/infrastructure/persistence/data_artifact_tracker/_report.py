"""Data Artifact Tracker — markdown provenance report generation."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from ._storage import _StorageMixin


def _artifact_section_lines(artifacts: list[dict[str, Any]]) -> list[str]:
    """Render artifacts grouped by type."""
    lines: list[str] = []
    by_type: dict[str, list[dict[str, Any]]] = {}
    for a in artifacts:
        t = a.get("artifact_type", "unknown")
        by_type.setdefault(t, []).append(a)

    for atype, items in by_type.items():
        lines.append(f"## {atype.capitalize()}s ({len(items)})")
        lines.append("")
        for item in items:
            lines.append(f"### {item.get('id')} — {item.get('tool_name')}")
            lines.append(f"- **Data Source**: {item.get('data_source', 'N/A')}")
            lines.append(f"- **Output**: {item.get('output_path', 'ephemeral')}")
            lines.append(f"- **Timestamp**: {item.get('timestamp')}")
            if item.get("parameters"):
                lines.append(
                    f"- **Parameters**: `{json.dumps(item['parameters'], ensure_ascii=False)}`"
                )
            if item.get("result_summary"):
                lines.append(f"- **Result**: {item['result_summary']}")
            if item.get("provenance_code"):
                lines.append("- **Reproducibility Code**:")
                lines.append("```python")
                lines.append(item["provenance_code"])
                lines.append("```")
            lines.append("")
    return lines


def _review_section_lines(reviews: list[dict[str, Any]]) -> list[str]:
    """Render asset review receipts."""
    lines = [f"## Asset Reviews ({len(reviews)})", ""]
    for review in reviews:
        lines.append(
            f"### {review.get('id')} — {review.get('asset_type')} {review.get('asset_path')}"
        )
        lines.append(f"- **Timestamp**: {review.get('timestamp')}")
        lines.append(f"- **Proposed Caption**: {review.get('proposed_caption', '')}")
        lines.append(f"- **Rationale**: {review.get('rationale', '')}")
        if review.get("evidence_excerpt"):
            lines.append(f"- **Evidence Excerpt**: {review.get('evidence_excerpt')}")
        observations = review.get("observations", [])
        if observations:
            lines.append("- **Observations**:")
            for observation in observations:
                lines.append(f"  - {observation}")
        lines.append("")
    return lines


def _receipt_entry_lines(receipt: dict[str, Any]) -> list[str]:
    file_info = receipt.get("file", {})
    provenance = receipt.get("provenance", {})
    visible = receipt.get("visible_watermark", {})
    removal = receipt.get("removal_package_check", {})
    return [
        f"### {receipt.get('id')} — {receipt.get('asset_path')}",
        f"- **Inspected**: {receipt.get('inspected_at')}",
        f"- **SHA-256**: `{file_info.get('sha256', '')}`",
        f"- **MIME**: {file_info.get('mime_type', '')}",
        f"- **C2PA**: {provenance.get('status', '')}",
        f"- **Visible Watermark**: {visible.get('status', '')}",
        "- **Removal-Package Check**: "
        f"{removal.get('status', '')} ({removal.get('provider_version') or 'n/a'})",
        f"- **Gate**: {receipt.get('gate_status', '')}",
        "- **Original Preserved**: "
        + ("yes" if receipt.get("original_preserved") is True else "no"),
        "- **Automated Removal**: "
        + ("disabled" if receipt.get("automated_removal_performed") is False else "UNKNOWN"),
        "",
    ]


def _receipt_section_lines(integrity_receipts: list[dict[str, Any]]) -> list[str]:
    """Render content-integrity receipts."""
    lines = [f"## Content Integrity Receipts ({len(integrity_receipts)})", ""]
    for receipt in integrity_receipts:
        lines.extend(_receipt_entry_lines(receipt))
    return lines


class _ReportMixin(_StorageMixin):
    """Render and persist the markdown provenance report."""

    def generate_report(self) -> str:
        """Generate a markdown report of all tracked artifacts."""
        data = self._load()
        artifacts = data.get("artifacts", [])

        lines = [
            "# Data Artifact Provenance Report",
            "",
            f"**Generated**: {datetime.now().isoformat()}",
            f"**Total Artifacts**: {len(artifacts)}",
            "",
        ]
        lines.extend(_artifact_section_lines(artifacts))

        reviews = data.get("asset_reviews", [])
        if reviews:
            lines.extend(_review_section_lines(reviews))

        integrity_receipts = data.get("content_integrity_receipts", [])
        if integrity_receipts:
            lines.extend(_receipt_section_lines(integrity_receipts))

        report_text = "\n".join(lines)

        # Save report
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        self._report_path.write_text(report_text, encoding="utf-8")

        return report_text
