"""Tests for PipelineGateValidator — hard gate enforcement."""

import base64
import hashlib
import json
import zipfile

import pytest
import yaml
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from med_paper_assistant.application.content_integrity import ContentIntegrityInspector
from med_paper_assistant.infrastructure.external import approval_signatures
from med_paper_assistant.infrastructure.external.approval_signatures import (
    APPROVAL_PUBLIC_KEYS_ENV,
    CONCEPT_APPROVAL_SCHEMA,
    REVIEW_APPROVAL_SCHEMA,
    canonical_external_approval_payload,
)
from med_paper_assistant.infrastructure.external.content_integrity import (
    C2paProvenanceAdapter,
    ConservativeVisibleWatermarkHeuristic,
    RemoveAiWatermarksInspectionAdapter,
)
from med_paper_assistant.infrastructure.persistence.autonomous_audit_loop import (
    AuditLoopConfig,
    AutonomousAuditLoop,
    Severity,
)
from med_paper_assistant.infrastructure.persistence.data_artifact_tracker import DataArtifactTracker
from med_paper_assistant.infrastructure.persistence.pipeline_gate_validator import (
    GateCheck,
    GateResult,
    PipelineGateValidator,
    derive_reference_source_revision,
)


@pytest.fixture
def project_dir(tmp_path):
    """Create a minimal project directory structure."""
    p = tmp_path / "test-project"
    for d in ["drafts", "references", "data", "results", ".audit", ".memory", "exports"]:
        (p / d).mkdir(parents=True)
    return p


@pytest.fixture
def validator(project_dir):
    return PipelineGateValidator(project_dir)


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _configure_approval_signer(monkeypatch) -> Ed25519PrivateKey:
    """Configure only a test public key; private material never enters production."""
    private_key = Ed25519PrivateKey.generate()
    monkeypatch.setenv(
        APPROVAL_PUBLIC_KEYS_ENV,
        json.dumps({"test-trusted-host": _base64url(private_key.public_key().public_bytes_raw())}),
    )
    return private_key


def _sign_approval_receipt(
    receipt: dict[str, object], private_key: Ed25519PrivateKey
) -> dict[str, object]:
    receipt["signature"] = {
        "algorithm": "Ed25519",
        "encoding": "base64url",
        "key_id": "test-trusted-host",
        "value": "",
    }
    signature = private_key.sign(canonical_external_approval_payload(receipt))
    signature_block = receipt["signature"]
    assert isinstance(signature_block, dict)
    signature_block["value"] = _base64url(signature)
    return receipt


def _add_prerequisites(project_dir, up_to_phase: int):
    """Add prerequisite artifacts needed so that validate_phase(up_to_phase) won't
    fail on prerequisite checks.

    Uses the same numeric comparison as _check_prerequisites in production code.
    Phase 65 (Evolution Gate) works correctly because 65 >= 7 (manuscript) and
    65 >= 9 (scorecard) are both True, while 65 == 11 (exports) is False.
    """
    if up_to_phase >= 2:
        pj = project_dir / "project.json"
        if not pj.is_file():
            pj.write_text('{"slug": "test"}')
    if up_to_phase >= 3:
        # Must meet paper-type minimum (default original-research = 20)
        refs = project_dir / "references"
        for i in range(20):
            ref_dir = refs / f"ref-{i}"
            ref_dir.mkdir(parents=True, exist_ok=True)
            meta = ref_dir / "metadata.json"
            if not meta.is_file():
                meta.write_text(json.dumps({"pmid": f"0000{i}", "title": f"Reference {i}"}))
    if up_to_phase >= 4:
        concept = project_dir / "concept.md"
        if not concept.is_file():
            concept.write_text("# NOVELTY\n\nNew idea\n\n# KEY SELLING POINTS\n\n- Point A")
        concept_review = project_dir / ".audit" / "concept-review.yaml"
        if not concept_review.is_file():
            concept_review.write_text(
                "metadata:\n"
                "  generated_at: '2026-01-01T00:00:00'\n"
                "review:\n"
                "  readiness: ready\n"
                "research_question:\n"
                "  canonical_question: Does intervention X improve outcome Y?\n"
                "claims_required:\n"
                "  - id: claim-1\n"
                "    text: Intervention X improves outcome Y.\n"
                "protected_content:\n"
                "  novelty_statement_locked:\n"
                "    present: true\n"
                "  selling_points_locked:\n"
                "    present: true\n"
            )
        concept_validation = project_dir / ".audit" / "concept-validation.md"
        if not concept_validation.is_file():
            concept_validation.write_text("# Concept Validation")
    if up_to_phase >= 5:
        concept = project_dir / "concept.md"
        if not concept.is_file():
            concept.write_text("# NOVELTY\n\nNew idea\n\n# KEY SELLING POINTS\n\n- Point A")
    if up_to_phase >= 7:
        ms = project_dir / "drafts" / "manuscript.md"
        if not ms.is_file():
            ms.write_text("# Manuscript\n\nBody text.\n\n## References\n\n")
    if up_to_phase >= 9:
        sc = project_dir / ".audit" / "quality-scorecard.md"
        if not sc.is_file():
            sc.write_text("# Scorecard")
    # Phase 8+ needs completed review loop (Phase 7 prerequisite)
    if up_to_phase >= 8:
        if not (project_dir / ".audit" / "audit-loop-review.json").is_file():
            _complete_review_loop(project_dir, rounds=2)
    if up_to_phase == 11:
        exports = project_dir / "exports"
        exports.mkdir(parents=True, exist_ok=True)
        _write_minimal_docx(exports / "paper.docx")
        _write_minimal_pdf(exports / "paper.pdf")
        audit = project_dir / ".audit"
        audit_timestamp = "2026-01-01T00:00:00"
        (audit / "pipeline-run-20260101.md").write_text(
            "# Pipeline Run\n"
            "## D7 retrospective: Review Retrospective\nReview retro\n"
            "## D8 retrospective: EQUATOR Retrospective\nEQUATOR retro\n"
        )
        (audit / "hook-effectiveness.md").write_text("# Hook Effectiveness\n")
        existing = (audit / "evolution-log.jsonl").read_text(encoding="utf-8")
        if "meta_learning" not in existing:
            (audit / "evolution-log.jsonl").write_text(
                existing
                + json.dumps(
                    {
                        "schema": "mdpaper.meta_learning_event.v1",
                        "event": "meta_learning",
                        "timestamp": audit_timestamp,
                        "source_tool": "run_meta_learning",
                        "audit_timestamp": audit_timestamp,
                        "run_number": 1,
                        "adjustments_count": 0,
                        "lessons_count": 0,
                        "suggestions_count": 0,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
        (audit / "meta-learning-audit.yaml").write_text(
            yaml.dump(
                [
                    {
                        "schema": "mdpaper.meta_learning_audit.v2",
                        "timestamp": audit_timestamp,
                        "source_tool": "run_meta_learning",
                        "analysis_steps": _analysis_steps(),
                        "run_number": 1,
                        "adjustments_count": 0,
                        "lessons_count": 0,
                        "suggestions_count": 0,
                        "adjustments": [],
                        "lessons": [],
                        "suggestions": [],
                    }
                ],
                default_flow_style=False,
            ),
            encoding="utf-8",
        )


def _write_minimal_docx(path):
    """Write a minimal structurally valid DOCX fixture."""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types></Types>")
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:r><w:t>Hello</w:t></w:r></w:p></w:body>"
            "</w:document>",
        )


def _write_minimal_pdf(path):
    """Write a minimal parseable one-page PDF fixture."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] /Resources << >> >>",
    ]
    payload = b"%PDF-1.4\n"
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(payload))
        payload += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_offset = len(payload)
    payload += f"xref\n0 {len(objects) + 1}\n".encode()
    payload += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        payload += f"{offset:010d} 00000 n \n".encode()
    payload += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
    ).encode()
    path.write_bytes(payload)


def _analysis_steps():
    return {f"D{i}": {"status": "completed"} for i in range(1, 10)}


def _write_reference_analysis_receipt(
    ref_dir,
    pmid: str,
    *,
    fulltext_ingested: bool = False,
) -> None:
    metadata_path = ref_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update(
        {
            "analysis_completed": True,
            "analysis_source_tool": "save_reference_analysis",
            "fulltext_ingested": fulltext_ingested,
            "fulltext_unavailable_reason": "not_open_access" if not fulltext_ingested else "",
            "asset_aware_doc_id": f"doc-{pmid}" if fulltext_ingested else None,
            "fulltext_sections": ["Methods", "Results"] if fulltext_ingested else [],
        }
    )
    source_valid, _, source_revision, source_kind = derive_reference_source_revision(
        ref_dir, metadata
    )
    if not source_valid:
        source_revision = "0" * 64
        source_kind = "asset-aware"
    analysis = {
        "schema": "mdpaper.reference_analysis.v1",
        "source_tool": "save_reference_analysis",
        "pmid": pmid,
        "summary": "Structured evidence analysis for the saved reference.",
        "methodology": "The study design and analysis methods were appraised.",
        "key_findings": "Findings were mapped to bounded manuscript claims.",
        "limitations": "Limitations and applicability were recorded.",
        "usage_sections": ["Introduction", "Discussion"],
        "relevance_score": 4,
        "source_revision_sha256": source_revision,
        "source_kind": source_kind,
        "analyzed_at": "2026-08-17T00:00:00+00:00",
    }
    analysis_path = ref_dir / "analysis.json"
    analysis_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    metadata.update(
        {
            "analysis_artifact_sha256": hashlib.sha256(analysis_path.read_bytes()).hexdigest(),
            "analysis_completed_at": analysis["analyzed_at"],
            "analysis_source_revision_sha256": source_revision,
            "analysis_summary": analysis["summary"],
            "usage_sections": analysis["usage_sections"],
        }
    )
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")


def _write_asset_aware_reference_receipt(ref_dir, pmid: str) -> None:
    """Create one valid Asset-Aware extraction and its source-bound analysis."""
    asset_dir = ref_dir / "artifacts" / "asset-aware"
    asset_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = asset_dir / "sections.md"
    artifact_path.write_text(
        "# Methods\n\nSubstantive extracted methods.\n\n# Results\n\nSubstantive findings.\n",
        encoding="utf-8",
    )
    artifact_raw = artifact_path.read_bytes()
    artifacts = [
        {
            "path": "sections.md",
            "sha256": hashlib.sha256(artifact_raw).hexdigest(),
            "bytes": len(artifact_raw),
        }
    ]
    revision_payload = {
        "asset_aware_doc_id": f"doc-{pmid}",
        "fulltext_sections": ["Methods", "Results"],
        "artifacts": artifacts,
    }
    source_revision = hashlib.sha256(
        json.dumps(
            revision_payload,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    receipt_path = asset_dir / "receipt.json"
    receipt_path.write_text(
        json.dumps(
            {
                "schema": "mdpaper.asset_aware_fulltext.v1",
                "source_tool": "asset-aware",
                "asset_aware_doc_id": f"doc-{pmid}",
                "fulltext_sections": ["Methods", "Results"],
                "completed_at": "2026-08-17T00:00:00+00:00",
                "source_revision_sha256": source_revision,
                "artifacts": artifacts,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    metadata_path = ref_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update(
        {
            "fulltext_ingested": True,
            "asset_aware_doc_id": f"doc-{pmid}",
            "fulltext_sections": ["Methods", "Results"],
            "fulltext_receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        }
    )
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    _write_reference_analysis_receipt(ref_dir, pmid, fulltext_ingested=True)


def _review_drafts_hash(project_dir) -> str:
    digest = hashlib.sha256()
    manuscript = project_dir / "drafts" / "manuscript.md"
    draft_files = (
        [manuscript] if manuscript.is_file() else sorted((project_dir / "drafts").glob("*.md"))
    )
    for draft_file in draft_files:
        digest.update(draft_file.name.encode("utf-8"))
        digest.update(draft_file.read_bytes())
    return digest.hexdigest() if draft_files else ""


def _write_review_artifacts(project_dir, rounds: int):
    audit = project_dir / ".audit"
    for i in range(1, rounds + 1):
        report = (
            "---\nmajor: 1\nminor: 0\noptional: 0\n---\n"
            f"# Round {i} Review\n\n"
            "## Methodology assessment\n"
            "The methodology reviewer identified one reproducibility concern.\n\n"
            "## Clinical domain assessment\n"
            "The domain reviewer checked whether the interpretation matched the study setting.\n\n"
            "## Statistical assessment\n"
            "The statistic reviewer checked estimates, uncertainty, and reporting choices.\n\n"
            "## Major issues\n"
            "- major: Clarify the analysis rationale and its evidentiary support.\n\n"
            + "Additional reviewer analysis explains the evidence and bounded correction. "
            * 55
        )
        (audit / f"review-report-{i}.md").write_text(report, encoding="utf-8")
        (audit / f"author-response-{i}.md").write_text(
            f"# Round {i} Response\n\n"
            "ACCEPT — Changed the manuscript to clarify the analysis rationale; "
            "the revision is supported by the recorded evidence and reference audit.\n",
            encoding="utf-8",
        )
        (audit / f"equator-compliance-{i}.md").write_text(
            f"# Round {i} EQUATOR\n\n"
            "- [x] Title and abstract\n"
            "- [x] Background and objectives\n"
            "- [x] Methods and setting\n"
            "- [x] Results and uncertainty\n"
            "- [x] Discussion and limitations\n",
            encoding="utf-8",
        )


def _complete_review_loop(project_dir, rounds: int, *, terminal: str = "quality_met") -> None:
    audit = project_dir / ".audit"
    drafts = project_dir / "drafts"
    audit.mkdir(parents=True, exist_ok=True)
    drafts.mkdir(parents=True, exist_ok=True)
    manuscript = drafts / "manuscript.md"
    if not manuscript.is_file():
        manuscript.write_text("# Manuscript\n\nInitial evidence-grounded text.\n", encoding="utf-8")

    _write_review_artifacts(project_dir, rounds)
    config = AuditLoopConfig(
        min_rounds=2,
        max_rounds=rounds if terminal == "max_rounds" else max(3, rounds),
        quality_threshold=7.0,
        context="review",
    )
    loop = AutonomousAuditLoop(audit, config=config)
    events: list[dict[str, object]] = []
    for round_num in range(1, rounds + 1):
        start_hash = _review_drafts_hash(project_dir)
        loop.start_round(artifact_hash=start_hash)
        issue_index = loop.record_issue(
            hook_id="R1",
            severity=Severity.MAJOR,
            description=f"Round {round_num} review issue",
            suggested_fix="Clarify the evidence-grounded analysis rationale",
        )
        manuscript.write_text(
            manuscript.read_text(encoding="utf-8")
            + f"\nRound {round_num} revision clarifies the analysis rationale.\n",
            encoding="utf-8",
        )
        loop.record_fix(issue_index, "author_revision", True)
        final_round = round_num == rounds
        score = 8.0 if final_round and terminal == "quality_met" else 6.0
        scores = {dimension: score for dimension in config.dimension_weights}
        verdict = loop.complete_round(scores, artifact_hash=_review_drafts_hash(project_dir))
        events.append(
            {
                "event": "review_round",
                "round": round_num,
                "verdict": verdict.value,
                "scores": scores,
                "weighted_score": score,
                "timestamp": f"2026-08-17T00:00:0{round_num}",
            }
        )

    evolution_log = audit / "evolution-log.jsonl"
    existing = evolution_log.read_text(encoding="utf-8") if evolution_log.is_file() else ""
    evolution_log.write_text(
        existing + "".join(json.dumps(event) + "\n" for event in events),
        encoding="utf-8",
    )


def _approve_required_sections(project_dir):
    """Persist explicit approval for canonical manuscript sections."""
    checkpoint = project_dir / ".audit" / "checkpoint.json"
    checkpoint.write_text(
        json.dumps(
            {
                "section_progress": {
                    "Abstract": {"approval_status": "approved"},
                    "Introduction": {"approval_status": "approved"},
                    "Methods": {"approval_status": "approved"},
                    "Results": {"approval_status": "approved"},
                    "Discussion": {"approval_status": "approved"},
                }
            }
        )
    )


def _record_asset_review(
    project_dir,
    asset_type: str,
    asset_path: str,
    caption: str,
):
    tracker = DataArtifactTracker(project_dir / ".audit", project_dir)
    integrity = ContentIntegrityInspector(
        provenance_inspector=C2paProvenanceAdapter(),
        visible_watermark_inspector=ConservativeVisibleWatermarkHeuristic(),
        removal_package_inspector=RemoveAiWatermarksInspectionAdapter(),
    ).inspect(project_dir / asset_path, asset_path=asset_path)
    integrity_receipt = tracker.record_content_integrity_receipt(
        asset_type=asset_type,
        asset_path=asset_path,
        receipt=integrity.to_dict(),
    )
    tracker.record_asset_review(
        asset_type=asset_type,
        asset_path=asset_path,
        observations=["Observed primary grouping", "Observed displayed outcome summary"],
        rationale="Caption aligns with the visible content and intended manuscript reference.",
        proposed_caption=caption,
        evidence_excerpt="verified during test",
        content_integrity_receipt_id=integrity_receipt["id"],
    )


class TestGateResult:
    def test_critical_failures(self):
        result = GateResult(
            phase=0,
            phase_name="Test",
            checks=[
                GateCheck(name="a", description="", passed=True),
                GateCheck(name="b", description="fail", passed=False, severity="CRITICAL"),
                GateCheck(name="c", description="warn", passed=False, severity="WARNING"),
            ],
            passed=False,
        )
        assert len(result.critical_failures) == 1
        assert len(result.warnings) == 1

    def test_to_markdown(self):
        result = GateResult(
            phase=7,
            phase_name="Review",
            checks=[GateCheck(name="test", description="desc", passed=False)],
            passed=False,
            timestamp="2026-01-01T00:00:00",
        )
        md = result.to_markdown()
        assert "❌ FAILED" in md
        assert "Phase 7" in md


class TestPhase0:
    def test_fail_no_journal_profile(self, validator):
        r = validator.validate_phase(0)
        assert not r.passed

    def test_fail_no_source_material_scan(self, validator, project_dir):
        (project_dir / "journal-profile.yaml").write_text("type: original")
        r = validator.validate_phase(0)
        assert not r.passed
        assert ".audit/source-materials.yaml" in r.missing

    def test_pass_with_journal_profile(self, validator, project_dir):
        (project_dir / "journal-profile.yaml").write_text("type: original")
        (project_dir / ".audit" / "source-materials.yaml").write_text(
            "schema: mdpaper.source_materials.v1\nsummary:\n  total_candidates: 0\n"
        )
        r = validator.validate_phase(0)
        assert r.passed


class TestPhase1:
    def test_pass_with_dirs(self, validator):
        r = validator.validate_phase(1)
        assert r.passed  # fixture creates all dirs

    def test_fail_missing_dir(self, project_dir):
        import shutil

        shutil.rmtree(project_dir / ".audit")
        v = PipelineGateValidator(project_dir)
        r = v.validate_phase(1)
        assert not r.passed


class TestPhase2:
    def test_fail_insufficient_refs(self, validator):
        r = validator.validate_phase(2)
        assert not r.passed
        ref_check = next(c for c in r.checks if c.name == "references_count")
        assert "0/" in ref_check.details  # "0/20 references found"

    def test_pass_with_refs_default_paper_type(self, validator, project_dir):
        """Default paper type is original-research, minimum 20 refs."""
        (project_dir / "project.json").write_text('{"slug": "test"}')
        for i in range(20):
            ref_dir = project_dir / "references" / f"ref-{i}"
            ref_dir.mkdir(parents=True)
            (ref_dir / "metadata.json").write_text(
                json.dumps({"pmid": f"0000{i}", "title": f"Reference {i}"})
            )
        r = validator.validate_phase(2)
        assert r.passed

    def test_fail_below_paper_type_minimum(self, validator, project_dir):
        """10 refs is below the 20 minimum for original-research."""
        (project_dir / "project.json").write_text('{"slug": "test"}')
        for i in range(10):
            ref_dir = project_dir / "references" / f"ref-{i}"
            ref_dir.mkdir(parents=True)
            (ref_dir / "metadata.json").write_text(
                json.dumps({"pmid": f"0000{i}", "title": f"Reference {i}"})
            )
        r = validator.validate_phase(2)
        assert not r.passed
        ref_check = next(c for c in r.checks if c.name == "references_count")
        assert "need 10 more" in ref_check.details

    def test_case_report_lower_minimum(self, validator, project_dir):
        """Case reports only need 8 refs (from journal-profile.yaml)."""
        import yaml

        (project_dir / "project.json").write_text('{"slug": "test"}')
        (project_dir / "journal-profile.yaml").write_text(
            yaml.dump({"paper": {"type": "case-report"}})
        )
        for i in range(8):
            ref_dir = project_dir / "references" / f"ref-{i}"
            ref_dir.mkdir(parents=True)
            (ref_dir / "metadata.json").write_text(
                json.dumps({"pmid": f"0000{i}", "title": f"Reference {i}"})
            )
        v = PipelineGateValidator(project_dir)
        r = v.validate_phase(2)
        assert r.passed

    def test_systematic_review_higher_minimum(self, validator, project_dir):
        """Systematic reviews need 40 refs — 20 is insufficient."""
        import yaml

        (project_dir / "project.json").write_text('{"slug": "test"}')
        (project_dir / "journal-profile.yaml").write_text(
            yaml.dump({"paper": {"type": "systematic-review"}})
        )
        for i in range(20):
            ref_dir = project_dir / "references" / f"ref-{i}"
            ref_dir.mkdir(parents=True)
            (ref_dir / "metadata.json").write_text(
                json.dumps({"pmid": f"0000{i}", "title": f"Reference {i}"})
            )
        v = PipelineGateValidator(project_dir)
        r = v.validate_phase(2)
        assert not r.passed
        ref_check = next(c for c in r.checks if c.name == "references_count")
        assert "systematic-review" in ref_check.description

    def test_journal_profile_override_minimum(self, validator, project_dir):
        """journal-profile.yaml minimum_reference_limits overrides defaults."""
        import yaml

        (project_dir / "project.json").write_text('{"slug": "test"}')
        profile = {
            "paper": {"type": "original-research"},
            "references": {"minimum_reference_limits": {"original-research": 25}},
        }
        (project_dir / "journal-profile.yaml").write_text(yaml.dump(profile))
        for i in range(22):
            ref_dir = project_dir / "references" / f"ref-{i}"
            ref_dir.mkdir(parents=True)
            (ref_dir / "metadata.json").write_text(
                json.dumps({"pmid": f"0000{i}", "title": f"Reference {i}"})
            )
        v = PipelineGateValidator(project_dir)
        r = v.validate_phase(2)
        assert not r.passed  # 22 < 25

    def test_legacy_flat_md_refs_require_structured_migration(self, validator, project_dir):
        """Arbitrary Markdown cannot satisfy bibliographic integrity."""
        (project_dir / "project.json").write_text('{"slug": "test"}')
        # Use letter type with low minimum (5) for easy testing
        import yaml

        (project_dir / "journal-profile.yaml").write_text(yaml.dump({"paper": {"type": "letter"}}))
        for i in range(5):
            (project_dir / "references" / f"ref-{i}.md").write_text(f"# Ref {i}")
        v = PipelineGateValidator(project_dir)
        r = v.validate_phase(2)
        assert not r.passed
        integrity = next(check for check in r.checks if check.name == "references_integrity")
        assert "require structured migration" in integrity.details

    def test_forged_verified_reference_is_not_counted(self, validator, project_dir):
        """A verified label without immutable PubMed provenance must fail closed."""
        (project_dir / "project.json").write_text('{"slug": "test"}')
        for i in range(20):
            ref_dir = project_dir / "references" / f"ref-{i}"
            ref_dir.mkdir(parents=True)
            metadata = {"pmid": f"0000{i}", "title": f"Reference {i}"}
            if i == 0:
                metadata.update(
                    {
                        "verified": True,
                        "trust_level": "verified",
                        "data_source": "pubmed_mcp_api",
                    }
                )
            (ref_dir / "metadata.json").write_text(json.dumps(metadata))

        result = validator.validate_phase(2)

        assert not result.passed
        integrity = next(check for check in result.checks if check.name == "references_integrity")
        assert "lacks PubMed provenance" in integrity.details

    def test_duplicate_pmid_cannot_inflate_reference_count(self, validator, project_dir):
        """Directory count and citation aliases cannot turn one paper into five."""
        (project_dir / "project.json").write_text('{"slug": "test"}')
        (project_dir / "journal-profile.yaml").write_text(
            yaml.safe_dump({"paper": {"type": "letter"}})
        )
        for i in range(5):
            ref_dir = project_dir / "references" / f"copy-{i}"
            ref_dir.mkdir(parents=True)
            (ref_dir / "metadata.json").write_text(
                json.dumps(
                    {
                        "pmid": "12345678",
                        "title": "The same paper in every directory",
                        "citation_key": f"alias-{i}",
                    }
                )
            )

        result = validator.validate_phase(2)

        assert not result.passed
        count = next(check for check in result.checks if check.name == "references_count")
        integrity = next(check for check in result.checks if check.name == "references_integrity")
        assert count.details.startswith("1/5")
        assert "duplicate identity pmid:12345678" in integrity.details

    def test_citation_key_only_is_not_a_bibliographic_identity(self, validator, project_dir):
        ref_dir = project_dir / "references" / "alias-only"
        ref_dir.mkdir(parents=True)
        (ref_dir / "metadata.json").write_text(
            json.dumps({"citation_key": "invented2026", "title": "Invented reference"})
        )

        _, invalid, _ = validator._reference_records(project_dir / "references")

        assert invalid == ["alias-only: no stable reference identity"]

    def test_matching_verified_labels_without_raw_payload_fail_closed(self, validator, project_dir):
        """An attacker can recompute labels/hashes, but cannot omit persisted source evidence."""
        pmid = "12345678"
        title = "Fabricated verified paper"
        retrieved_at = "2026-08-17T00:00:00+00:00"
        source_url = f"http://127.0.0.1:8765/api/cached_article/{pmid}"
        payload_hash = "a" * 64
        ref_dir = project_dir / "references" / pmid
        ref_dir.mkdir(parents=True)
        (ref_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "pmid": pmid,
                    "title": title,
                    "verified": True,
                    "trust_level": "verified",
                    "data_source": "pubmed_mcp_api",
                    "retrieved_at": retrieved_at,
                    "source_url": source_url,
                    "payload_hash": payload_hash,
                    "provenance": [
                        {
                            "event": "pubmed_mcp_fetch",
                            "source": "pubmed",
                            "data_source": "pubmed_mcp_api",
                            "requested_pmid": pmid,
                            "retrieved_at": retrieved_at,
                            "source_url": source_url,
                            "payload_hash": payload_hash,
                        }
                    ],
                }
            )
        )

        records, invalid, _ = validator._reference_records(project_dir / "references")

        assert not records
        assert "missing its PubMed transport payload" in invalid[0]

        metadata = json.loads((ref_dir / "metadata.json").read_text(encoding="utf-8"))
        transport_payload = {"pmid": pmid, "title": title}
        actual_hash = hashlib.sha256(
            json.dumps(
                transport_payload,
                allow_nan=False,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        attacker_url = f"https://attacker.invalid/api/cached_article/{pmid}"
        metadata.update(
            {
                "source_url": attacker_url,
                "payload_hash": actual_hash,
                "pubmed_transport_payload": transport_payload,
            }
        )
        metadata["provenance"][0].update({"source_url": attacker_url, "payload_hash": actual_hash})
        (ref_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

        records, invalid, _ = validator._reference_records(project_dir / "references")

        assert not records
        assert "configured trusted endpoint" in invalid[0]


class TestWorkflowModeShortCircuit:
    def test_library_wiki_skips_manuscript_phase_gates(self, project_dir):
        (project_dir / "project.json").write_text(
            json.dumps({"slug": "test", "workflow_mode": "library-wiki"})
        )

        validator = PipelineGateValidator(project_dir)
        result = validator.validate_phase(7)

        assert result.passed
        check = next(c for c in result.checks if c.name == "workflow_mode:library-wiki")
        assert check.passed

        phase_two = validator.validate_phase(2)
        assert not phase_two.passed
        ref_check = next(c for c in phase_two.checks if c.name == "references_count")
        assert "need 20 more" in ref_check.details


class TestPhase3And4:
    def test_phase3_fails_without_concept_review_artifact(self, validator, project_dir):
        _add_prerequisites(project_dir, up_to_phase=3)
        (project_dir / "concept.md").write_text(
            "# NOVELTY\n\nQuestion\n\n# KEY SELLING POINTS\n\n- Point A"
        )

        r = validator.validate_phase(3)

        assert not r.passed
        review_check = next(c for c in r.checks if c.name == "audit:concept-review.yaml")
        assert not review_check.passed

    def test_phase4_fails_without_complete_concept_review(self, validator, project_dir):
        _add_prerequisites(project_dir, up_to_phase=3)
        (project_dir / ".audit" / "concept-review.yaml").write_text(
            "review:\n  readiness: ready\nclaims_required: []\n"
        )
        (project_dir / "manuscript-plan.yaml").write_text("title: draft\n")

        r = validator.validate_phase(4)

        assert not r.passed
        prereq_check = next(c for c in r.checks if c.name == "prereq:audit:concept-review.yaml")
        assert not prereq_check.passed

    def test_phase4_passes_with_complete_concept_review(self, validator, project_dir):
        _add_prerequisites(project_dir, up_to_phase=4)
        (project_dir / "manuscript-plan.yaml").write_text("title: draft\n")

        r = validator.validate_phase(4)

        assert r.passed

    def test_phase3_blocks_revise_readiness_without_manual_override(self, validator, project_dir):
        _add_prerequisites(project_dir, up_to_phase=4)
        (project_dir / ".audit" / "concept-review.yaml").write_text(
            "metadata:\n"
            "  generated_at: '2026-01-01T00:00:00'\n"
            "review:\n"
            "  readiness: revise\n"
            "research_question:\n"
            "  canonical_question: Does intervention X improve outcome Y?\n"
            "claims_required:\n"
            "  - id: claim-1\n"
            "    text: Intervention X improves outcome Y.\n"
            "protected_content:\n"
            "  novelty_statement_locked:\n"
            "    present: true\n"
            "  selling_points_locked:\n"
            "    present: true\n"
        )

        r = validator.validate_phase(3)

        assert not r.passed
        decision_check = next(c for c in r.checks if c.name == "concept-review-decision")
        assert decision_check.passed is False
        assert "external human approval receipt is missing" in decision_check.details

    def test_phase4_allows_signed_external_override_for_revise_readiness(
        self, validator, project_dir, monkeypatch
    ):
        _add_prerequisites(project_dir, up_to_phase=4)
        review_path = project_dir / ".audit" / "concept-review.yaml"
        review_path.write_text(
            "metadata:\n"
            "  generated_at: '2026-01-01T00:00:00'\n"
            "review:\n"
            "  readiness: revise\n"
            "research_question:\n"
            "  canonical_question: Does intervention X improve outcome Y?\n"
            "claims_required:\n"
            "  - id: claim-1\n"
            "    text: Intervention X improves outcome Y.\n"
            "protected_content:\n"
            "  novelty_statement_locked:\n"
            "    present: true\n"
            "  selling_points_locked:\n"
            "    present: true\n"
        )
        receipt = _sign_approval_receipt(
            {
                "schema": CONCEPT_APPROVAL_SCHEMA,
                "approved_to_proceed": True,
                "approved_at": "2026-08-17T00:00:00+00:00",
                "approved_by": "principal-investigator:pi-001",
                "accepted_readiness": "revise",
                "rationale": "The concept is clinically meaningful despite weak novelty score.",
                "accepted_risks": "Novelty limitations will be disclosed in the manuscript.",
                "mode": "human-collaboration",
                "decision_source": "external-user-confirmation",
                "confirmation_id": "concept-confirmation-0001",
                "project_slug": "test",
                "concept_review_sha256": hashlib.sha256(review_path.read_bytes()).hexdigest(),
                "concept_artifact_sha256": hashlib.sha256(
                    (project_dir / "concept.md").read_bytes()
                ).hexdigest(),
            },
            _configure_approval_signer(monkeypatch),
        )
        (project_dir / ".audit" / "concept-review-override.yaml").write_text(
            yaml.safe_dump(receipt, sort_keys=False)
        )
        (project_dir / "manuscript-plan.yaml").write_text("title: draft\n")

        r = validator.validate_phase(4)

        assert r.passed
        decision_check = next(c for c in r.checks if c.name == "concept-review-ready")
        assert "external approval" in decision_check.details

    def test_concept_override_requires_specific_reviewer_and_current_review_hash(
        self, validator, project_dir, monkeypatch
    ):
        _add_prerequisites(project_dir, up_to_phase=4)
        review_path = project_dir / ".audit" / "concept-review.yaml"
        review = yaml.safe_load(review_path.read_text(encoding="utf-8"))
        review["review"]["readiness"] = "revise"
        review_path.write_text(yaml.safe_dump(review, sort_keys=False), encoding="utf-8")
        approved_review_bytes = review_path.read_bytes()
        override_path = project_dir / ".audit" / "concept-review-override.yaml"
        private_key = _configure_approval_signer(monkeypatch)
        receipt = _sign_approval_receipt(
            {
                "schema": CONCEPT_APPROVAL_SCHEMA,
                "approved_to_proceed": True,
                "approved_at": "2026-08-17T00:00:00+00:00",
                "approved_by": "human",
                "accepted_readiness": "revise",
                "rationale": "Proceed as a scoped interim report with an explicit caveat.",
                "accepted_risks": "The concept needs further novelty validation.",
                "mode": "human-collaboration",
                "decision_source": "external-user-confirmation",
                "confirmation_id": "concept-confirmation-0002",
                "project_slug": "test",
                "concept_review_sha256": hashlib.sha256(review_path.read_bytes()).hexdigest(),
                "concept_artifact_sha256": hashlib.sha256(
                    (project_dir / "concept.md").read_bytes()
                ).hexdigest(),
            },
            private_key,
        )
        override_path.write_text(yaml.safe_dump(receipt), encoding="utf-8")

        generic_result = validator.validate_phase(3)
        generic_check = next(
            check for check in generic_result.checks if check.name == "concept-review-decision"
        )
        assert not generic_check.passed
        assert "specific external reviewer identity" in generic_check.details

        receipt["approved_by"] = "principal-investigator:pi-002"
        _sign_approval_receipt(receipt, private_key)
        override_path.write_text(yaml.safe_dump(receipt), encoding="utf-8")
        assert validator.validate_phase(3).passed

        review_path.write_text(
            review_path.read_text(encoding="utf-8") + "\n# post-approval mutation\n",
            encoding="utf-8",
        )
        stale_result = validator.validate_phase(3)
        stale_check = next(
            check for check in stale_result.checks if check.name == "concept-review-decision"
        )
        assert not stale_check.passed
        assert "stale for the current concept review" in stale_check.details

        review_path.write_bytes(approved_review_bytes)
        concept_path = project_dir / "concept.md"
        concept_path.write_text(
            concept_path.read_text(encoding="utf-8") + "\nPost-approval concept mutation.\n",
            encoding="utf-8",
        )
        stale_concept_result = validator.validate_phase(3)
        stale_concept_check = next(
            check
            for check in stale_concept_result.checks
            if check.name == "concept-review-decision"
        )
        assert not stale_concept_check.passed
        assert "stale for the current concept artifact" in stale_concept_check.details

    def test_ready_concept_does_not_require_crypto_backend(
        self, validator, project_dir, monkeypatch
    ):
        _add_prerequisites(project_dir, up_to_phase=4)

        def missing_backend():
            raise ModuleNotFoundError("cryptography intentionally unavailable")

        monkeypatch.setattr(approval_signatures, "_load_ed25519_backend", missing_backend)

        assert validator.validate_phase(3).passed


class TestPhase5:
    def test_fail_no_manuscript(self, validator):
        r = validator.validate_phase(5)
        assert not r.passed

    def test_fail_missing_sections(self, validator, project_dir):
        (project_dir / "drafts" / "manuscript.md").write_text("# Abstract\n\n## Introduction\n")
        r = validator.validate_phase(5)
        assert not r.passed  # missing Methods, Results, Discussion

    def test_pass_full_manuscript(self, validator, project_dir):
        _add_prerequisites(project_dir, up_to_phase=5)
        content = "\n".join(
            [
                "# Title",
                "## Abstract",
                "text",
                "## Introduction",
                "text",
                "## Methods",
                "text",
                "## Results",
                "text",
                "## Discussion",
                "text",
            ]
        )
        (project_dir / "drafts" / "manuscript.md").write_text(content)
        _approve_required_sections(project_dir)
        r = validator.validate_phase(5)
        assert r.passed

    def test_fail_when_approval_checkpoint_missing(self, validator, project_dir):
        _add_prerequisites(project_dir, up_to_phase=5)
        (project_dir / "drafts" / "manuscript.md").write_text(
            "\n".join(
                [
                    "# Title",
                    "## Abstract",
                    "text",
                    "## Introduction",
                    "text",
                    "## Methods",
                    "text",
                    "## Results",
                    "text",
                    "## Discussion",
                    "text",
                ]
            )
        )

        r = validator.validate_phase(5)
        assert not r.passed
        approval_check = next(c for c in r.checks if c.name == "section_approval")
        assert approval_check.passed is False
        assert "checkpoint.json" in approval_check.details

    def test_fail_when_required_sections_not_all_approved(self, validator, project_dir):
        _add_prerequisites(project_dir, up_to_phase=5)
        (project_dir / "drafts" / "manuscript.md").write_text(
            "\n".join(
                [
                    "# Title",
                    "## Abstract",
                    "text",
                    "## Introduction",
                    "text",
                    "## Methods",
                    "text",
                    "## Results",
                    "text",
                    "## Discussion",
                    "text",
                ]
            )
        )
        (project_dir / ".audit" / "checkpoint.json").write_text(
            json.dumps(
                {
                    "section_progress": {
                        "Abstract": {"approval_status": "approved"},
                        "Introduction": {"approval_status": "approved"},
                        "Methods": {"approval_status": "approved"},
                        "Results": {"approval_status": "pending"},
                    }
                }
            )
        )

        r = validator.validate_phase(5)
        assert not r.passed
        approval_check = next(c for c in r.checks if c.name == "section_approval")
        assert approval_check.passed is False
        assert "Results" in approval_check.details or "Discussion" in approval_check.details

    def test_fail_required_planned_asset_missing_from_manifest(self, validator, project_dir):
        import yaml

        _add_prerequisites(project_dir, up_to_phase=5)
        (project_dir / "manuscript-plan.yaml").write_text(
            yaml.dump(
                {
                    "asset_plan": [
                        {
                            "id": "fig-1",
                            "type": "flow_diagram",
                            "section": "Methods",
                            "caption": "Study flow diagram",
                        }
                    ]
                }
            )
        )
        (project_dir / "drafts" / "manuscript.md").write_text(
            "\n".join(
                [
                    "# Title",
                    "## Abstract",
                    "text",
                    "## Introduction",
                    "text",
                    "## Methods",
                    "See Figure 1.",
                    "## Results",
                    "text",
                    "## Discussion",
                    "text",
                ]
            )
        )

        r = validator.validate_phase(5)
        assert not r.passed
        failed = next(c for c in r.checks if c.name == "asset-plan:fig-1:registered")
        assert failed.passed is False

    def test_fail_required_planned_figure_without_exportable_asset(self, validator, project_dir):
        import yaml

        _add_prerequisites(project_dir, up_to_phase=5)
        (project_dir / "results" / "figures").mkdir(parents=True)
        (project_dir / "results" / "figures" / "study-flow.drawio").write_text("xml")
        (project_dir / "results" / "manifest.json").write_text(
            json.dumps(
                {
                    "figures": [
                        {
                            "number": 1,
                            "filename": "study-flow.drawio",
                            "caption": "Study flow diagram",
                        }
                    ]
                }
            )
        )
        (project_dir / "manuscript-plan.yaml").write_text(
            yaml.dump(
                {
                    "asset_plan": [
                        {
                            "id": "fig-1",
                            "type": "flow_diagram",
                            "section": "Methods",
                            "caption": "Study flow diagram",
                        }
                    ]
                }
            )
        )
        (project_dir / "drafts" / "manuscript.md").write_text(
            "\n".join(
                [
                    "# Title",
                    "## Abstract",
                    "text",
                    "## Introduction",
                    "text",
                    "## Methods",
                    "![Figure 1. Study flow diagram](../results/figures/study-flow.drawio)",
                    "**Figure 1.** Study flow diagram",
                    "See Figure 1.",
                    "## Results",
                    "text",
                    "## Discussion",
                    "text",
                ]
            )
        )

        r = validator.validate_phase(5)
        assert not r.passed
        failed = next(c for c in r.checks if c.name == "asset-plan:fig-1:exportable")
        assert failed.passed is False

    def test_pass_required_planned_assets_when_registered_and_placed(self, validator, project_dir):
        import yaml

        _add_prerequisites(project_dir, up_to_phase=5)
        (project_dir / "results" / "figures").mkdir(parents=True)
        (project_dir / "results" / "tables").mkdir(parents=True)
        (project_dir / "results" / "figures" / "study-flow.drawio").write_text("xml")
        (project_dir / "results" / "figures" / "study-flow.png").write_bytes(b"png")
        (project_dir / "results" / "tables" / "baseline.md").write_text("| a | b |")
        (project_dir / ".audit" / "data-artifacts.yaml").write_text(
            yaml.dump(
                {
                    "artifacts": [
                        {"id": "fig-1", "kind": "figure"},
                        {"id": "table-1", "kind": "table"},
                    ]
                }
            )
        )
        (project_dir / "results" / "manifest.json").write_text(
            json.dumps(
                {
                    "figures": [
                        {
                            "number": 1,
                            "filename": "study-flow.drawio",
                            "caption": "Study flow diagram",
                        }
                    ],
                    "tables": [
                        {
                            "number": 1,
                            "filename": "baseline.md",
                            "caption": "Baseline characteristics of study participants",
                        }
                    ],
                }
            )
        )
        (project_dir / "manuscript-plan.yaml").write_text(
            yaml.dump(
                {
                    "asset_plan": [
                        {
                            "id": "fig-1",
                            "type": "flow_diagram",
                            "section": "Methods",
                            "caption": "Study flow diagram",
                        },
                        {
                            "id": "table-1",
                            "type": "table_one",
                            "section": "Results",
                            "caption": "Baseline characteristics of study participants",
                        },
                    ]
                }
            )
        )
        (project_dir / "drafts" / "manuscript.md").write_text(
            "\n".join(
                [
                    "# Title",
                    "## Abstract",
                    "text",
                    "## Introduction",
                    "text",
                    "## Methods",
                    "![Figure 1. Study flow diagram](../results/figures/study-flow.png)",
                    "**Figure 1.** Study flow diagram",
                    "See Figure 1.",
                    "## Results",
                    "**Table 1.** Baseline characteristics of study participants",
                    "See Table 1 for baseline characteristics.",
                    "## Discussion",
                    "text",
                ]
            )
        )
        _record_asset_review(
            project_dir,
            "figure",
            "results/figures/study-flow.drawio",
            "Study flow diagram",
        )
        _record_asset_review(
            project_dir,
            "table",
            "results/tables/baseline.md",
            "Baseline characteristics of study participants",
        )
        _approve_required_sections(project_dir)

        r = validator.validate_phase(5)
        assert r.passed

    def test_fail_planned_asset_without_review_receipt(self, validator, project_dir):
        import yaml

        _add_prerequisites(project_dir, up_to_phase=5)
        (project_dir / "results" / "figures").mkdir(parents=True)
        (project_dir / "results" / "figures" / "forest.png").write_bytes(b"png")
        (project_dir / ".audit" / "data-artifacts.yaml").write_text(
            yaml.dump(
                {
                    "artifacts": [
                        {
                            "id": "DA-001",
                            "artifact_type": "figure",
                            "output_path": "results/figures/forest.png",
                            "provenance_code": "print('x')",
                        }
                    ]
                }
            )
        )
        (project_dir / "results" / "manifest.json").write_text(
            json.dumps(
                {
                    "figures": [
                        {
                            "number": 1,
                            "filename": "forest.png",
                            "caption": "Forest plot of primary outcome",
                        }
                    ],
                    "tables": [],
                }
            )
        )
        (project_dir / "manuscript-plan.yaml").write_text(
            yaml.dump(
                {
                    "asset_plan": [
                        {
                            "id": "fig-forest",
                            "type": "custom_figure",
                            "section": "Results",
                            "caption": "Forest plot of primary outcome",
                        }
                    ]
                }
            )
        )
        (project_dir / "drafts" / "manuscript.md").write_text(
            "\n".join(
                [
                    "# Title",
                    "## Abstract",
                    "text",
                    "## Introduction",
                    "text",
                    "## Methods",
                    "text",
                    "## Results",
                    "**Figure 1.** Forest plot of primary outcome",
                    "See Figure 1.",
                    "## Discussion",
                    "text",
                ]
            )
        )
        _approve_required_sections(project_dir)

        r = validator.validate_phase(5)
        assert not r.passed
        review_check = next(c for c in r.checks if c.name == "asset-plan:fig-forest:reviewed")
        assert review_check.passed is False
        assert "review" in review_check.details


class TestPhase7:
    """Phase 7 is the most critical gate — tests the review loop enforcement."""

    def test_fail_no_review_artifacts(self, validator):
        """Without any review artifacts, Phase 7 must FAIL."""
        r = validator.validate_phase(7)
        assert not r.passed
        names = [c.name for c in r.critical_failures]
        assert "audit-loop:state" in names
        assert "review:rounds_completed" in names

    def test_fail_partial_round(self, validator, project_dir):
        """Even with loop state but missing artifacts, must FAIL."""
        audit = project_dir / ".audit"
        state = {
            "config": {"max_rounds": 3},
            "rounds": [{"round": 1, "verdict": "continue"}],
        }
        (audit / "audit-loop-review.json").write_text(json.dumps(state))
        # Missing review-report-1.md, author-response-1.md, equator
        r = validator.validate_phase(7)
        assert not r.passed
        names = [c.name for c in r.critical_failures]
        assert "review:review-report-1.md" in names
        assert "review:author-response-1.md" in names

    def test_pass_complete_review(self, validator, project_dir):
        """A state-machine review with revalidated R1-R6 artifacts should PASS."""
        _add_prerequisites(project_dir, up_to_phase=7)
        _complete_review_loop(project_dir, rounds=2)

        r = validator.validate_phase(7)

        assert r.passed
        checks = {check.name: check for check in r.checks}
        assert all(checks[f"review:r{hook_num}-2"].passed for hook_num in range(1, 7))

    def test_fail_when_quality_met_verdict_is_handwritten(self, validator, project_dir):
        """A plausible label cannot replace state-machine score recomputation."""
        _add_prerequisites(project_dir, up_to_phase=7)
        _complete_review_loop(project_dir, rounds=2)
        loop_path = project_dir / ".audit" / "audit-loop-review.json"
        state = json.loads(loop_path.read_text(encoding="utf-8"))
        state["rounds"][-1]["scores"] = {
            dimension: 1.0 for dimension in state["config"]["dimension_weights"]
        }
        state["rounds"][-1]["weighted_avg"] = 1.0
        state["rounds"][-1]["verdict"] = "quality_met"
        loop_path.write_text(json.dumps(state), encoding="utf-8")

        result = validator.validate_phase(7)

        assert not result.passed
        integrity = next(check for check in result.checks if check.name == "review:state_integrity")
        assert "recomputed verdict" in integrity.details

    def test_fail_when_current_manuscript_differs_from_final_reviewed_artifact(
        self, validator, project_dir
    ):
        """A quality verdict cannot be replayed after post-review manuscript edits."""
        _add_prerequisites(project_dir, up_to_phase=7)
        _complete_review_loop(project_dir, rounds=2)
        manuscript = project_dir / "drafts" / "manuscript.md"
        manuscript.write_text(
            manuscript.read_text(encoding="utf-8") + "\nUnreviewed conclusion added later.\n",
            encoding="utf-8",
        )

        result = validator.validate_phase(7)

        assert not result.passed
        current = next(
            check for check in result.checks if check.name == "review:final-artifact-current"
        )
        assert not current.passed
        assert "does not match" in current.details

    def test_review_policy_floor_rejects_lowered_serialized_threshold(self, validator, project_dir):
        """Editing persisted config cannot turn zero scores into quality evidence."""
        _add_prerequisites(project_dir, up_to_phase=7)
        _complete_review_loop(project_dir, rounds=2)
        loop_path = project_dir / ".audit" / "audit-loop-review.json"
        state = json.loads(loop_path.read_text(encoding="utf-8"))
        state["config"]["min_rounds"] = 1
        state["config"]["quality_threshold"] = 0
        loop_path.write_text(json.dumps(state), encoding="utf-8")

        result = validator.validate_phase(7)

        assert not result.passed
        integrity = next(check for check in result.checks if check.name == "review:state_integrity")
        assert "min_rounds must be at least 2" in integrity.details
        assert "quality_threshold must be at least 7.0" in integrity.details

    def test_fail_when_review_artifacts_bypass_r1_r6(self, validator, project_dir):
        """Replacing a reviewed report with a stub invalidates the hard gate."""
        _add_prerequisites(project_dir, up_to_phase=7)
        _complete_review_loop(project_dir, rounds=2)
        (project_dir / ".audit" / "review-report-2.md").write_text(
            "# Handwritten verdict\nLooks good.\n", encoding="utf-8"
        )

        result = validator.validate_phase(7)

        assert not result.passed
        assert any(check.name == "review:r1-2" for check in result.critical_failures)

    def test_fail_closed_when_review_hook_execution_raises(
        self, validator, project_dir, monkeypatch
    ):
        """An unexpected hook exception becomes a failed gate, not an unhandled bypass."""
        from med_paper_assistant.infrastructure.persistence.review_hooks import (
            ReviewHooksEngine,
        )

        _add_prerequisites(project_dir, up_to_phase=7)
        _complete_review_loop(project_dir, rounds=2)

        def fail_hooks(*args, **kwargs):
            raise RuntimeError("simulated hook failure")

        monkeypatch.setattr(ReviewHooksEngine, "run_all", fail_hooks)

        result = validator.validate_phase(7)

        assert not result.passed
        r1 = next(check for check in result.checks if check.name == "review:r1-1")
        assert "hook execution failed: RuntimeError" in r1.details


class TestPhase65:
    def test_fail_no_baseline(self, validator, project_dir):
        r = validator.validate_phase(65)
        assert not r.passed

    def test_pass_with_baseline(self, validator, project_dir):
        _add_prerequisites(project_dir, up_to_phase=65)
        audit = project_dir / ".audit"
        entries = [json.dumps({"event": "baseline", "round": 0})]
        (audit / "evolution-log.jsonl").write_text("\n".join(entries) + "\n")
        (audit / "quality-scorecard.md").write_text("# Scorecard")
        r = validator.validate_phase(65)
        assert r.passed


class TestPhase11:
    def test_skips_git_checks_when_prerequisites_fail(self, validator, project_dir, monkeypatch):
        """Final gate should not run Git subprocesses while earlier gates still fail."""
        import subprocess

        (project_dir / ".git").mkdir()

        def fail_run(*args, **kwargs):
            raise AssertionError("git subprocess should not run")

        monkeypatch.setattr(subprocess, "run", fail_run)

        r = validator.validate_phase(11)
        names = [c.name for c in r.checks]
        assert not r.passed
        assert "git:skipped" in names
        assert "git:clean" not in names

    def test_phase11_reuses_single_status_call_for_clean_and_push(
        self, validator, project_dir, monkeypatch
    ):
        """Phase 11 should avoid multiple slow git status calls."""
        import subprocess

        _add_prerequisites(project_dir, up_to_phase=11)
        (project_dir / ".git").mkdir()
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs))
            if cmd[1] == "status":
                return subprocess.CompletedProcess(
                    cmd,
                    0,
                    stdout="# branch.upstream origin/master\n# branch.ab +0 -0\n",
                    stderr="",
                )
            if cmd[1] == "log":
                return subprocess.CompletedProcess(
                    cmd,
                    0,
                    stdout="abc123 release paper\ndrafts/manuscript.md\n",
                    stderr="",
                )
            raise AssertionError(f"unexpected git command: {cmd}")

        monkeypatch.setattr(subprocess, "run", fake_run)

        r = validator.validate_phase(11)
        names = [c.name for c in r.checks]
        status_calls = [cmd for cmd, _ in calls if cmd[1] == "status"]
        assert "git:clean" in names
        assert "git:pushed" in names
        assert len(status_calls) == 1
        assert all(kwargs["timeout"] == 3 for _, kwargs in calls)
        assert all(kwargs["env"]["GIT_OPTIONAL_LOCKS"] == "0" for _, kwargs in calls)

    def test_phase11_detects_behind_upstream(self, validator, project_dir, monkeypatch):
        """`+0 -N` means local is behind upstream and must not be reported as synced."""
        import subprocess

        _add_prerequisites(project_dir, up_to_phase=11)
        _write_minimal_docx(project_dir / "exports" / "paper.docx")
        _write_minimal_pdf(project_dir / "exports" / "paper.pdf")
        (project_dir / ".git").mkdir()

        def fake_run(cmd, **kwargs):
            if cmd[1] == "status":
                return subprocess.CompletedProcess(
                    cmd,
                    0,
                    stdout="# branch.upstream origin/master\n# branch.ab +0 -3\n",
                    stderr="",
                )
            if cmd[1] == "log":
                return subprocess.CompletedProcess(
                    cmd,
                    0,
                    stdout="abc123 release paper\ndrafts/manuscript.md\n",
                    stderr="",
                )
            raise AssertionError(f"unexpected git command: {cmd}")

        monkeypatch.setattr(subprocess, "run", fake_run)

        r = validator.validate_phase(11)
        pushed_check = next(c for c in r.checks if c.name == "git:pushed")
        assert not pushed_check.passed
        assert "behind" in pushed_check.details

    def test_phase11_allows_missing_upstream(self, validator, project_dir, monkeypatch):
        """Paper-only workflows often have no remote; that should not block delivery."""
        import subprocess

        _add_prerequisites(project_dir, up_to_phase=11)
        (project_dir / ".git").mkdir()

        def fake_run(cmd, **kwargs):
            if cmd[1] == "status":
                return subprocess.CompletedProcess(
                    cmd,
                    0,
                    stdout="# branch.oid abc123\n# branch.head main\n",
                    stderr="",
                )
            if cmd[1] == "log":
                return subprocess.CompletedProcess(
                    cmd,
                    0,
                    stdout="abc123 release paper\ndrafts/manuscript.md\n",
                    stderr="",
                )
            raise AssertionError(f"unexpected git command: {cmd}")

        monkeypatch.setattr(subprocess, "run", fake_run)

        r = validator.validate_phase(11)
        pushed_check = next(c for c in r.checks if c.name == "git:pushed")
        assert r.passed
        assert pushed_check.passed
        assert pushed_check.severity == "INFO"
        assert "optional" in pushed_check.details

    def test_phase11_missing_git_is_advisory(self, validator, project_dir):
        """A manuscript export should not require the user to use Git at all."""
        _add_prerequisites(project_dir, up_to_phase=11)

        r = validator.validate_phase(11)
        repository_check = next(c for c in r.checks if c.name == "git:repository")
        assert r.passed
        assert not repository_check.passed
        assert repository_check.severity == "WARNING"
        assert "optional" in repository_check.details

    def test_phase11_git_timeout_returns_warning(self, validator, project_dir, monkeypatch):
        """A slow Git command should warn instead of hanging or blocking paper delivery."""
        import subprocess

        _add_prerequisites(project_dir, up_to_phase=11)
        (project_dir / ".git").mkdir()

        def slow_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs["timeout"])

        monkeypatch.setattr(subprocess, "run", slow_run)

        r = validator.validate_phase(11)
        error_check = next(c for c in r.checks if c.name == "git:error")
        assert r.passed
        assert not error_check.passed
        assert error_check.severity == "WARNING"
        assert "timed out" in error_check.details


class TestPhase21SourceMaterials:
    def test_pending_primary_source_material_blocks_phase21(self, validator, project_dir):
        (project_dir / "project.json").write_text('{"slug": "test"}')
        for i in range(20):
            ref_dir = project_dir / "references" / f"ref-{i}"
            ref_dir.mkdir(parents=True, exist_ok=True)
            (ref_dir / "metadata.json").write_text(
                json.dumps({"pmid": f"0000{i}", "title": f"Reference {i}"})
            )
            _write_reference_analysis_receipt(ref_dir, f"0000{i}")
        (project_dir / "references" / "fulltext-ingestion-status.md").write_text("ok")
        (project_dir / ".audit" / "source-materials.yaml").write_text(
            yaml.dump(
                {
                    "schema": "mdpaper.source_materials.v1",
                    "materials": [
                        {
                            "id": "source-001",
                            "relative_path": "table.docx",
                            "evidence_priority": "primary_user_material",
                            "ingestion": {
                                "status": "pending_asset_aware",
                                "required": True,
                            },
                        }
                    ],
                }
            )
        )

        r = validator.validate_phase(21)

        assert not r.passed
        assert "source-materials:asset-aware" in r.missing

    def test_ingested_primary_source_material_passes_phase21(self, validator, project_dir):
        (project_dir / "project.json").write_text('{"slug": "test"}')
        for i in range(20):
            ref_dir = project_dir / "references" / f"ref-{i}"
            ref_dir.mkdir(parents=True, exist_ok=True)
            (ref_dir / "metadata.json").write_text(
                json.dumps({"pmid": f"0000{i}", "title": f"Reference {i}"})
            )
            _write_reference_analysis_receipt(ref_dir, f"0000{i}")
        (project_dir / "references" / "fulltext-ingestion-status.md").write_text("ok")
        (project_dir / ".audit" / "source-materials.yaml").write_text(
            yaml.dump(
                {
                    "schema": "mdpaper.source_materials.v1",
                    "materials": [
                        {
                            "id": "source-001",
                            "relative_path": "table.docx",
                            "evidence_priority": "primary_user_material",
                            "ingestion": {
                                "status": "ingested_asset_aware",
                                "asset_aware_doc_id": "doc_123",
                                "required": False,
                            },
                        }
                    ],
                }
            )
        )

        r = validator.validate_phase(21)

        assert r.passed


class TestPhase21Ordering:
    def test_phase21_prerequisites_do_not_require_later_phase_artifacts(
        self, validator, project_dir
    ):
        """Phase 2.1 is encoded as 21 but must not inherit Phase 7/9 prerequisites."""
        (project_dir / "project.json").write_text('{"slug": "test"}')
        refs = project_dir / "references"
        for i in range(20):
            ref_dir = refs / f"ref-{i}"
            ref_dir.mkdir(parents=True, exist_ok=True)
            (ref_dir / "metadata.json").write_text(
                json.dumps({"pmid": f"0000{i}", "title": f"Reference {i}"})
            )
            _write_reference_analysis_receipt(ref_dir, f"0000{i}")

        r = validator.validate_phase(21)
        names = {c.name for c in r.checks}
        assert "prereq:references" in names
        assert "prereq:concept.md" not in names
        assert "prereq:manuscript.md" not in names
        assert "prereq:quality-scorecard" not in names
        assert "prereq:review_completed" not in names

    def test_boolean_only_analysis_claim_fails_closed(self, validator, project_dir):
        """analysis_completed=true is not evidence without a hashed producer artifact."""
        (project_dir / "project.json").write_text('{"slug": "test"}')
        for i in range(20):
            ref_dir = project_dir / "references" / f"ref-{i}"
            ref_dir.mkdir(parents=True, exist_ok=True)
            (ref_dir / "metadata.json").write_text(
                json.dumps(
                    {
                        "pmid": f"0000{i}",
                        "title": f"Reference {i}",
                        "analysis_completed": True,
                        "fulltext_ingested": False,
                        "fulltext_unavailable_reason": "not_open_access",
                    }
                )
            )
        (project_dir / "references" / "fulltext-ingestion-status.md").write_text("recorded")

        result = validator.validate_phase(21)

        assert not result.passed
        analysis = next(check for check in result.checks if check.name == "analysis_coverage")
        assert "analysis.json is missing" in analysis.details

    def test_fulltext_metadata_without_physical_artifact_fails_closed(self, validator, project_dir):
        """Asset-Aware ids/section labels alone cannot prove fulltext ingestion."""
        (project_dir / "project.json").write_text('{"slug": "test"}')
        for i in range(20):
            ref_dir = project_dir / "references" / f"ref-{i}"
            ref_dir.mkdir(parents=True, exist_ok=True)
            (ref_dir / "metadata.json").write_text(
                json.dumps({"pmid": f"0000{i}", "title": f"Reference {i}"})
            )
            _write_reference_analysis_receipt(
                ref_dir,
                f"0000{i}",
                fulltext_ingested=True,
            )
        (project_dir / "references" / "fulltext-ingestion-status.md").write_text("recorded")

        result = validator.validate_phase(21)

        assert not result.passed
        fulltext = next(check for check in result.checks if check.name == "fulltext_evidence")
        assert "without a verifiable source receipt" in fulltext.details

    def test_asset_aware_source_revision_is_recomputed_from_manifest(self, validator, project_dir):
        ref_dir = project_dir / "references" / "12345678"
        ref_dir.mkdir(parents=True)
        metadata_path = ref_dir / "metadata.json"
        metadata_path.write_text(
            json.dumps({"pmid": "12345678", "title": "Receipt-bound extraction"})
        )
        _write_asset_aware_reference_receipt(ref_dir, "12345678")
        receipt_path = ref_dir / "artifacts" / "asset-aware" / "receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["source_revision_sha256"] = "f" * 64
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["fulltext_receipt_sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

        valid, details, _, _ = validator._validate_fulltext_status(ref_dir, metadata)

        assert not valid
        assert "source revision does not match its manifest" in details

    def test_asset_aware_one_byte_artifact_fails_closed(self, validator, project_dir):
        ref_dir = project_dir / "references" / "12345678"
        ref_dir.mkdir(parents=True)
        metadata_path = ref_dir / "metadata.json"
        metadata_path.write_text(json.dumps({"pmid": "12345678", "title": "Tiny fake extraction"}))
        _write_asset_aware_reference_receipt(ref_dir, "12345678")
        (ref_dir / "artifacts" / "asset-aware" / "sections.md").write_bytes(b"x")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        valid, details, _, _ = validator._validate_fulltext_status(ref_dir, metadata)

        assert not valid
        assert "too small" in details

    def test_analysis_is_invalidated_when_metadata_source_revision_changes(
        self, validator, project_dir
    ):
        ref_dir = project_dir / "references" / "12345678"
        ref_dir.mkdir(parents=True)
        metadata_path = ref_dir / "metadata.json"
        metadata_path.write_text(
            json.dumps({"pmid": "12345678", "title": "Metadata-only analysis"})
        )
        _write_reference_analysis_receipt(ref_dir, "12345678")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["fulltext_unavailable_reason"] = "publisher_paywall"
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
        source_valid, _, source_revision, source_kind = validator._validate_fulltext_status(
            ref_dir, metadata
        )

        analysis_valid, details = validator._validate_reference_analysis(
            ref_dir,
            metadata,
            source_revision_sha256=source_revision,
            source_kind=source_kind,
        )

        assert source_valid
        assert not analysis_valid
        assert "stale for the current source revision" in details

    def test_one_character_analysis_field_is_not_substantive(self, validator, project_dir):
        ref_dir = project_dir / "references" / "12345678"
        ref_dir.mkdir(parents=True)
        metadata_path = ref_dir / "metadata.json"
        metadata_path.write_text(json.dumps({"pmid": "12345678", "title": "Shallow analysis"}))
        _write_reference_analysis_receipt(ref_dir, "12345678")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        analysis_path = ref_dir / "analysis.json"
        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        analysis["methodology"] = "x"
        analysis_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
        metadata["analysis_artifact_sha256"] = hashlib.sha256(
            analysis_path.read_bytes()
        ).hexdigest()
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
        source_valid, _, source_revision, source_kind = validator._validate_fulltext_status(
            ref_dir, metadata
        )

        analysis_valid, details = validator._validate_reference_analysis(
            ref_dir,
            metadata,
            source_revision_sha256=source_revision,
            source_kind=source_kind,
        )

        assert source_valid
        assert not analysis_valid
        assert "methodology must contain at least 8" in details


class TestHeartbeat:
    def test_heartbeat_returns_status(self, validator):
        status = validator.get_pipeline_status()
        assert "completion_pct" in status
        assert "phases" in status
        assert len(status["phases"]) == 14

    def test_heartbeat_reflects_progress(self, validator, project_dir):
        # Add Phase 0 artifacts → Phase 0 passes
        (project_dir / "journal-profile.yaml").write_text("type: original")
        (project_dir / ".audit" / "source-materials.yaml").write_text(
            "schema: mdpaper.source_materials.v1\nsummary:\n  total_candidates: 0\n"
        )
        status = validator.get_pipeline_status()
        phase_0 = [p for p in status["phases"] if p["phase"] == 0][0]
        assert phase_0["passed"] is True

    def test_heartbeat_does_not_call_full_gate_validation(self, validator, monkeypatch):
        """Heartbeat must stay lightweight and avoid validate_phase side effects."""

        def fail_validate_phase(phase):
            raise AssertionError(f"validate_phase({phase}) should not run in heartbeat")

        monkeypatch.setattr(validator, "validate_phase", fail_validate_phase)
        status = validator.get_pipeline_status()
        assert status["phases_total"] == 14

    def test_heartbeat_does_not_write_gate_validation_log(self, validator, project_dir):
        """Heartbeat should not append hard-gate audit entries."""
        validator.get_pipeline_status()
        assert not (project_dir / ".audit" / "gate-validations.jsonl").exists()

    def test_heartbeat_omits_git_subprocesses(self, validator, project_dir, monkeypatch):
        """Heartbeat must not run Git even when Phase 11 artifacts are present."""
        import subprocess

        _add_prerequisites(project_dir, up_to_phase=11)
        (project_dir / ".git").mkdir()

        def fail_run(*args, **kwargs):
            raise AssertionError("git subprocess should not run in heartbeat")

        monkeypatch.setattr(subprocess, "run", fail_run)
        status = validator.get_pipeline_status()
        phase_11 = next(p for p in status["phases"] if p["phase"] == 11)
        assert phase_11["name"] == "Final Delivery"


class TestAgentActionableGateErrors:
    def test_phase10_pipeline_run_reports_wrong_name_candidates(self, validator, project_dir):
        _add_prerequisites(project_dir, up_to_phase=10)
        (project_dir / ".audit" / "pipeline-run.md").write_text("# Run\n")

        r = validator.validate_phase(10)
        check = next(c for c in r.checks if c.name == "pipeline-run.md")
        assert not check.passed
        assert check.expected_pattern == "pipeline-run-*.md"
        assert check.search_path == ".audit/pipeline-run-*.md"
        assert ".audit/pipeline-run.md" in check.actual_found
        assert "pipeline-run-YYYYMMDD-HHmm.md" in check.fix_hint

    def test_phase10_d7_d8_reports_expected_heading_pattern(self, validator, project_dir):
        _add_prerequisites(project_dir, up_to_phase=10)
        (project_dir / ".audit" / "pipeline-run-20260101-1200.md").write_text(
            "# Run\n## D7 Review Retrospective\n## D8 Retrospective\n"
        )

        r = validator.validate_phase(10)
        d7 = next(c for c in r.checks if c.name == "pipeline-run:D7")
        d8 = next(c for c in r.checks if c.name == "pipeline-run:D8")
        assert not d7.passed
        assert not d8.passed
        assert d7.expected_pattern.startswith("^##\\s+D7")
        assert d7.actual_found == ["## D7 Review Retrospective"]
        assert "## D7 retrospective:" in d7.fix_hint
        assert d8.actual_found == ["## D8 Retrospective"]

    def test_gate_result_json_compact_returns_failing_metadata(self):
        result = GateResult(
            phase=10,
            phase_name="Retrospective",
            checks=[
                GateCheck(name="ok", description="ok", passed=True),
                GateCheck(
                    name="pipeline-run:D7",
                    description="D7 section",
                    passed=False,
                    expected_pattern="^##\\s+D7",
                    search_path=".audit/pipeline-run-*.md",
                    actual_found=["## D7 Review"],
                    fix_hint="Rename heading",
                ),
            ],
            passed=False,
            timestamp="2026-01-01T00:00:00",
        )
        data = json.loads(result.to_json(compact=True))
        assert data["schema"] == "mdpaper.gate_result.v1"
        assert [c["name"] for c in data["checks"]] == ["pipeline-run:D7"]
        assert data["checks"][0]["expected_pattern"] == "^##\\s+D7"


class TestGateLogging:
    def test_gate_validation_logged(self, validator, project_dir):
        validator.validate_phase(0)
        log_file = project_dir / ".audit" / "gate-validations.jsonl"
        assert log_file.is_file()
        entry = json.loads(log_file.read_text().strip().split("\n")[0])
        assert entry["phase"] == 0
        assert "passed" in entry


class TestProjectStructure:
    """Tests for validate_project_structure — independent of pipeline."""

    def test_empty_project_reports_missing(self, project_dir):
        """Bare project dir should fail on project.json and concept."""
        # Remove the dirs that the fixture auto-creates
        import shutil

        from med_paper_assistant.infrastructure.persistence.pipeline_gate_validator import (
            PipelineGateValidator,
        )

        for d in project_dir.iterdir():
            if d.is_dir():
                shutil.rmtree(d)
        v = PipelineGateValidator(project_dir)
        r = v.validate_project_structure()
        assert r.phase == -1
        assert r.phase_name == "Project Structure"
        # project.json missing → CRITICAL → overall fail
        pj_check = next(c for c in r.checks if c.name == "project.json")
        assert not pj_check.passed

    def test_complete_project_passes(self, validator, project_dir):
        """Project with all required dirs + project.json passes."""
        (project_dir / "project.json").write_text('{"slug": "test"}')
        (project_dir / "concept.md").write_text("# Concept")
        (project_dir / ".memory" / "activeContext.md").write_text("# Active")
        (project_dir / ".memory" / "progress.md").write_text("# Progress")
        r = validator.validate_project_structure()
        assert r.passed

    def test_concept_in_drafts_accepted(self, validator, project_dir):
        """concept.md in drafts/ should also pass."""
        (project_dir / "project.json").write_text('{"slug": "test"}')
        (project_dir / "drafts" / "concept.md").write_text("# Concept")
        r = validator.validate_project_structure()
        concept_check = next(c for c in r.checks if c.name == "concept.md")
        assert concept_check.passed


class TestPrerequisiteChecks:
    """Tests for _check_prerequisites prepended in validate_phase for phase > 1."""

    def test_phase_1_no_prereqs(self, validator, project_dir):
        """Phase 1 should NOT have prerequisite checks."""
        r = validator.validate_phase(1)
        prereq_checks = [c for c in r.checks if c.name.startswith("prereq:")]
        assert len(prereq_checks) == 0

    def test_phase_2_has_project_json_prereq(self, validator, project_dir):
        """Phase 2 should prepend prereq:project.json check."""
        r = validator.validate_phase(2)
        prereq_checks = [c for c in r.checks if c.name.startswith("prereq:")]
        assert len(prereq_checks) == 1
        assert prereq_checks[0].name == "prereq:project.json"
        assert prereq_checks[0].severity == "CRITICAL"

    def test_phase_5_has_concept_prereq(self, validator, project_dir):
        """Phase 5 should check concept.md prerequisite."""
        r = validator.validate_phase(5)
        prereq_names = [c.name for c in r.checks if c.name.startswith("prereq:")]
        assert "prereq:project.json" in prereq_names
        assert "prereq:references" in prereq_names
        assert "prereq:concept.md" in prereq_names

    def test_phase_7_has_manuscript_prereq(self, validator, project_dir):
        """Phase 7 should check manuscript.md prerequisite."""
        r = validator.validate_phase(7)
        prereq_names = [c.name for c in r.checks if c.name.startswith("prereq:")]
        assert "prereq:manuscript.md" in prereq_names

    def test_prereqs_are_critical_blocking(self, validator, project_dir):
        """Prerequisite failures should be CRITICAL — blocking phase progression."""
        r = validator.validate_phase(5)
        prereq_fails = [c for c in r.checks if c.name.startswith("prereq:") and not c.passed]
        assert len(prereq_fails) > 0
        for c in prereq_fails:
            assert c.severity == "CRITICAL"


class TestReviewPrerequisite:
    """Tests for the Phase 7 review completion prerequisite enforced on phases 8+."""

    def test_phase_8_requires_review_completed(self, validator, project_dir):
        """Phase 8+ gate should check prereq:review_completed."""
        _add_prerequisites(project_dir, up_to_phase=7)
        r = validator.validate_phase(8)
        prereq_names = [c.name for c in r.checks]
        assert "prereq:review_completed" in prereq_names

    def test_phase_8_fails_without_review_loop(self, validator, project_dir):
        """Phase 8 should fail when audit-loop-review.json doesn't exist."""
        _add_prerequisites(project_dir, up_to_phase=7)
        r = validator.validate_phase(8)
        review_check = next(c for c in r.checks if c.name == "prereq:review_completed")
        assert not review_check.passed
        assert "start_review_round" in review_check.details

    def test_phase_8_fails_with_insufficient_rounds(self, validator, project_dir):
        """Phase 8 should fail when fewer than min_rounds completed."""
        _add_prerequisites(project_dir, up_to_phase=7)
        _complete_review_loop(project_dir, rounds=1)
        r = validator.validate_phase(8)
        review_check = next(c for c in r.checks if c.name == "prereq:review_completed")
        assert not review_check.passed
        assert "1/2" in review_check.details

    def test_phase_8_passes_with_completed_review(self, validator, project_dir):
        """Phase 8 should pass when review loop is properly completed."""
        _add_prerequisites(project_dir, up_to_phase=8)
        r = validator.validate_phase(8)
        review_check = next(c for c in r.checks if c.name == "prereq:review_completed")
        assert review_check.passed

    def test_phase_8_fails_with_unresolved_citation(self, validator, project_dir):
        """A References heading alone is not enough for Phase 8 reference sync."""
        _add_prerequisites(project_dir, up_to_phase=8)
        (project_dir / "drafts" / "manuscript.md").write_text(
            "# Manuscript\n\nClaim with [[missing2026_99999999]].\n\n## References\n\n"
        )

        r = validator.validate_phase(8)

        assert not r.passed
        assert any(c.name == "reference-sync:wikilinks" for c in r.critical_failures)

    def test_phase_8_resolves_legacy_flat_md_reference_files(self, validator, project_dir):
        """Legacy flat references/key.md files should resolve manuscript wikilinks."""
        _add_prerequisites(project_dir, up_to_phase=8)
        key = "smith2026_12345678"
        (project_dir / "references" / f"{key}.md").write_text("# Smith 2026\n")
        (project_dir / "drafts" / "manuscript.md").write_text(
            f"# Manuscript\n\nClaim with [[{key}]].\n\n## References\n\n"
        )

        r = validator.validate_phase(8)

        c5 = next(c for c in r.checks if c.name == "reference-sync:wikilinks")
        assert c5.passed

    def test_phase_9_also_requires_review(self, validator, project_dir):
        """Phase 9 (Export) should also require review completion."""
        _add_prerequisites(project_dir, up_to_phase=7)
        r = validator.validate_phase(9)
        prereq_names = [c.name for c in r.checks]
        assert "prereq:review_completed" in prereq_names

    def test_phase_9_fails_with_corrupt_export_files(self, validator, project_dir):
        """Phase 9 must prove export integrity, not just file extensions."""
        _add_prerequisites(project_dir, up_to_phase=9)
        exports = project_dir / "exports"
        (exports / "paper.docx").write_bytes(b"PK")
        (exports / "paper.pdf").write_bytes(b"%PDF")

        r = validator.validate_phase(9)

        assert not r.passed
        names = {c.name for c in r.critical_failures}
        assert "export:docx:integrity" in names
        assert "export:pdf:integrity" in names

    def test_phase_65_does_not_require_review(self, validator, project_dir):
        """Phase 65 (Evolution Gate) sits before Phase 7 — should NOT check review."""
        _add_prerequisites(project_dir, up_to_phase=6)
        r = validator.validate_phase(65)
        prereq_names = [c.name for c in r.checks]
        assert "prereq:review_completed" not in prereq_names

    def test_review_fails_with_invalid_verdict(self, validator, project_dir):
        """Review should fail when loop didn't terminate properly."""
        _add_prerequisites(project_dir, up_to_phase=7)
        loop_state = project_dir / ".audit" / "audit-loop-review.json"
        loop_state.write_text(
            json.dumps(
                {
                    "config": {"min_rounds": 2, "max_rounds": 3},
                    "rounds": [
                        {"round": 1, "verdict": "needs_revision"},
                        {"round": 2, "verdict": "in_progress"},
                    ],
                }
            )
        )
        r = validator.validate_phase(8)
        review_check = next(c for c in r.checks if c.name == "prereq:review_completed")
        assert not review_check.passed
        assert "state integrity" in review_check.details.lower()


class TestCheckReviewCompleted:
    """Direct tests for _check_review_completed helper."""

    def test_missing_audit_loop_file(self, validator, project_dir):
        """Should fail with guidance when file doesn't exist."""
        passed, details = validator._check_review_completed()
        assert not passed
        assert "start_review_round" in details

    def test_corrupt_json(self, validator, project_dir):
        """Should fail gracefully on corrupt JSON."""
        (project_dir / ".audit" / "audit-loop-review.json").write_text("{not valid")
        passed, details = validator._check_review_completed()
        assert not passed
        assert "corrupt" in details

    def test_quality_met_verdict(self, validator, project_dir):
        """Should pass with quality_met verdict."""
        _complete_review_loop(project_dir, rounds=2)
        passed, details = validator._check_review_completed()
        assert passed
        assert "quality_met" in details

    def test_quality_met_does_not_require_crypto_backend(self, validator, project_dir, monkeypatch):
        _complete_review_loop(project_dir, rounds=2)

        def missing_backend():
            raise ModuleNotFoundError("cryptography intentionally unavailable")

        monkeypatch.setattr(approval_signatures, "_load_ed25519_backend", missing_backend)

        passed, details = validator._check_review_completed()
        assert passed
        assert "quality_met" in details

    def test_max_rounds_verdict_requires_signed_state_bound_human_override(
        self, validator, project_dir, monkeypatch
    ):
        """A round limit is an escalation, not autonomous evidence of quality."""
        (project_dir / "project.json").write_text('{"slug": "test"}')
        _complete_review_loop(project_dir, rounds=3, terminal="max_rounds")
        passed, details = validator._check_review_completed()
        assert not passed
        assert "human approval receipt is missing" in details

        state_path = project_dir / ".audit" / "audit-loop-review.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        private_key = _configure_approval_signer(monkeypatch)
        receipt = _sign_approval_receipt(
            {
                "schema": REVIEW_APPROVAL_SCHEMA,
                "approved_to_proceed": True,
                "approved_at": state["rounds"][-1]["completed_at"],
                "approved_by": "principal-investigator:pi-001",
                "accepted_verdict": "max_rounds",
                "final_weighted_score": state["rounds"][-1]["weighted_avg"],
                "quality_threshold": state["config"]["quality_threshold"],
                "audit_loop_sha256": hashlib.sha256(state_path.read_bytes()).hexdigest(),
                "final_artifact_sha256": state["rounds"][-1]["artifact_hash_end"],
                "rationale": "The deadline requires a clearly disclosed interim report.",
                "accepted_risks": "The manuscript remains below the configured target.",
                "mode": "human-collaboration",
                "decision_source": "external-user-confirmation",
                "confirmation_id": "review-confirmation-0001",
                "project_slug": "test",
            },
            private_key,
        )
        unsigned_v2 = {key: value for key, value in receipt.items() if key != "signature"}
        unsigned_v2["schema"] = "mdpaper.review_completion_override.v2"
        (project_dir / ".audit" / "review-completion-override.yaml").write_text(
            yaml.safe_dump(unsigned_v2, sort_keys=False),
            encoding="utf-8",
        )
        passed, details = validator._check_review_completed()
        assert not passed
        assert "schema is unsupported" in details

        (project_dir / ".audit" / "review-completion-override.yaml").write_text(
            yaml.safe_dump(receipt, sort_keys=False),
            encoding="utf-8",
        )
        passed, details = validator._check_review_completed()
        assert passed
        assert "max_rounds" in details

        override_path = project_dir / ".audit" / "review-completion-override.yaml"
        receipt = yaml.safe_load(override_path.read_text(encoding="utf-8"))
        receipt["approved_by"] = "human"
        _sign_approval_receipt(receipt, private_key)
        override_path.write_text(yaml.safe_dump(receipt), encoding="utf-8")
        passed, details = validator._check_review_completed()
        assert not passed
        assert "specific external reviewer identity" in details

        state["rounds"][-1]["weighted_avg"] = 6.1
        state_path.write_text(json.dumps(state), encoding="utf-8")
        passed, details = validator._check_review_completed()
        assert not passed
        assert "stale" in details or "state integrity" in details

    def test_signed_review_override_becomes_stale_after_manuscript_change(
        self, validator, project_dir, monkeypatch
    ):
        (project_dir / "project.json").write_text('{"slug": "test"}')
        _complete_review_loop(project_dir, rounds=3, terminal="max_rounds")
        state_path = project_dir / ".audit" / "audit-loop-review.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        receipt = _sign_approval_receipt(
            {
                "schema": REVIEW_APPROVAL_SCHEMA,
                "approved_to_proceed": True,
                "approved_at": state["rounds"][-1]["completed_at"],
                "approved_by": "principal-investigator:pi-001",
                "accepted_verdict": "max_rounds",
                "final_weighted_score": state["rounds"][-1]["weighted_avg"],
                "quality_threshold": state["config"]["quality_threshold"],
                "audit_loop_sha256": hashlib.sha256(state_path.read_bytes()).hexdigest(),
                "final_artifact_sha256": state["rounds"][-1]["artifact_hash_end"],
                "rationale": "The deadline requires a clearly disclosed interim report.",
                "accepted_risks": "The manuscript remains below the configured target.",
                "mode": "human-collaboration",
                "decision_source": "external-user-confirmation",
                "confirmation_id": "review-confirmation-stale-0001",
                "project_slug": "test",
            },
            _configure_approval_signer(monkeypatch),
        )
        (project_dir / ".audit" / "review-completion-override.yaml").write_text(
            yaml.safe_dump(receipt, sort_keys=False),
            encoding="utf-8",
        )
        assert validator._check_review_completed()[0]

        manuscript = project_dir / "drafts" / "manuscript.md"
        manuscript.write_text(
            manuscript.read_text(encoding="utf-8") + "\nPost-approval mutation.\n",
            encoding="utf-8",
        )

        passed, details = validator._check_review_completed()
        assert not passed
        assert "final-artifact-current" in details

    def test_rewrite_needed_verdict_does_not_complete_review(self, validator, project_dir):
        """rewrite_needed must regress to Phase 5, not unlock Phase 8."""
        (project_dir / ".audit" / "audit-loop-review.json").write_text(
            json.dumps(
                {
                    "config": {"min_rounds": 1, "max_rounds": 3},
                    "rounds": [{"round": 1, "verdict": "rewrite_needed"}],
                }
            )
        )
        passed, details = validator._check_review_completed()
        assert not passed
        assert "state integrity" in details.lower()
