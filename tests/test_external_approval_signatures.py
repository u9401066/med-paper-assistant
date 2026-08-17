"""Cryptographic trust-boundary tests for external human approvals."""

from __future__ import annotations

import base64
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from med_paper_assistant.infrastructure.external import approval_signatures
from med_paper_assistant.infrastructure.external.approval_signatures import (
    APPROVAL_PUBLIC_KEYS_ENV,
    CONCEPT_APPROVAL_SCHEMA,
    canonical_external_approval_payload,
    verify_external_approval_signature,
)


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _signed_receipt() -> tuple[dict[str, object], dict[str, str]]:
    private_key = Ed25519PrivateKey.generate()
    key_id = "trusted-host-2026"
    receipt: dict[str, object] = {
        "schema": CONCEPT_APPROVAL_SCHEMA,
        "approved_to_proceed": True,
        "approved_at": "2026-08-17T00:00:00+00:00",
        "approved_by": "principal-investigator:pi-001",
        "accepted_readiness": "revise",
        "rationale": "Proceed with the bounded design and disclose the residual risk.",
        "accepted_risks": "Novelty remains limited and requires explicit disclosure.",
        "mode": "human-collaboration",
        "decision_source": "external-user-confirmation",
        "confirmation_id": "concept-confirmation-0001",
        "project_slug": "test",
        "concept_review_sha256": "a" * 64,
        "concept_artifact_sha256": "b" * 64,
        "signature": {
            "algorithm": "Ed25519",
            "encoding": "base64url",
            "key_id": key_id,
            "value": "",
        },
    }
    signature = private_key.sign(canonical_external_approval_payload(receipt))
    receipt["signature"]["value"] = _base64url(signature)  # type: ignore[index]
    trust_store = {
        APPROVAL_PUBLIC_KEYS_ENV: json.dumps(
            {key_id: _base64url(private_key.public_key().public_bytes_raw())}
        )
    }
    return receipt, trust_store


def test_valid_ed25519_receipt_uses_host_trust_anchor() -> None:
    receipt, trust_store = _signed_receipt()

    result = verify_external_approval_signature(receipt, environ=trust_store)

    assert result.valid
    assert result.key_id == "trusted-host-2026"
    assert len(result.payload_sha256) == 64


def test_canonical_payload_is_order_independent_and_domain_separated() -> None:
    receipt, _ = _signed_receipt()
    reordered = dict(reversed(list(receipt.items())))

    canonical = canonical_external_approval_payload(receipt)

    assert canonical == canonical_external_approval_payload(reordered)
    assert canonical.startswith(b"mdpaper.external-approval.v3\x00")
    assert b'"value"' not in canonical
    assert b'"key_id":"trusted-host-2026"' in canonical


def test_tampered_receipt_fails_signature_verification() -> None:
    receipt, trust_store = _signed_receipt()
    receipt["accepted_risks"] = "No remaining risk."

    result = verify_external_approval_signature(receipt, environ=trust_store)

    assert not result.valid
    assert "signature verification failed" in result.details


def test_wrong_trusted_key_fails_signature_verification() -> None:
    receipt, trust_store = _signed_receipt()
    wrong_key = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
    trust_store[APPROVAL_PUBLIC_KEYS_ENV] = json.dumps({"trusted-host-2026": _base64url(wrong_key)})

    result = verify_external_approval_signature(receipt, environ=trust_store)

    assert not result.valid
    assert "signature verification failed" in result.details


def test_missing_trusted_key_configuration_fails_closed() -> None:
    receipt, _ = _signed_receipt()

    result = verify_external_approval_signature(receipt, environ={})

    assert not result.valid
    assert APPROVAL_PUBLIC_KEYS_ENV in result.details


def test_unknown_key_id_fails_closed_without_embedded_key_fallback() -> None:
    receipt, trust_store = _signed_receipt()
    receipt["signature"]["key_id"] = "untrusted-key"  # type: ignore[index]

    result = verify_external_approval_signature(receipt, environ=trust_store)

    assert not result.valid
    assert "not trusted" in result.details


def test_key_id_substitution_fails_even_when_alias_has_same_public_key() -> None:
    receipt, trust_store = _signed_receipt()
    configured_keys = json.loads(trust_store[APPROVAL_PUBLIC_KEYS_ENV])
    configured_keys["trusted-host-alias"] = configured_keys["trusted-host-2026"]
    trust_store[APPROVAL_PUBLIC_KEYS_ENV] = json.dumps(configured_keys)
    receipt["signature"]["key_id"] = "trusted-host-alias"  # type: ignore[index]

    result = verify_external_approval_signature(receipt, environ=trust_store)

    assert not result.valid
    assert "signature verification failed" in result.details


def test_missing_crypto_backend_fails_closed(monkeypatch) -> None:
    receipt, trust_store = _signed_receipt()

    def missing_backend():
        raise ModuleNotFoundError("cryptography intentionally unavailable")

    monkeypatch.setattr(approval_signatures, "_load_ed25519_backend", missing_backend)

    result = verify_external_approval_signature(receipt, environ=trust_store)

    assert not result.valid
    assert "dependency is unavailable" in result.details


def test_unsigned_v2_receipt_is_not_accepted() -> None:
    receipt, trust_store = _signed_receipt()
    receipt["schema"] = "mdpaper.concept_review_override.v2"
    receipt.pop("signature")

    result = verify_external_approval_signature(receipt, environ=trust_store)

    assert not result.valid
    assert "schema is unsupported" in result.details
