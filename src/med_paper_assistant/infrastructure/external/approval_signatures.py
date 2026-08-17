"""Fail-closed verification for externally issued human-approval receipts.

The MCP server never signs approvals and never reads private key material.  A
trusted host supplies an Ed25519 public-key allowlist through process
configuration, while an external UI or approval service signs the receipt.
Workspace files therefore remain evidence, not a trust anchor.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import import_module
from typing import Any

APPROVAL_PUBLIC_KEYS_ENV = "MDPAPER_APPROVAL_ED25519_PUBLIC_KEYS"
APPROVAL_SIGNATURE_ALGORITHM = "Ed25519"
APPROVAL_SIGNATURE_ENCODING = "base64url"
CONCEPT_APPROVAL_SCHEMA = "mdpaper.concept_review_override.v3"
REVIEW_APPROVAL_SCHEMA = "mdpaper.review_completion_override.v3"

_APPROVAL_SCHEMAS = {CONCEPT_APPROVAL_SCHEMA, REVIEW_APPROVAL_SCHEMA}
_DOMAIN_SEPARATOR = b"mdpaper.external-approval.v3\x00"
_KEY_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_BASE64URL_PATTERN = re.compile(r"[A-Za-z0-9_-]+")
_SIGNATURE_FIELDS = {"algorithm", "encoding", "key_id", "value"}
_MAX_TRUSTED_KEYS = 64
_MAX_TRUST_STORE_BYTES = 65536


@dataclass(frozen=True)
class ApprovalSignatureVerification:
    """Result of an external approval signature check."""

    valid: bool
    details: str
    key_id: str = ""
    payload_sha256: str = ""


def _decode_base64url(value: str, *, expected_bytes: int) -> bytes:
    """Decode strict, unpadded base64url with an exact output length."""
    if _BASE64URL_PATTERN.fullmatch(value) is None:
        raise ValueError("value is not unpadded base64url")
    padding = "=" * (-len(value) % 4)
    decoded = base64.b64decode(
        (value + padding).encode("ascii"),
        altchars=b"-_",
        validate=True,
    )
    if len(decoded) != expected_bytes:
        raise ValueError(f"decoded value must contain {expected_bytes} bytes")
    return decoded


def canonical_external_approval_payload(receipt: Mapping[str, Any]) -> bytes:
    """Return the domain-separated canonical bytes covered by a v3 signature.

    The complete receipt is signed except for ``signature.value`` itself.
    Signature algorithm, encoding, and key identity remain inside the signed
    payload, preventing algorithm/key substitution.  JSON is strict (no NaN),
    UTF-8, key-sorted, and whitespace-free so trusted hosts can reproduce it.
    """
    signature = receipt.get("signature")
    if not isinstance(signature, Mapping) or set(signature) != _SIGNATURE_FIELDS:
        raise ValueError("signature block must contain exactly algorithm, encoding, key_id, value")

    canonical_receipt = dict(receipt)
    canonical_receipt["signature"] = {
        "algorithm": signature.get("algorithm"),
        "encoding": signature.get("encoding"),
        "key_id": signature.get("key_id"),
    }
    canonical_json = json.dumps(
        canonical_receipt,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return _DOMAIN_SEPARATOR + canonical_json


def _load_ed25519_backend() -> tuple[type[Any], type[Exception]]:
    """Load the verifier lazily so normal non-override gates remain available."""
    exceptions = import_module("cryptography.exceptions")
    ed25519 = import_module("cryptography.hazmat.primitives.asymmetric.ed25519")
    return ed25519.Ed25519PublicKey, exceptions.InvalidSignature


def _trusted_public_key(
    key_id: str,
    *,
    environ: Mapping[str, str],
) -> tuple[bytes | None, str]:
    """Resolve one public key exclusively from host process configuration."""
    encoded_store = environ.get(APPROVAL_PUBLIC_KEYS_ENV, "")
    if not encoded_store.strip():
        return (
            None,
            f"trusted approval public keys are not configured in {APPROVAL_PUBLIC_KEYS_ENV}",
        )
    if len(encoded_store.encode("utf-8")) > _MAX_TRUST_STORE_BYTES:
        return None, "trusted approval public-key configuration is too large"
    try:
        store = json.loads(encoded_store)
    except json.JSONDecodeError:
        return None, "trusted approval public-key configuration is invalid JSON"
    if not isinstance(store, dict) or not store or len(store) > _MAX_TRUSTED_KEYS:
        return None, "trusted approval public-key configuration must be a bounded JSON object"
    encoded_key = store.get(key_id)
    if not isinstance(encoded_key, str):
        return None, f"approval signing key is not trusted: {key_id}"
    try:
        return _decode_base64url(encoded_key, expected_bytes=32), ""
    except (UnicodeEncodeError, ValueError):
        return None, f"trusted approval public key is malformed: {key_id}"


def verify_external_approval_signature(
    receipt: Mapping[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
) -> ApprovalSignatureVerification:
    """Verify a v3 receipt against a host-configured Ed25519 trust anchor.

    Any missing dependency, malformed configuration, unknown key, malformed
    signature, or verification error returns an invalid result.  No workspace
    path is consulted for keys and no fallback accepts unsigned receipts.
    """
    if receipt.get("schema") not in _APPROVAL_SCHEMAS:
        return ApprovalSignatureVerification(
            False, "external approval receipt schema is unsupported"
        )

    signature = receipt.get("signature")
    if not isinstance(signature, Mapping) or set(signature) != _SIGNATURE_FIELDS:
        return ApprovalSignatureVerification(False, "external approval signature block is invalid")
    if signature.get("algorithm") != APPROVAL_SIGNATURE_ALGORITHM:
        return ApprovalSignatureVerification(
            False, "external approval signature algorithm is unsupported"
        )
    if signature.get("encoding") != APPROVAL_SIGNATURE_ENCODING:
        return ApprovalSignatureVerification(
            False, "external approval signature encoding is unsupported"
        )

    key_id = signature.get("key_id")
    if not isinstance(key_id, str) or _KEY_ID_PATTERN.fullmatch(key_id) is None:
        return ApprovalSignatureVerification(False, "external approval signing key_id is invalid")

    public_key_bytes, key_error = _trusted_public_key(
        key_id,
        environ=os.environ if environ is None else environ,
    )
    if public_key_bytes is None:
        return ApprovalSignatureVerification(False, key_error, key_id=key_id)

    signature_value = signature.get("value")
    if not isinstance(signature_value, str):
        return ApprovalSignatureVerification(
            False,
            "external approval signature value is missing",
            key_id=key_id,
        )
    try:
        signature_bytes = _decode_base64url(signature_value, expected_bytes=64)
        payload = canonical_external_approval_payload(receipt)
    except (TypeError, UnicodeEncodeError, ValueError):
        return ApprovalSignatureVerification(
            False,
            "external approval signed payload is malformed",
            key_id=key_id,
        )

    payload_sha256 = hashlib.sha256(payload).hexdigest()
    try:
        public_key_type, invalid_signature_error = _load_ed25519_backend()
    except (AttributeError, ImportError, ModuleNotFoundError):
        return ApprovalSignatureVerification(
            False,
            "Ed25519 verifier dependency is unavailable",
            key_id=key_id,
            payload_sha256=payload_sha256,
        )

    try:
        public_key = public_key_type.from_public_bytes(public_key_bytes)
        public_key.verify(signature_bytes, payload)
    except invalid_signature_error:
        return ApprovalSignatureVerification(
            False,
            "external approval signature verification failed",
            key_id=key_id,
            payload_sha256=payload_sha256,
        )
    except (TypeError, ValueError):
        return ApprovalSignatureVerification(
            False,
            "trusted approval public key could not be loaded",
            key_id=key_id,
            payload_sha256=payload_sha256,
        )
    except Exception:
        return ApprovalSignatureVerification(
            False,
            "Ed25519 verifier failed closed",
            key_id=key_id,
            payload_sha256=payload_sha256,
        )

    return ApprovalSignatureVerification(
        True,
        f"Ed25519 signature verified with trusted key {key_id}",
        key_id=key_id,
        payload_sha256=payload_sha256,
    )


__all__ = [
    "APPROVAL_PUBLIC_KEYS_ENV",
    "APPROVAL_SIGNATURE_ALGORITHM",
    "APPROVAL_SIGNATURE_ENCODING",
    "CONCEPT_APPROVAL_SCHEMA",
    "REVIEW_APPROVAL_SCHEMA",
    "ApprovalSignatureVerification",
    "canonical_external_approval_payload",
    "verify_external_approval_signature",
]
