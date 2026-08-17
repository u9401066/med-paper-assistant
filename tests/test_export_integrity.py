"""Parity and fail-closed tests for shared export integrity checks."""

from __future__ import annotations

import zipfile
from pathlib import Path

from pypdf import PdfWriter

from med_paper_assistant.application.export_pipeline import ExportPipeline
from med_paper_assistant.shared.export_integrity import (
    inspect_docx_xml_smoke,
    inspect_pdf_smoke,
)


def _write_docx(path: Path, document_xml: str) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types></Types>")
        archive.writestr("word/document.xml", document_xml)


def _valid_document_xml(text: str = "Exported manuscript") -> str:
    return (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body>"
        "</w:document>"
    )


def _write_pdf(path: Path, *, pages: int) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    with path.open("wb") as stream:
        writer.write(stream)


def _failed_check_names(result: dict[str, object]) -> set[str]:
    checks = result["checks"]
    assert isinstance(checks, list)
    return {
        str(check["name"])
        for check in checks
        if isinstance(check, dict) and check.get("passed") is False
    }


def test_docx_shared_result_matches_export_pipeline_public_api(tmp_path: Path) -> None:
    path = tmp_path / "valid.docx"
    _write_docx(path, _valid_document_xml())

    assert ExportPipeline.inspect_docx_xml_smoke(path) == inspect_docx_xml_smoke(path)


def test_pdf_shared_result_matches_export_pipeline_public_api(tmp_path: Path) -> None:
    path = tmp_path / "valid.pdf"
    _write_pdf(path, pages=1)

    assert ExportPipeline.inspect_pdf_smoke(path) == inspect_pdf_smoke(path)


def test_docx_rejects_non_zip_container(tmp_path: Path) -> None:
    path = tmp_path / "not-a-docx.docx"
    path.write_bytes(b"not an OOXML zip container")

    result = inspect_docx_xml_smoke(path)

    assert result["passed"] is False
    assert "zip_container" in _failed_check_names(result)


def test_docx_rejects_malformed_document_xml(tmp_path: Path) -> None:
    path = tmp_path / "malformed.docx"
    _write_docx(path, "<w:document>")

    result = inspect_docx_xml_smoke(path)

    assert result["passed"] is False
    assert "document_xml_parse" in _failed_check_names(result)


def test_docx_rejects_missing_body_and_raw_citation_tokens(tmp_path: Path) -> None:
    missing_body = tmp_path / "missing-body.docx"
    _write_docx(
        missing_body,
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>',
    )
    leaked_citation = tmp_path / "leaked-citation.docx"
    _write_docx(leaked_citation, _valid_document_xml("Unresolved [@smith2026]"))

    missing_body_result = inspect_docx_xml_smoke(missing_body)
    leaked_citation_result = inspect_docx_xml_smoke(leaked_citation)

    assert "word/body" in _failed_check_names(missing_body_result)
    assert "raw_citation_tokens" in _failed_check_names(leaked_citation_result)


def test_pdf_rejects_keyword_spoof_that_cannot_be_parsed(tmp_path: Path) -> None:
    path = tmp_path / "spoofed.pdf"
    path.write_bytes(
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\nstartxref\n0\n%%EOF\n"
    )

    result = inspect_pdf_smoke(path)

    assert result["passed"] is False
    assert "pdf_parse" in _failed_check_names(result)


def test_pdf_rejects_valid_zero_page_document(tmp_path: Path) -> None:
    path = tmp_path / "zero-pages.pdf"
    _write_pdf(path, pages=0)

    result = inspect_pdf_smoke(path)

    assert result["passed"] is False
    assert result["stats"]["pages"] == 0
    assert "page_count" in _failed_check_names(result)


def test_missing_exports_fail_with_stable_public_payload(tmp_path: Path) -> None:
    docx_path = tmp_path / "missing.docx"
    pdf_path = tmp_path / "missing.pdf"

    docx_result = inspect_docx_xml_smoke(docx_path)
    pdf_result = inspect_pdf_smoke(pdf_path)

    assert docx_result == {
        "schema": "mdpaper.docx_xml_smoke.v1",
        "path": str(docx_path),
        "passed": False,
        "checks": [{"name": "file_exists", "passed": False, "details": "MISSING"}],
        "stats": {},
    }
    assert pdf_result == {
        "schema": "mdpaper.pdf_smoke.v1",
        "path": str(pdf_path),
        "passed": False,
        "checks": [{"name": "file_exists", "passed": False, "details": "MISSING"}],
        "stats": {},
    }
