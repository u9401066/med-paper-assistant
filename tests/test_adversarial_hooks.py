"""Adversarial / metamorphic verification harness.

Proves the quality VERIFIERS (writing hooks) actually CATCH bad input — not just
pass good input. For each covered hook we declare exactly one KNOWN-GOOD fixture
that must pass and one or more KNOWN-BAD fixtures (a known-direction mutation of
the good one) that must be caught.

Design doc: docs/design/adversarial-verification-harness.md

Why this exists:
- The agent is a generator; the hooks are the verifier. We can only harden the
  verifier, so we must continuously PROVE it rejects bad input.
- Existing tests mostly assert "good input passes". This asserts the inverse —
  "bad input is caught" — which is the actual job of a verifier.

`caught(result)` is uniform: a hook catches a problem iff `result.passed is False`.
Every hook already sets `passed` correctly (a CRITICAL issue or a threshold breach
flips it), so the harness needs no per-hook special-casing.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from med_paper_assistant.infrastructure.persistence.writing_hooks import (
    HookResult,
    WritingHooksEngine,
)

# ── Hooks this harness commits to covering (coverage ratchet) ──────────
ADVERSARIAL_TARGETS = {"A3", "A5", "A6", "B8", "C3", "C4", "P7"}


def _engine(project_dir: Path) -> WritingHooksEngine:
    (project_dir / ".audit").mkdir(parents=True, exist_ok=True)
    (project_dir / "drafts").mkdir(parents=True, exist_ok=True)
    return WritingHooksEngine(project_dir)


def caught(result: HookResult) -> bool:
    """A verifier 'catches' a problem when it does not pass."""
    return not result.passed


# ── Known-good / known-bad content fixtures ────────────────────────────

# A3: Anti-AI phrasing
A3_GOOD = "We measured the primary outcome at 24 hours and observed a reduction in pain scores."
A3_BAD = (
    "It is important to note that this intervention plays a crucial role in our "
    "groundbreaking study of postoperative recovery."
)

# A5: Language consistency (prefer American)
A5_GOOD = "We analyzed the color of randomized tumor samples in the center."
A5_BAD = "We analysed the colour of randomised tumour samples in the centre."

# A6: Internal overlap / copy-paste (two paragraphs)
A6_GOOD = (
    "The cohort comprised adults undergoing elective surgery during the study window here.\n\n"
    "Outcomes were ascertained by blinded assessors using a standardized instrument throughout."
)
A6_BAD = (
    "The cohort comprised adults undergoing elective surgery during the study window here.\n\n"
    "The cohort comprised adults undergoing elective surgery during the study window here."
)

# B8: Stats test alignment (Methods vs Results)
B8_METHODS = "Group differences were assessed with a two-sample t-test."
B8_RESULTS_GOOD = "The groups differed in the primary outcome (t-test, p < 0.05)."
B8_RESULTS_BAD = "Survival differed across the three arms by ANOVA (p < 0.05)."

# C3: N-value consistency (Methods is source of truth)
C3_GOOD = (
    "## Methods\n\nWe enrolled 100 patients (N=100) in the trial.\n\n"
    "## Results\n\nAmong the 100 patients (N=100), the primary outcome occurred in 30."
)
C3_BAD = (
    "## Methods\n\nWe enrolled 100 patients (N=100) in the trial.\n\n"
    "## Results\n\nAmong the 250 patients (N=250), the primary outcome occurred in 30."
)

# C4: Abbreviation first-use (PONV is not a common/excluded abbreviation)
C4_GOOD = (
    "Postoperative nausea and vomiting (PONV) was the secondary outcome. "
    "PONV occurred in ten patients."
)
C4_BAD = "PONV was the secondary outcome. PONV occurred in ten patients."

# P7: Reference + DOI integrity
P7_GOOD_DOI = "10.1001/jama.2020.1585"
P7_BAD_DOI = "not-a-real-doi"


def _p7_build(doi: str) -> Callable[[Path], HookResult]:
    def _build(project_dir: Path) -> HookResult:
        ref_dir = project_dir / "references" / "smith2024_12345678"
        ref_dir.mkdir(parents=True, exist_ok=True)
        (ref_dir / "metadata.json").write_text(
            json.dumps({"_data_source": "pubmed_api", "title": "Test", "doi": doi}),
            encoding="utf-8",
        )
        return _engine(project_dir).check_reference_integrity()

    return _build


def _content_build(method: str, *args: str) -> Callable[[Path], HookResult]:
    def _build(project_dir: Path) -> HookResult:
        return getattr(_engine(project_dir), method)(*args)

    return _build


@dataclass(frozen=True)
class Scenario:
    hook_id: str
    kind: str  # "good" | "bad"
    label: str
    build: Callable[[Path], HookResult]


SCENARIOS: list[Scenario] = [
    # A3 — anti-AI phrasing
    Scenario("A3", "good", "clean prose", _content_build("check_anti_ai_patterns", A3_GOOD)),
    Scenario("A3", "bad", "AI filler phrases", _content_build("check_anti_ai_patterns", A3_BAD)),
    # A5 — language consistency
    Scenario(
        "A5", "good", "american spelling",
        _content_build("check_language_consistency", A5_GOOD, "american"),
    ),
    Scenario(
        "A5", "bad", "british spelling",
        _content_build("check_language_consistency", A5_BAD, "american"),
    ),
    # A6 — overlap
    Scenario("A6", "good", "distinct paragraphs", _content_build("check_overlap", A6_GOOD)),
    Scenario("A6", "bad", "duplicated paragraph", _content_build("check_overlap", A6_BAD)),
    # B8 — stats alignment
    Scenario(
        "B8", "good", "declared test",
        _content_build("check_data_claim_alignment", B8_METHODS, B8_RESULTS_GOOD),
    ),
    Scenario(
        "B8", "bad", "undeclared ANOVA",
        _content_build("check_data_claim_alignment", B8_METHODS, B8_RESULTS_BAD),
    ),
    # C3 — n-value consistency
    Scenario("C3", "good", "consistent N", _content_build("check_n_value_consistency", C3_GOOD)),
    Scenario("C3", "bad", "mismatched N", _content_build("check_n_value_consistency", C3_BAD)),
    # C4 — abbreviation first use
    Scenario("C4", "good", "defined abbr", _content_build("check_abbreviation_first_use", C4_GOOD)),
    Scenario("C4", "bad", "undefined abbr", _content_build("check_abbreviation_first_use", C4_BAD)),
    # P7 — reference + DOI integrity
    Scenario("P7", "good", "valid DOI", _p7_build(P7_GOOD_DOI)),
    Scenario("P7", "bad", "malformed DOI", _p7_build(P7_BAD_DOI)),
]


_GOOD = [s for s in SCENARIOS if s.kind == "good"]
_BAD = [s for s in SCENARIOS if s.kind == "bad"]


@pytest.mark.parametrize("scenario", _GOOD, ids=lambda s: f"{s.hook_id}-good-{s.label}")
def test_known_good_passes(scenario: Scenario, tmp_path: Path) -> None:
    """A known-good fixture must NOT be flagged (no false positive)."""
    result = scenario.build(tmp_path / "proj")
    assert result.hook_id == scenario.hook_id
    assert result.passed is True, (
        f"Hook {scenario.hook_id} false-positived on good input "
        f"({scenario.label}); issues={[i.message for i in result.issues]}"
    )


@pytest.mark.parametrize("scenario", _BAD, ids=lambda s: f"{s.hook_id}-bad-{s.label}")
def test_known_bad_is_caught(scenario: Scenario, tmp_path: Path) -> None:
    """A known-bad fixture MUST be caught — this is the verifier's whole job."""
    result = scenario.build(tmp_path / "proj")
    assert result.hook_id == scenario.hook_id
    assert caught(result), (
        f"Hook {scenario.hook_id} FAILED to catch bad input ({scenario.label}). "
        f"This means the verifier is asleep for this failure mode."
    )


def test_metamorphic_verdict_flips(tmp_path: Path) -> None:
    """For every covered hook the verdict must flip good(pass) -> bad(caught)."""
    by_hook: dict[str, dict[str, list[Scenario]]] = {}
    for s in SCENARIOS:
        by_hook.setdefault(s.hook_id, {"good": [], "bad": []})[s.kind].append(s)

    for hook_id, kinds in by_hook.items():
        for good in kinds["good"]:
            assert good.build(tmp_path / f"{hook_id}-g").passed is True
        assert any(
            caught(bad.build(tmp_path / f"{hook_id}-b-{i}"))
            for i, bad in enumerate(kinds["bad"])
        ), f"Hook {hook_id} never flips to caught under any known-bad mutation"


def test_coverage_ratchet() -> None:
    """Every committed target must have BOTH a good and a bad scenario.

    This is the verifier's own ratchet: adversarial coverage can only be added,
    never silently lost. Adding a hook to ADVERSARIAL_TARGETS without fixtures
    fails here on purpose.
    """
    good_hooks = {s.hook_id for s in _GOOD}
    bad_hooks = {s.hook_id for s in _BAD}

    missing_good = ADVERSARIAL_TARGETS - good_hooks
    missing_bad = ADVERSARIAL_TARGETS - bad_hooks
    assert not missing_good, f"targets missing a known-good fixture: {sorted(missing_good)}"
    assert not missing_bad, f"targets missing a known-bad fixture: {sorted(missing_bad)}"

    # And no scenario references a hook outside the declared target set.
    stray = (good_hooks | bad_hooks) - ADVERSARIAL_TARGETS
    assert not stray, f"scenarios for undeclared hooks: {sorted(stray)}"
