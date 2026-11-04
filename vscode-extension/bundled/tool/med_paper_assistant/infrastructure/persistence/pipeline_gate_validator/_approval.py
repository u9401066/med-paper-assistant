"""Shared checks for externally issued, signed approval receipts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from med_paper_assistant.infrastructure.external.approval_signatures import (
    verify_external_approval_signature,
)

from ._io import UNREADABLE, read_json_value

_REQUIRED_TEXT_FIELDS = ("approved_by", "rationale", "accepted_risks")
_CONFIRMATION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{15,127}")
_GENERIC_APPROVERS = {"human", "user", "agent", "ai", "llm", "autopilot"}


def _is_blank_text(value: object) -> bool:
    return not isinstance(value, str) or not value.strip()


def check_receipt_preamble(
    override: dict[str, Any], label: str, schema: str
) -> tuple[str | None, str]:
    """Check fields, schema, signature and decision source of a receipt.

    Returns ``(failure_message, signature_details)``; the failure is ``None``
    when every check passed.
    """
    empty_fields = [name for name in _REQUIRED_TEXT_FIELDS if _is_blank_text(override.get(name))]
    if empty_fields:
        return f"{label} has empty fields: {', '.join(empty_fields)}", ""
    if override.get("schema") != schema:
        return f"{label} schema is unsupported", ""
    signature_verification = verify_external_approval_signature(override)
    if not signature_verification.valid:
        return f"{label}: {signature_verification.details}", ""
    if override.get("approved_to_proceed") is not True:
        return f"{label} does not approve proceeding", ""
    if override.get("mode") != "human-collaboration":
        return f"{label} mode must be human-collaboration", ""
    if override.get("decision_source") != "external-user-confirmation":
        return f"{label} was not issued by an external user confirmation", ""
    return None, signature_verification.details


def check_receipt_identity(override: dict[str, Any], label: str, project_dir: Path) -> str | None:
    """Check confirmation id, approver identity and project binding of a receipt."""
    confirmation_id = override.get("confirmation_id")
    if not isinstance(confirmation_id, str) or _CONFIRMATION_ID.fullmatch(confirmation_id) is None:
        return f"{label} confirmation_id is missing or invalid"
    approved_by = str(override.get("approved_by")).strip().lower()
    if approved_by in _GENERIC_APPROVERS:
        return f"{label} requires a specific external reviewer identity"

    project_slug = project_dir.name
    project_json = project_dir / "project.json"
    if project_json.is_file():
        project_data = read_json_value(project_json)
        if project_data is UNREADABLE:
            return "project identity is unreadable"
        if isinstance(project_data, dict):
            project_slug = str(project_data.get("slug") or project_slug)
    if override.get("project_slug") != project_slug:
        return f"{label} belongs to a different project"
    return None
