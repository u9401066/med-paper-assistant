"""Reference evidence helpers: identity, PubMed transport binding, source revision."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from med_paper_assistant.domain.entities.reference import has_verified_pubmed_provenance

from ._constants import _MIN_REFERENCE_ARTIFACT_BYTES, _SHA256_PATTERN

_Revision = tuple[bool, str, str, str]


class _EvidenceError(Exception):
    """Raised when Phase 2.1 source evidence fails verification."""


def _canonical_json_sha256(payload: Any) -> str:
    """Return the SHA-256 of strict, deterministic JSON."""
    canonical = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _reference_identity(metadata: dict[str, Any]) -> str:
    """Return a source-qualified bibliographic identity, or an empty string."""
    pmid = str(metadata.get("pmid") or "").strip()
    if pmid.isdigit():
        return f"pmid:{pmid}"

    doi = str(metadata.get("doi") or metadata.get("DOI") or "").strip().lower()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"^doi:\s*", "", doi)
    if doi.startswith("10.") and "/" in doi:
        return f"doi:{doi}"

    zotero_key = str(metadata.get("zotero_key") or "").strip()
    if zotero_key:
        return f"zotero:{zotero_key}"

    unique_id = str(metadata.get("unique_id") or "").strip()
    content_hash = str(metadata.get("content_hash") or "").strip().lower()
    imported_from = str(metadata.get("imported_from") or "").strip()
    if unique_id and imported_from and _SHA256_PATTERN.fullmatch(content_hash):
        return f"local:{content_hash}"
    return ""


def _validate_pubmed_transport_payload(metadata: dict[str, Any]) -> tuple[bool, str]:
    """Bind VERIFIED metadata to the exact PubMed transport payload bytes."""
    if not has_verified_pubmed_provenance(metadata):
        return False, "verified trust claim lacks PubMed provenance"

    transport_payload = metadata.get("pubmed_transport_payload")
    if not isinstance(transport_payload, dict):
        return False, "verified reference is missing its PubMed transport payload"
    try:
        actual_hash = _canonical_json_sha256(transport_payload)
    except (TypeError, ValueError):
        return False, "PubMed transport payload is not canonical JSON"

    recorded_hash = str(metadata.get("payload_hash") or "").strip().lower()
    if actual_hash != recorded_hash:
        return False, "PubMed transport payload hash does not match provenance"
    pmid = str(metadata.get("pmid") or "").strip()
    if str(transport_payload.get("pmid") or "").strip() != pmid:
        return False, "PubMed transport payload PMID does not match metadata"
    if (
        str(transport_payload.get("title") or "").strip()
        != str(metadata.get("title") or "").strip()
    ):
        return False, "PubMed transport payload title does not match metadata"
    source_url = str(metadata.get("source_url") or "")
    configured_endpoint = os.environ.get("PUBMED_MCP_API_URL", "http://127.0.0.1:8765").rstrip("/")
    try:
        configured_url = urlsplit(configured_endpoint)
        recorded_url = urlsplit(source_url)
        configured_authority = (
            configured_url.scheme.lower(),
            (configured_url.hostname or "").lower(),
            configured_url.port,
        )
        recorded_authority = (
            recorded_url.scheme.lower(),
            (recorded_url.hostname or "").lower(),
            recorded_url.port,
        )
    except ValueError:
        return False, "PubMed source URL is invalid"
    if recorded_authority != configured_authority:
        return False, "PubMed source URL does not match the configured trusted endpoint"
    if re.search(rf"/api/cached_article/{re.escape(pmid)}(?:\?|$)", source_url) is None:
        return False, "PubMed source URL does not identify the recorded PMID"
    return True, f"PubMed payload sha256={actual_hash[:12]}…"


def _safe_artifact(path: Path) -> tuple[bool, bytes, str]:
    try:
        if path.is_symlink() or not path.is_file():
            return False, b"", "artifact is not a regular file"
        raw = path.read_bytes()
    except OSError:
        return False, b"", "artifact is unreadable"
    if len(raw) < _MIN_REFERENCE_ARTIFACT_BYTES:
        return (
            False,
            raw,
            (f"artifact is too small ({len(raw)} < {_MIN_REFERENCE_ARTIFACT_BYTES} bytes)"),
        )
    return True, raw, hashlib.sha256(raw).hexdigest()


def _fail(details: str) -> _Revision:
    return False, details, "", ""


def _verify_local_source(ref_dir: Path, metadata: dict[str, Any]) -> _Revision | None:
    """Verify ``source/`` artifacts; ``None`` means no source artifacts exist."""
    source_artifacts = sorted((ref_dir / "source").glob("*"))
    for source_path in source_artifacts:
        valid, _, digest_or_error = _safe_artifact(source_path)
        if not valid:
            continue
        recorded_hash = str(metadata.get("content_hash") or "").strip().lower()
        if _SHA256_PATTERN.fullmatch(recorded_hash) is None:
            return _fail("source artifact exists but metadata content_hash is missing")
        if digest_or_error != recorded_hash:
            continue
        return (
            True,
            f"source artifact verified: {source_path.name} sha256={recorded_hash[:12]}…",
            recorded_hash,
            "local-source",
        )
    if source_artifacts:
        return _fail("no source artifact matches metadata content_hash")
    return None


def _read_receipt(receipt_path: Path) -> tuple[bytes, dict[str, Any]]:
    try:
        receipt_raw = receipt_path.read_bytes()
        receipt = json.loads(receipt_raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise _EvidenceError("Asset-Aware receipt is unreadable or invalid JSON") from None
    if not isinstance(receipt, dict):
        raise _EvidenceError("Asset-Aware receipt must be a JSON object")
    if receipt.get("schema") != "mdpaper.asset_aware_fulltext.v1":
        raise _EvidenceError("Asset-Aware receipt schema is unsupported")
    if receipt.get("source_tool") != "asset-aware":
        raise _EvidenceError("Asset-Aware receipt source_tool is invalid")
    return receipt_raw, receipt


def _check_receipt_binding(
    receipt: dict[str, Any], receipt_raw: bytes, metadata: dict[str, Any]
) -> tuple[str, list[str], str]:
    """Bind the receipt to metadata; return ``(doc_id, sections, source_revision)``."""
    receipt_hash = hashlib.sha256(receipt_raw).hexdigest()
    if metadata.get("fulltext_receipt_sha256") != receipt_hash:
        raise _EvidenceError("Asset-Aware receipt hash does not match metadata")
    doc_id = str(metadata.get("asset_aware_doc_id") or "").strip()
    sections = metadata.get("fulltext_sections")
    normalized_sections = (
        [str(section).strip() for section in sections if str(section).strip()]
        if isinstance(sections, list)
        else []
    )
    if not doc_id or receipt.get("asset_aware_doc_id") != doc_id:
        raise _EvidenceError("Asset-Aware document identity does not match metadata")
    if not normalized_sections or receipt.get("fulltext_sections") != normalized_sections:
        raise _EvidenceError("Asset-Aware sections do not match metadata")
    source_revision = str(receipt.get("source_revision_sha256") or "").lower()
    if _SHA256_PATTERN.fullmatch(source_revision) is None:
        raise _EvidenceError("Asset-Aware source revision is missing")
    return doc_id, normalized_sections, source_revision


def _check_receipt_timestamp(receipt: dict[str, Any]) -> None:
    completed_at = receipt.get("completed_at")
    try:
        if not isinstance(completed_at, str):
            raise TypeError
        completed_time = datetime.fromisoformat(completed_at)
        if completed_time.utcoffset() is None:
            raise ValueError
    except (TypeError, ValueError):
        raise _EvidenceError("Asset-Aware receipt timestamp is invalid") from None


def _check_receipt_artifacts(receipt_path: Path, artifacts: list[Any]) -> None:
    artifact_root = receipt_path.parent.resolve()
    seen_paths: set[str] = set()
    for index, entry in enumerate(artifacts):
        if not isinstance(entry, dict):
            raise _EvidenceError(f"Asset-Aware artifact {index} is invalid")
        relative_path = entry.get("path")
        if not isinstance(relative_path, str) or not relative_path or relative_path in seen_paths:
            raise _EvidenceError(f"Asset-Aware artifact {index} path is invalid")
        seen_paths.add(relative_path)
        candidate = receipt_path.parent / relative_path
        try:
            resolved = candidate.resolve()
            resolved.relative_to(artifact_root)
        except (OSError, ValueError):
            raise _EvidenceError("Asset-Aware artifact escapes its receipt directory") from None
        valid, raw, digest_or_error = _safe_artifact(candidate)
        if not valid:
            raise _EvidenceError(f"Asset-Aware {relative_path}: {digest_or_error}")
        if entry.get("sha256") != digest_or_error or entry.get("bytes") != len(raw):
            raise _EvidenceError(f"Asset-Aware {relative_path} hash/size mismatch")


def _verify_receipt(receipt_path: Path, metadata: dict[str, Any]) -> _Revision:
    receipt_raw, receipt = _read_receipt(receipt_path)
    doc_id, normalized_sections, source_revision = _check_receipt_binding(
        receipt, receipt_raw, metadata
    )
    _check_receipt_timestamp(receipt)
    artifacts = receipt.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise _EvidenceError("Asset-Aware receipt has no artifact manifest")
    _check_receipt_artifacts(receipt_path, artifacts)
    computed_revision = _canonical_json_sha256(
        {
            "asset_aware_doc_id": doc_id,
            "fulltext_sections": normalized_sections,
            "artifacts": artifacts,
        }
    )
    if source_revision != computed_revision:
        raise _EvidenceError("Asset-Aware source revision does not match its manifest")
    return (
        True,
        f"Asset-Aware receipt verified ({len(artifacts)} artifacts)",
        source_revision,
        "asset-aware",
    )


def _verify_asset_aware_receipt(ref_dir: Path, metadata: dict[str, Any]) -> _Revision | None:
    """Verify the Asset-Aware receipt; ``None`` means no receipt exists."""
    receipt_path = ref_dir / "artifacts" / "asset-aware" / "receipt.json"
    if not receipt_path.is_file():
        return None
    try:
        return _verify_receipt(receipt_path, metadata)
    except _EvidenceError as error:
        return _fail(str(error))


def _verify_legacy_fulltext(ref_dir: Path, metadata: dict[str, Any]) -> _Revision:
    legacy_artifacts = [
        *sorted(ref_dir.glob("fulltext.*")),
        *sorted((ref_dir / "sections").glob("*.md")),
    ]
    recorded_hash = str(metadata.get("fulltext_artifact_sha256") or "").strip().lower()
    for legacy_path in legacy_artifacts:
        valid, _, digest_or_error = _safe_artifact(legacy_path)
        if valid and digest_or_error == recorded_hash:
            return (
                True,
                f"fulltext artifact verified: {legacy_path.name} sha256={recorded_hash[:12]}…",
                recorded_hash,
                "legacy-fulltext",
            )
    if legacy_artifacts:
        return _fail("legacy fulltext artifact hash/size is invalid")
    return _fail("fulltext_ingested=true without a verifiable source receipt")


def _metadata_only_revision(metadata: dict[str, Any]) -> _Revision:
    reason = str(metadata.get("fulltext_unavailable_reason") or "").strip()
    if len(reason) < 8:
        return _fail("fulltext unavailable reason is missing or too vague")
    revision_payload = {
        "identity": _reference_identity(metadata),
        "title": str(metadata.get("title") or "").strip(),
        "abstract": str(metadata.get("abstract") or "").strip(),
        "payload_hash": str(metadata.get("payload_hash") or "").strip().lower(),
        "fulltext_unavailable_reason": reason,
    }
    return (
        True,
        f"metadata-only fallback recorded: {reason}",
        _canonical_json_sha256(revision_payload),
        "metadata-only",
    )


def derive_reference_source_revision(
    ref_dir: Path,
    metadata: dict[str, Any],
) -> tuple[bool, str, str, str]:
    """Validate Phase 2.1 source evidence and return its immutable revision.

    The returned tuple is ``(valid, details, source_revision_sha256,
    source_kind)``.  Analysis receipts bind to the revision so replacing a PDF,
    extraction, or metadata-only fallback invalidates stale analysis.
    """
    if metadata.get("fulltext_ingested") is not True:
        return _metadata_only_revision(metadata)
    local_source = _verify_local_source(ref_dir, metadata)
    if local_source is not None:
        return local_source
    receipt = _verify_asset_aware_receipt(ref_dir, metadata)
    if receipt is not None:
        return receipt
    return _verify_legacy_fulltext(ref_dir, metadata)
