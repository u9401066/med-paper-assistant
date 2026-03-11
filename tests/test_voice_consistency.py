"""Tests for Hook A3c: Voice Consistency Detector.

Validates paragraph-level voice consistency analysis:
  - Uniform text passes (all paragraphs similar style)
  - Mixed voice detected (ESL + polished paragraphs → outliers)
  - Vocabulary sophistication gap detection
  - Too-few-paragraphs graceful skip
  - Integration with WritingHooksEngine batch runner
"""

from pathlib import Path

import pytest

from med_paper_assistant.infrastructure.persistence.writing_hooks import (
    WritingHooksEngine,
)


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    d = tmp_path / "test-project"
    d.mkdir()
    (d / ".audit").mkdir()
    (d / "drafts").mkdir()
    return d


@pytest.fixture()
def engine(project_dir: Path) -> WritingHooksEngine:
    return WritingHooksEngine(project_dir)


# ── Helpers ──────────────────────────────────────────────────────────────


def _uniform_paragraphs(n: int = 6) -> str:
    """Generate n paragraphs with very similar style (should pass A3c)."""
    base_sentences = [
        "The patient received standard treatment during the study period.",
        "Blood samples were collected at baseline and at follow-up visits.",
        "Statistical analysis was performed using standard software packages.",
        "The primary outcome was measured at four weeks after enrollment.",
        "Adverse events were recorded throughout the observation period.",
        "Written informed consent was obtained from all participants.",
    ]
    paragraphs = []
    for i in range(n):
        # Rotate sentences to create varied but stylistically consistent paragraphs
        rotated = (
            base_sentences[i % len(base_sentences) :] + base_sentences[: i % len(base_sentences)]
        )
        paragraphs.append(" ".join(rotated))
    return "\n\n".join(paragraphs)


def _mixed_voice_paragraphs() -> str:
    """Generate paragraphs with deliberate style breaks (should fail A3c).

    Paragraphs 1-3 and 5: simple ESL-like sentences (short words, simple structure).
    Paragraph 4: polished corporate-academic prose with em-dashes, semicolons,
    and sophisticated vocabulary — the kind of style break a human reviewer notices.
    """
    esl_para_1 = (
        "We did this study to find out if the drug works for the patients. "
        "The study was done at our hospital. We got approval from the ethics "
        "board before we start. All patient data was kept in a safe place. "
        "We use simple methods to get the results."
    )
    esl_para_2 = (
        "The patients were split into two groups by random. One group got the "
        "drug and other group got a fake pill. We check the blood test every "
        "week for three months. The nurse record all the side effect that happen."
    )
    esl_para_3 = (
        "We look at the data and find that the drug group was better. The blood "
        "level go down in most patient. Not many bad thing happen in the study. "
        "We are happy with the result we got from this study."
    )
    polished_para = (
        "The multifaceted pharmacokinetic profile of the investigational compound "
        "— characterized by its unprecedented bioavailability and remarkably "
        "favorable tolerability; a constellation of attributes that distinguishes "
        "it from contemporaneous therapeutic interventions — underscores the "
        "transformative potential of this sophisticated pharmacological paradigm "
        "within the broader armamentarium of evidence-based medical therapeutics."
    )
    esl_para_5 = (
        "In the end we think the drug is good for the patient. More study is "
        "needed to make sure about the long term effect. We hope that other "
        "hospital can also try this drug for their patient. This study have "
        "some limit that we need to say about."
    )
    return "\n\n".join([esl_para_1, esl_para_2, esl_para_3, polished_para, esl_para_5])


# ── Tests ────────────────────────────────────────────────────────────────


class TestHookA3cBasic:
    """Basic functionality of check_voice_consistency."""

    def test_uniform_text_passes(self, engine: WritingHooksEngine):
        text = _uniform_paragraphs(6)
        r = engine.check_voice_consistency(text)
        assert r.hook_id == "A3c"
        assert r.passed is True
        assert r.stats["paragraph_count"] == 6
        assert r.stats["outlier_count"] == 0

    def test_too_few_paragraphs_skips(self, engine: WritingHooksEngine):
        text = (
            "First paragraph with enough words to pass the minimum threshold for counting.\n\n"
            "Second paragraph also with enough words to pass the minimum threshold for it.\n\n"
            "Third paragraph that has enough words but we still only have three paragraphs total."
        )
        r = engine.check_voice_consistency(text)
        assert r.passed is True
        assert r.stats.get("skipped") is True
        assert r.stats.get("reason") == "too_few_paragraphs"

    def test_empty_content(self, engine: WritingHooksEngine):
        r = engine.check_voice_consistency("")
        assert r.passed is True
        assert r.stats.get("skipped") is True

    def test_hook_id_correct(self, engine: WritingHooksEngine):
        text = _uniform_paragraphs(5)
        r = engine.check_voice_consistency(text)
        assert r.hook_id == "A3c"

    def test_stats_contain_required_fields(self, engine: WritingHooksEngine):
        text = _uniform_paragraphs(5)
        r = engine.check_voice_consistency(text)
        assert "paragraph_count" in r.stats
        assert "outlier_count" in r.stats
        assert "sophistication_gap" in r.stats
        assert "baselines" in r.stats
        assert "paragraph_scores" in r.stats

    def test_baselines_have_metric_keys(self, engine: WritingHooksEngine):
        text = _uniform_paragraphs(5)
        r = engine.check_voice_consistency(text)
        baselines = r.stats["baselines"]
        for key in ["avg_sent_len", "avg_word_len", "ttr", "punct_complexity"]:
            assert key in baselines
            assert "mean" in baselines[key]
            assert "std" in baselines[key]

    def test_paragraph_scores_match_count(self, engine: WritingHooksEngine):
        text = _uniform_paragraphs(5)
        r = engine.check_voice_consistency(text)
        assert len(r.stats["paragraph_scores"]) == r.stats["paragraph_count"]


class TestHookA3cVoiceBreak:
    """Detection of voice consistency breaks."""

    def test_mixed_voice_flags_outliers(self, engine: WritingHooksEngine):
        text = _mixed_voice_paragraphs()
        r = engine.check_voice_consistency(text)
        assert r.passed is False
        assert r.stats["outlier_count"] >= 1
        # The polished paragraph (paragraph 4) should be flagged
        outlier_indices = [op["paragraph"] for op in r.stats["outlier_paragraphs"]]
        assert 4 in outlier_indices

    def test_mixed_voice_issues_have_warning_severity(self, engine: WritingHooksEngine):
        text = _mixed_voice_paragraphs()
        r = engine.check_voice_consistency(text)
        assert len(r.issues) >= 1
        for issue in r.issues:
            assert issue.severity == "WARNING"
            assert issue.hook_id == "A3c"

    def test_voice_break_message_contains_paragraph_number(self, engine: WritingHooksEngine):
        text = _mixed_voice_paragraphs()
        r = engine.check_voice_consistency(text)
        voice_break_issues = [i for i in r.issues if "Voice break" in i.message]
        assert len(voice_break_issues) >= 1
        # Should mention the paragraph number
        assert any("paragraph 4" in i.message for i in voice_break_issues)


class TestHookA3cSophisticationGap:
    """Detection of vocabulary sophistication gaps."""

    def test_sophistication_gap_detected(self, engine: WritingHooksEngine):
        text = _mixed_voice_paragraphs()
        r = engine.check_voice_consistency(text)
        # The polished paragraph has much longer words than ESL paragraphs
        gap = r.stats["sophistication_gap"]
        assert gap > 1.0  # Should be substantial

    def test_sophistication_gap_issue_message(self, engine: WritingHooksEngine):
        text = _mixed_voice_paragraphs()
        r = engine.check_voice_consistency(text)
        gap_issues = [i for i in r.issues if "sophistication gap" in i.message]
        if r.stats["sophistication_gap"] > 1.2:
            assert len(gap_issues) >= 1
            assert "ESL-to-polished-prose" in gap_issues[0].message

    def test_uniform_text_no_gap(self, engine: WritingHooksEngine):
        text = _uniform_paragraphs(6)
        r = engine.check_voice_consistency(text)
        assert r.stats["sophistication_gap"] < 1.0


class TestHookA3cCustomThreshold:
    """Custom outlier_z threshold parameter."""

    def test_stricter_threshold_flags_more(self, engine: WritingHooksEngine):
        text = _mixed_voice_paragraphs()
        strict = engine.check_voice_consistency(text, outlier_z=1.0)
        lenient = engine.check_voice_consistency(text, outlier_z=3.0)
        assert strict.stats["outlier_count"] >= lenient.stats["outlier_count"]

    def test_very_lenient_threshold_passes(self, engine: WritingHooksEngine):
        text = _mixed_voice_paragraphs()
        r = engine.check_voice_consistency(text, outlier_z=10.0)
        # Even mixed voice should pass with z=10.0 (no outliers)
        assert r.stats["outlier_count"] == 0


class TestHookA3cMarkdownHandling:
    """Proper handling of markdown elements."""

    def test_markdown_headings_stripped(self, engine: WritingHooksEngine):
        paragraphs = []
        for i in range(5):
            heading = f"## Section {i + 1}\n\n"
            body = (
                "The study was conducted at our institution during the past year. "
                "Patients were enrolled after meeting all inclusion criteria. "
                "Data was collected and analyzed using standard methods."
            )
            paragraphs.append(heading + body)
        text = "\n\n".join(paragraphs)
        r = engine.check_voice_consistency(text)
        # Headings should not count as separate paragraphs
        assert r.stats.get("paragraph_count", 0) <= 5

    def test_wikilinks_stripped(self, engine: WritingHooksEngine):
        paragraphs = []
        for _ in range(5):
            body = (
                "Previous work [[smith2024_12345678]] demonstrated that the drug "
                "reduces symptoms [[jones2023_87654321]]. These findings support "
                "our hypothesis about treatment efficacy in this population."
            )
            paragraphs.append(body)
        text = "\n\n".join(paragraphs)
        r = engine.check_voice_consistency(text)
        assert r.hook_id == "A3c"
        # Should process without errors
        assert "paragraph_count" in r.stats


class TestHookA3cBatchIntegration:
    """Integration with WritingHooksEngine batch runners."""

    def test_a3c_in_post_write_batch(self, engine: WritingHooksEngine):
        text = _uniform_paragraphs(5)
        results = engine.run_post_write_hooks(text, section="introduction")
        assert "A3c" in results
        assert results["A3c"].hook_id == "A3c"
