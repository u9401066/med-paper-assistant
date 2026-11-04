"""Reference record loading and analysis-artifact validation for the gate validator."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ._base import GateBase
from ._constants import REFERENCE_ANALYSIS_TEXT_MINIMUMS
from ._io import UNREADABLE, read_json_value
from ._reference_evidence import (
    _reference_identity,
    _validate_pubmed_transport_payload,
    derive_reference_source_revision,
)

_ANALYSIS_SCHEMA = "mdpaper.reference_analysis.v1"
_ANALYSIS_TOOL = "save_reference_analysis"


def _inspect_metadata(
    metadata: dict[str, Any], seen_identities: dict[str, str]
) -> tuple[str, str | None]:
    """Return ``(identity, problem)`` for one parsed metadata object."""
    identity = _reference_identity(metadata)
    if not identity:
        return identity, "no stable reference identity"
    title = str(metadata.get("title") or "").strip()
    if not title:
        return identity, "bibliographic title is missing"
    if identity in seen_identities:
        return identity, (
            f"duplicate identity {identity} (already stored by {seen_identities[identity]})"
        )

    trust_level = str(metadata.get("trust_level") or "").strip().lower()
    data_source = str(metadata.get("data_source") or "").strip().lower()
    claims_verified = (
        metadata.get("verified") is True
        or trust_level == "verified"
        or data_source == "pubmed_mcp_api"
    )
    if claims_verified:
        provenance_valid, provenance_details = _validate_pubmed_transport_payload(metadata)
        if not provenance_valid:
            return identity, provenance_details
    return identity, None


def _legacy_markdown_count(refs_dir: Path, invalid: list[str]) -> int:
    """Count non-empty legacy Markdown references, recording unreadable ones in ``invalid``."""
    legacy_files = []
    for path in sorted(refs_dir.glob("*.md")):
        if path.name == "fulltext-ingestion-status.md" or not path.is_file():
            continue
        try:
            if path.stat().st_size > 0:
                legacy_files.append(path)
        except OSError:
            invalid.append(f"{path.name}: unreadable legacy reference")
    if legacy_files:
        invalid.append(
            f"{len(legacy_files)} legacy Markdown reference(s) require structured migration"
        )
    return len(legacy_files)


def _analysis_content_failure(analysis: dict[str, Any]) -> str | None:
    if analysis.get("schema") != _ANALYSIS_SCHEMA:
        return "analysis.json schema is missing or unsupported"
    if analysis.get("source_tool") != _ANALYSIS_TOOL:
        return "analysis.json source_tool is not save_reference_analysis"
    for field_name, minimum_chars in REFERENCE_ANALYSIS_TEXT_MINIMUMS.items():
        field_value = str(analysis.get(field_name) or "").strip()
        if len(field_value) < minimum_chars:
            return (
                f"analysis.json {field_name} must contain at least "
                f"{minimum_chars} substantive characters"
            )
    usage_sections = analysis.get("usage_sections")
    if (
        not isinstance(usage_sections, list)
        or not usage_sections
        or any(not isinstance(section, str) or not section.strip() for section in usage_sections)
    ):
        return "analysis.json usage_sections must contain named manuscript sections"
    relevance_score = analysis.get("relevance_score")
    if (
        isinstance(relevance_score, bool)
        or not isinstance(relevance_score, int)
        or not 1 <= relevance_score <= 5
    ):
        return "analysis.json relevance_score must be an integer from 1 to 5"
    return None


def _analysis_binding_failure(
    analysis: dict[str, Any],
    metadata: dict[str, Any],
    ref_dir: Path,
    source_revision_sha256: str,
    source_kind: str,
) -> str | None:
    if analysis.get("source_revision_sha256") != source_revision_sha256:
        return "analysis.json is stale for the current source revision"
    if analysis.get("source_kind") != source_kind:
        return "analysis.json source_kind does not match source evidence"

    expected_ids = {
        str(value).strip()
        for value in (metadata.get("unique_id"), metadata.get("pmid"))
        if str(value or "").strip()
    }
    if not expected_ids:
        expected_ids.add(ref_dir.name)
    if str(analysis.get("pmid") or "").strip() not in expected_ids:
        return "analysis.json reference identity does not match metadata"
    return None


def _analysis_time_failure(analyzed_at: str) -> str | None:
    try:
        analyzed_time = datetime.fromisoformat(analyzed_at)
        if analyzed_time.utcoffset() is None:
            raise ValueError
    except ValueError:
        return "analysis.json analyzed_at is invalid"
    return None


def _analysis_receipt_failure(
    metadata: dict[str, Any],
    analysis: dict[str, Any],
    actual_hash: str,
    source_revision_sha256: str,
) -> str | None:
    if metadata.get("analysis_artifact_sha256") != actual_hash:
        return "analysis artifact hash does not match metadata"
    if metadata.get("analysis_source_tool") != _ANALYSIS_TOOL:
        return "metadata analysis_source_tool is invalid"
    if metadata.get("analysis_completed_at") != str(analysis.get("analyzed_at") or ""):
        return "metadata analysis_completed_at does not match analysis.json"
    if metadata.get("analysis_source_revision_sha256") != source_revision_sha256:
        return "metadata analysis receipt is stale for the current source"
    if (
        str(metadata.get("analysis_summary") or "").strip()
        != str(analysis.get("summary") or "").strip()
    ):
        return "metadata analysis_summary does not match analysis.json"
    if metadata.get("usage_sections") != analysis.get("usage_sections"):
        return "metadata usage_sections do not match analysis.json"
    return None


class ReferenceChecksMixin(GateBase):
    """Structured reference loading and analysis/source-revision validation."""

    @staticmethod
    def _reference_records(
        refs_dir: Path,
    ) -> tuple[list[tuple[Path, dict[str, Any]]], list[str], int]:
        """Load unique, sufficiently described references and reject forged trust."""
        if not refs_dir.is_dir():
            return [], [], 0

        records: list[tuple[Path, dict[str, Any]]] = []
        invalid: list[str] = []
        seen_identities: dict[str, str] = {}
        for metadata_path in sorted(refs_dir.glob("*/metadata.json")):
            name = metadata_path.parent.name
            metadata = read_json_value(metadata_path)
            if metadata is UNREADABLE:
                invalid.append(f"{name}: unreadable metadata.json")
                continue
            if not isinstance(metadata, dict):
                invalid.append(f"{name}: metadata must be an object")
                continue

            identity, problem = _inspect_metadata(metadata, seen_identities)
            if problem is not None:
                invalid.append(f"{name}: {problem}")
                continue
            seen_identities[identity] = name
            records.append((metadata_path.parent, metadata))

        legacy_count = _legacy_markdown_count(refs_dir, invalid)
        return records, invalid, legacy_count

    @classmethod
    def _count_references(cls, refs_dir: Path) -> int:
        """Count valid structured references, or non-empty legacy Markdown records."""
        records, _, legacy_count = cls._reference_records(refs_dir)
        return len(records) if records else legacy_count

    @staticmethod
    def _validate_reference_analysis(
        ref_dir: Path,
        metadata: dict[str, Any],
        *,
        source_revision_sha256: str,
        source_kind: str,
    ) -> tuple[bool, str]:
        """Verify a complete analysis and bind it to the validated source revision."""
        analysis_path = ref_dir / "analysis.json"
        if not analysis_path.is_file():
            return False, "analysis.json is missing"
        try:
            raw = analysis_path.read_bytes()
            analysis = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return False, "analysis.json is unreadable or invalid JSON"
        if not isinstance(analysis, dict):
            return False, "analysis.json must contain an object"

        failure = _analysis_content_failure(analysis)
        if failure is None:
            failure = _analysis_binding_failure(
                analysis, metadata, ref_dir, source_revision_sha256, source_kind
            )
        if failure is None:
            failure = _analysis_time_failure(str(analysis.get("analyzed_at") or ""))
        actual_hash = hashlib.sha256(raw).hexdigest()
        if failure is None:
            failure = _analysis_receipt_failure(
                metadata, analysis, actual_hash, source_revision_sha256
            )
        if failure is not None:
            return False, failure
        return True, f"verified analysis artifact sha256={actual_hash[:12]}…"

    @staticmethod
    def _validate_fulltext_status(
        ref_dir: Path,
        metadata: dict[str, Any],
    ) -> tuple[bool, str, str, str]:
        """Delegate to the shared, receipt-bound source revision validator."""
        return derive_reference_source_revision(ref_dir, metadata)
