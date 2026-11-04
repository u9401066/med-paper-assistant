"""Hook runner behind the run_writing_hooks tool."""

import re

from med_paper_assistant.infrastructure.persistence.hook_effectiveness_tracker import (
    HookEffectivenessTracker,
)
from med_paper_assistant.infrastructure.persistence.writing_hooks import (
    HookResult,
    WritingHooksEngine,
)


def extract_section(content: str, title: str) -> str:
    """Return the body of the ``## <title>`` section, or an empty string."""
    pattern = rf"(?:^|\n)##?\s+{title}\b.*?\n(.*?)(?=\n##?\s|\Z)"
    m = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


class WritingHookRun:
    """Runs the requested writing hooks, recording each outcome and tallying issues."""

    def __init__(
        self,
        engine: WritingHooksEngine,
        tracker: HookEffectivenessTracker,
        requested: set[str],
        content: str,
    ) -> None:
        self.engine = engine
        self.tracker = tracker
        self.requested = requested
        self.content = content
        self.results: dict[str, dict] = {}
        self.critical = 0
        self.warning = 0

    def record(self, result_key: str, hook_id: str, result: HookResult) -> None:
        """Store a hook result, log the tracker event and add to the issue totals."""
        self.results[result_key] = result.to_dict()
        self.tracker.record_event(hook_id, "pass" if result.passed else "trigger")
        self.critical += result.critical_count
        self.warning += result.warning_count

    def _record_precommit(self, hook_id: str, result: HookResult) -> None:
        """Record a delegated pre-commit result under its own hook id."""
        result.hook_id = hook_id
        for issue in result.issues:
            issue.hook_id = hook_id
        self.record(hook_id, hook_id, result)

    def _section(self, title: str) -> str:
        return extract_section(self.content, title)

    def post_write(self, prefer_language: str) -> None:
        """Post-write hooks A1-A6."""
        req, engine, content = self.requested, self.engine, self.content
        if "A1" in req:
            self.record("A1", "A1", engine.check_word_count_compliance(content))

        if "A2" in req:
            # Run per-section for Introduction and Discussion
            for sec_name in ("Introduction", "Discussion"):
                sec_text = self._section(sec_name)
                if sec_text:
                    r = engine.check_citation_density(sec_text, section_name=sec_name)
                    self.record(f"A2:{sec_name}", "A2", r)

        if "A3" in req:
            self.record("A3", "A3", engine.check_anti_ai_patterns(content))

        if "A3B" in req:
            self.record("A3B", "A3B", engine.check_ai_writing_signals(content))

        if "A3C" in req:
            self.record("A3C", "A3C", engine.check_voice_consistency(content))

        if "A4" in req:
            self.record("A4", "A4", engine.check_wikilink_format(content))

        if "A5" in req:
            r = engine.check_language_consistency(content, prefer=prefer_language)
            self.record("A5", "A5", r)

        if "A6" in req:
            self.record("A6", "A6", engine.check_overlap(content))

    def data_and_citations(self) -> None:
        """B8 data alignment, C9 supplementary, F artifacts and C10-C13 citation hooks."""
        req, engine, content = self.requested, self.engine, self.content
        if "B8" in req:
            self._data_claim_alignment()

        if "C9" in req:
            self.record("C9", "C9", engine.check_supplementary_crossref(content))

        if "F" in req:
            self.record("F", "F1", engine.validate_data_artifacts(content))

        if "C10" in req:
            self.record("C10", "C10", engine.check_reference_fulltext_status(content))

        if "C11" in req:
            self.record("C11", "C11", engine.check_citation_distribution(content))

        if "C12" in req:
            self.record("C12", "C12", engine.check_citation_relevance_audit(content))

        if "C13" in req:
            self.record("C13", "C13", engine.check_figure_table_quality(content))

    def _data_claim_alignment(self) -> None:
        """B8: statistical tests reported in Results must be described in Methods."""
        methods = self._section("Methods")
        results = self._section("Results")
        if methods and results:
            r = self.engine.check_data_claim_alignment(methods, results)
            self.record("B8", "B8", r)
        else:
            self.results["B8"] = {
                "hook_id": "B8",
                "passed": True,
                "issues": [],
                "stats": {"skipped": "Methods or Results section not found"},
            }

    def manuscript_level(self) -> None:
        """Post-manuscript hooks C3-C7d."""
        req, engine, content = self.requested, self.engine, self.content
        if "C3" in req:
            self.record("C3", "C3", engine.check_n_value_consistency(content))

        if "C4" in req:
            self.record("C4", "C4", engine.check_abbreviation_first_use(content))

        if "C5" in req:
            self.record("C5", "C5", engine.check_wikilink_resolvable(content))

        if "C6" in req:
            self.record("C6", "C6", engine.check_total_word_count(content))

        if "C7A" in req:
            self.record("C7a", "C7a", engine.check_figure_table_counts(content))

        if "C7D" in req:
            self.record("C7d", "C7d", engine.check_cross_references(content))

    def precommit(self) -> None:
        """Pre-commit hooks P1, P2, P4, P5 and P7."""
        req, engine, content = self.requested, self.engine, self.content
        if "P1" in req:
            self._record_precommit("P1", engine.check_wikilink_resolvable(content))

        if "P2" in req:
            r = engine.check_anti_ai_patterns(
                content,
                section="precommit",
                warn_threshold=1,
                critical_threshold=3,
            )
            self._record_precommit("P2", r)

        if "P4" in req:
            r = engine.check_word_count_compliance(content, critical_threshold_pct=50)
            self._record_precommit("P4", r)

        if "P5" in req:
            self.record("P5", "P5", engine.check_protected_content())

        if "P7" in req:
            self.record("P7", "P7", engine.check_reference_integrity(content))

    def git(self) -> None:
        """Git status hook G9."""
        if "G9" in self.requested:
            self.record("G9", "G9", self.engine.check_git_status())

    def section_quality(self) -> None:
        """Section writing quality hooks B9-B16."""
        req, engine, content = self.requested, self.engine, self.content
        if "B9" in req:
            for sec_name in ("Methods", "Results"):
                sec_text = self._section(sec_name)
                if sec_text:
                    r = engine.check_section_tense(sec_text, section=sec_name)
                    self.record(f"B9:{sec_name}", "B9", r)

        if "B10" in req:
            for sec_name in ("Introduction", "Methods", "Results", "Discussion"):
                sec_text = self._section(sec_name)
                if sec_text:
                    r = engine.check_paragraph_quality(sec_text, section=sec_name)
                    self.record(f"B10:{sec_name}", "B10", r)

        if "B11" in req:
            self.record("B11", "B11", engine.check_results_interpretation(content))

        if "B12" in req:
            self.record("B12", "B12", engine.check_intro_structure(content))

        if "B13" in req:
            self.record("B13", "B13", engine.check_discussion_structure(content))

        if "B14" in req:
            self.record("B14", "B14", engine.check_ethical_statements(content))

        if "B15" in req:
            self.record("B15", "B15", engine.check_hedging_density(content))

        if "B16" in req:
            self.record("B16", "B16", engine.check_effect_size_reporting(content))
