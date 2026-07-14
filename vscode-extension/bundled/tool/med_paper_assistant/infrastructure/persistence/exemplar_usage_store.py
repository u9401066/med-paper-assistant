"""Auditable, non-evidentiary use records for exemplar documents.

Exemplars may calibrate structure, methodology reporting, argument flow, or
style. They must never become evidence, citation credit, or a source of copied
prose. This store makes that boundary machine-readable under ``.audit/``.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ALLOWED_EXEMPLAR_ROLES: frozenset[str] = frozenset(
    {
        "structure",
        "methodology",
        "reporting",
        "argument-map",
        "style-calibration",
    }
)
PROHIBITED_EXEMPLAR_ROLES: frozenset[str] = frozenset(
    {
        "verbatim-copy",
        "evidence-substitute",
        "citation-substitute",
        "fabricated-data",
    }
)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ExemplarPolicyError(ValueError):
    """Raised when an exemplar-use request violates the safety contract."""


class ExemplarUsageStore:
    """Persist project-level exemplar-use records with immutable policy flags."""

    DATA_FILE = "exemplar-usage.yaml"
    SCHEMA = "mdpaper.exemplar_usage.v1"

    def __init__(self, project_dir: str | Path) -> None:
        self._audit_dir = Path(project_dir) / ".audit"
        self._path = self._audit_dir / self.DATA_FILE

    @property
    def path(self) -> Path:
        """Return the audit artifact path."""
        return self._path

    def _empty_data(self) -> dict[str, Any]:
        return {
            "schema": self.SCHEMA,
            "policy": {
                "evidence_eligible": False,
                "citation_credit": False,
                "verbatim_copy": False,
                "requires_independent_verification": True,
                "allowed_roles": sorted(ALLOWED_EXEMPLAR_ROLES),
                "prohibited_roles": sorted(PROHIBITED_EXEMPLAR_ROLES),
            },
            "next_id": 1,
            "records": [],
        }

    def load(self) -> dict[str, Any]:
        """Load the artifact or return a new in-memory document."""
        if not self._path.is_file():
            return self._empty_data()
        try:
            loaded = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ExemplarPolicyError(f"invalid exemplar audit artifact: {exc}") from exc
        if not isinstance(loaded, dict):
            raise ExemplarPolicyError("exemplar audit artifact must be a mapping")
        loaded.setdefault("records", [])
        loaded.setdefault("next_id", 1)
        return loaded

    def _save(self, data: dict[str, Any]) -> None:
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        rendered = yaml.safe_dump(
            data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        temporary_path = self._path.with_suffix(".yaml.tmp")
        temporary_path.write_text(rendered, encoding="utf-8")
        temporary_path.replace(self._path)

    @staticmethod
    def _clean_string_list(values: list[Any], field_name: str) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            if not isinstance(value, str):
                raise ExemplarPolicyError(f"{field_name} must contain only strings")
            normalized = value.strip().lower() if field_name == "roles" else value.strip()
            if normalized and normalized not in cleaned:
                cleaned.append(normalized)
        return cleaned

    def record(
        self,
        *,
        source_id: str,
        roles: list[Any],
        target_sections: list[Any] | None = None,
        purpose: str = "",
        source_sha256: str = "",
        recorded_by: str = "agent",
    ) -> dict[str, Any]:
        """Record a bounded, transformative use of an exemplar."""
        normalized_source = source_id.strip()
        if not normalized_source:
            raise ExemplarPolicyError("source_id is required")
        if len(normalized_source) > 500:
            raise ExemplarPolicyError("source_id must be 500 characters or fewer")

        normalized_roles = self._clean_string_list(roles, "roles")
        if not normalized_roles:
            raise ExemplarPolicyError("at least one exemplar role is required")
        prohibited = sorted(set(normalized_roles) & PROHIBITED_EXEMPLAR_ROLES)
        if prohibited:
            raise ExemplarPolicyError(f"prohibited exemplar role(s): {', '.join(prohibited)}")
        unsupported = sorted(set(normalized_roles) - ALLOWED_EXEMPLAR_ROLES)
        if unsupported:
            allowed = ", ".join(sorted(ALLOWED_EXEMPLAR_ROLES))
            raise ExemplarPolicyError(
                f"unsupported exemplar role(s): {', '.join(unsupported)}; allowed: {allowed}"
            )

        normalized_sections = self._clean_string_list(target_sections or [], "target_sections")
        normalized_hash = source_sha256.strip().lower()
        if normalized_hash and not _SHA256_PATTERN.fullmatch(normalized_hash):
            raise ExemplarPolicyError("source_sha256 must be exactly 64 hexadecimal characters")
        normalized_purpose = purpose.strip()
        if len(normalized_purpose) > 2000:
            raise ExemplarPolicyError("purpose must be 2000 characters or fewer")

        data = self.load()
        issues = self.validate_integrity(data)
        if issues:
            raise ExemplarPolicyError(
                "existing exemplar audit artifact violates policy: " + issues[0]
            )
        record_id = f"EX-{int(data.get('next_id', 1)):04d}"
        record = {
            "id": record_id,
            "source_id": normalized_source,
            "source_sha256": normalized_hash or None,
            "roles": normalized_roles,
            "target_sections": normalized_sections,
            "purpose": normalized_purpose,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "recorded_by": recorded_by.strip() or "agent",
            "content_use": "transformative_reference_only",
            "evidence_eligible": False,
            "citation_credit": False,
            "verbatim_copy": False,
            "requires_independent_verification": True,
        }
        records = data.setdefault("records", [])
        if not isinstance(records, list):
            raise ExemplarPolicyError("exemplar audit records must be a list")
        records.append(record)
        data["next_id"] = int(data.get("next_id", 1)) + 1
        self._save(data)
        return record

    def validate_integrity(self, data: dict[str, Any] | None = None) -> list[str]:
        """Return policy violations found in a loaded audit artifact."""
        document = data if data is not None else self.load()
        issues: list[str] = []
        if document.get("schema") != self.SCHEMA:
            issues.append(f"schema must be {self.SCHEMA}")

        policy = document.get("policy")
        if not isinstance(policy, dict):
            issues.append("policy must be a mapping")
        else:
            for flag in ("evidence_eligible", "citation_credit", "verbatim_copy"):
                if policy.get(flag) is not False:
                    issues.append(f"policy.{flag} must be false")
            if policy.get("requires_independent_verification") is not True:
                issues.append("policy.requires_independent_verification must be true")
            if policy.get("allowed_roles") != sorted(ALLOWED_EXEMPLAR_ROLES):
                issues.append("policy.allowed_roles must match the code-enforced allowlist")
            if policy.get("prohibited_roles") != sorted(PROHIBITED_EXEMPLAR_ROLES):
                issues.append("policy.prohibited_roles must match the code-enforced denylist")

        records = document.get("records")
        if not isinstance(records, list):
            return issues + ["records must be a list"]
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                issues.append(f"records[{index}] must be a mapping")
                continue
            roles = record.get("roles", [])
            if not isinstance(roles, list) or not roles:
                issues.append(f"records[{index}].roles must be a non-empty list")
            elif set(roles) - ALLOWED_EXEMPLAR_ROLES:
                issues.append(f"records[{index}] contains a disallowed role")
            for flag in ("evidence_eligible", "citation_credit", "verbatim_copy"):
                if record.get(flag) is not False:
                    issues.append(f"records[{index}].{flag} must be false")
            if record.get("requires_independent_verification") is not True:
                issues.append(f"records[{index}].requires_independent_verification must be true")
        return issues

    def summary(self) -> dict[str, Any]:
        """Return record counts and integrity status."""
        data = self.load()
        records = data.get("records", [])
        issues = self.validate_integrity(data)
        return {
            "total": len(records) if isinstance(records, list) else 0,
            "integrity_passed": not issues,
            "issues": issues,
            "path": str(self._path),
        }
