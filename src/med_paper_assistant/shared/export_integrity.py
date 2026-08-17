"""Layer-neutral structural smoke checks for exported DOCX and PDF files.

These helpers deliberately avoid application or infrastructure dependencies so
that export orchestration and pipeline gates can share one implementation.  The
checks are offline and structural: they do not claim that a document is
visually correct or publication-ready.
"""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from defusedxml import ElementTree


def inspect_docx_xml_smoke(docx_path: str | Path) -> dict[str, Any]:
    """Run a lightweight DOCX XML smoke test for export regression.

    This checks the OOXML container and main document body without requiring
    Microsoft Word, LibreOffice, or Pandoc.  It is deliberately structural:
    invalid zip, missing ``word/document.xml``, malformed XML, missing body,
    zero paragraphs, empty text, or leaked raw citation tokens fail.
    """
    path = Path(docx_path)
    result: dict[str, Any] = {
        "schema": "mdpaper.docx_xml_smoke.v1",
        "path": str(path),
        "passed": False,
        "checks": [],
        "stats": {},
    }

    def add_check(name: str, passed: bool, details: str = "") -> None:
        result["checks"].append({"name": name, "passed": passed, "details": details})

    if not path.is_file():
        add_check("file_exists", False, "MISSING")
        return result
    add_check("file_exists", True, "exists")

    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            has_content_types = "[Content_Types].xml" in names
            has_document_xml = "word/document.xml" in names
            add_check("[Content_Types].xml", has_content_types)
            add_check("word/document.xml", has_document_xml)
            if not has_document_xml:
                return result

            try:
                root = ElementTree.fromstring(archive.read("word/document.xml"))
            except ElementTree.ParseError as exc:
                add_check("document_xml_parse", False, str(exc))
                return result
    except zipfile.BadZipFile:
        add_check("zip_container", False, "not a valid DOCX zip container")
        return result

    add_check("zip_container", True, "valid zip")
    add_check("document_xml_parse", True, "valid XML")

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    body = root.find("w:body", ns)
    has_body = body is not None
    add_check("word/body", has_body)
    if body is None:
        return result

    paragraphs = body.findall(".//w:p", ns)
    tables = body.findall(".//w:tbl", ns)
    text_nodes = body.findall(".//w:t", ns)
    text_chars = sum(len(node.text or "") for node in text_nodes)
    plain_text = "".join(node.text or "" for node in text_nodes)
    raw_tokens = [token for token in ("[@", "[[", "]]") if token in plain_text]
    result["stats"] = {
        "paragraphs": len(paragraphs),
        "tables": len(tables),
        "text_nodes": len(text_nodes),
        "text_chars": text_chars,
        "raw_citation_tokens": raw_tokens,
    }
    add_check("paragraphs", len(paragraphs) > 0, f"{len(paragraphs)} paragraph(s)")
    add_check("text", text_chars > 0, f"{text_chars} text character(s)")
    add_check(
        "raw_citation_tokens",
        not raw_tokens,
        "none" if not raw_tokens else ", ".join(raw_tokens),
    )

    result["passed"] = all(check["passed"] for check in result["checks"])
    return result


def inspect_pdf_smoke(pdf_path: str | Path) -> dict[str, Any]:
    """Run a lightweight PDF structural smoke test for export success."""
    path = Path(pdf_path)
    result: dict[str, Any] = {
        "schema": "mdpaper.pdf_smoke.v1",
        "path": str(path),
        "passed": False,
        "checks": [],
        "stats": {},
    }

    def add_check(name: str, passed: bool, details: str = "") -> None:
        result["checks"].append({"name": name, "passed": passed, "details": details})

    if not path.is_file():
        add_check("file_exists", False, "MISSING")
        return result
    add_check("file_exists", True, "exists")

    try:
        data = path.read_bytes()
    except OSError as exc:
        add_check("readable", False, str(exc))
        return result

    result["stats"] = {"bytes": len(data)}
    add_check("non_empty", len(data) >= 16, f"{len(data)} bytes")
    add_check("pdf_header", data.startswith(b"%PDF-"))
    add_check("pdf_trailer", b"%%EOF" in data[-2048:])
    add_check("startxref", b"startxref" in data[-4096:])
    add_check("objects", b" obj" in data and b"endobj" in data)
    add_check("catalog", b"/Catalog" in data)
    add_check("pages_tree", b"/Pages" in data)

    try:
        from pypdf import PdfReader  # type: ignore[import-untyped]
    except ModuleNotFoundError:
        result["stats"]["pages"] = "not_checked"
    else:
        try:
            reader = PdfReader(BytesIO(data), strict=False)
            page_count = len(reader.pages)
        except Exception as exc:
            add_check("pdf_parse", False, str(exc))
        else:
            result["stats"]["pages"] = page_count
            add_check("pdf_parse", True, f"{page_count} page(s)")
            add_check("page_count", page_count > 0, f"{page_count} page(s)")

    result["passed"] = all(check["passed"] for check in result["checks"])
    return result
