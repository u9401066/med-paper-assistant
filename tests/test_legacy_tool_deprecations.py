from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _read_package(relative_dir: str) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8") for path in sorted((ROOT / relative_dir).glob("*.py"))
    )


def test_project_legacy_public_verbs_point_to_facade_replacements() -> None:
    content = _read("src/med_paper_assistant/interfaces/mcp/tools/project/crud/queries.py")

    assert 'DEPRECATED public verb. Prefer `project_action(action="list")`.' in content
    assert 'DEPRECATED public verb. Prefer `project_action(action="current")`.' in content


def test_review_audit_legacy_public_verbs_point_to_facade_replacements() -> None:
    content = _read_package("src/med_paper_assistant/interfaces/mcp/tools/review/audit_hooks")

    assert (
        'DEPRECATED public verb. Prefer `run_quality_checks(action="quality_audit", ...)`.'
        in content
    )
    assert (
        'DEPRECATED public verb. Prefer `run_quality_checks(action="writing_hooks", ...)`.'
        in content
    )


def test_pipeline_legacy_public_verbs_point_to_facade_replacements() -> None:
    content = _read_package("src/med_paper_assistant/interfaces/mcp/tools/review/pipeline_gate")

    assert (
        'DEPRECATED public verb. Prefer `pipeline_action(action="validate_phase", phase=...)`.'
        in content
    )
    assert 'DEPRECATED public verb. Prefer `pipeline_action(action="heartbeat")`.' in content
    assert (
        'DEPRECATED public verb. Prefer `pipeline_action(action="start_review", ...)`.' in content
    )
    assert (
        'DEPRECATED public verb. Prefer `pipeline_action(action="submit_review", ...)`.' in content
    )


def test_export_legacy_public_verbs_point_to_facade_replacements() -> None:
    content = _read("src/med_paper_assistant/interfaces/mcp/tools/export/pandoc_export.py")

    assert 'DEPRECATED public verb. Prefer `export_document(action="docx", ...)`.' in content
    assert 'DEPRECATED public verb. Prefer `export_document(action="pdf", ...)`.' in content
