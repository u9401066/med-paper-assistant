"""Writing Hooks — Article-type-aware hook applicability matrix.

Single source of truth declaring which writing hooks apply to which paper
types. The always-on batch runners (``run_post_*_hooks``) consult this matrix
so that hooks designed for IMRaD / empirical manuscripts do **not** misfire on
letters, narrative reviews, or case reports that have no statistical
Methods/Results structure.

Two tiers
---------
- **COMMON** — applies to every paper type (anti-AI, language consistency,
  word count, citation integrity, wikilinks, paragraph quality, ...). Any hook
  not listed in :data:`_TYPE_SPECIFIC_APPLICABILITY` is treated as common.
- **TYPE-SPECIFIC** — applies only to a subset of paper types. Currently the
  statistical Methods↔Results hooks (B8/B11/B16) are limited to empirical
  study types.

Backward compatibility
-----------------------
The default paper type is ``"original-research"`` (see
``JournalConfigMixin._get_paper_type``), which is a member of every type set.
Unconfigured projects therefore keep running the full hook set exactly as
before; only ``letter`` / ``review-article`` / ``case-report`` / ``other``
projects get the non-applicable statistical hooks recorded as *skipped*.

Auditability
------------
A gated-off hook is **not** silently dropped: the batch runner records an
audit-friendly :class:`HookResult` (``passed=True``, ``stats.applicable=False``)
with the reason. This preserves the hook key for downstream consumers and keeps
a per-paper-type trail consistent with CONSTITUTION §22 (auditable).
"""

from __future__ import annotations

from med_paper_assistant.shared.constants import PAPER_TYPES

from ._models import HookResult

# All known paper types — canonical taxonomy lives in ``shared.constants``.
ALL_PAPER_TYPES: frozenset[str] = frozenset(PAPER_TYPES.keys())

# Empirical study types that contain a formal statistical Methods + Results
# section. These are the only types for which statistical-alignment hooks make
# sense.
EMPIRICAL_TYPES: frozenset[str] = frozenset(
    {"original-research", "systematic-review", "meta-analysis"}
)

# Fallback paper type for unknown/empty inputs (keeps legacy callers unchanged).
DEFAULT_PAPER_TYPE = "original-research"

# Hooks whose logic assumes a statistical Methods↔Results structure. They are
# recorded as not-applicable (skipped) for non-empirical paper types.
#
# Anything not listed here is COMMON (applies to every paper type).
_TYPE_SPECIFIC_APPLICABILITY: dict[str, frozenset[str]] = {
    "B8": EMPIRICAL_TYPES,  # Data-claim statistical alignment (Methods↔Results)
    "B11": EMPIRICAL_TYPES,  # Results-section objectivity guard
    "B16": EMPIRICAL_TYPES,  # Effect-size reporting for statistical results
}


def applicable_types(hook_id: str) -> frozenset[str]:
    """Return the set of paper types a hook applies to.

    Common (non-listed) hooks apply to every paper type.
    """
    return _TYPE_SPECIFIC_APPLICABILITY.get(hook_id, ALL_PAPER_TYPES)


def is_applicable(hook_id: str, paper_type: str | None) -> bool:
    """Whether ``hook_id`` should run for ``paper_type``.

    Unknown hooks default to applicable (common tier). Unknown/empty paper
    types fall back to ``original-research`` so legacy callers are unaffected.
    """
    pt = paper_type or DEFAULT_PAPER_TYPE
    return pt in applicable_types(hook_id)


def is_type_specific(hook_id: str) -> bool:
    """Whether the hook is gated to a subset of paper types."""
    return hook_id in _TYPE_SPECIFIC_APPLICABILITY


def type_specific_hook_ids() -> frozenset[str]:
    """Return the set of hook ids that are gated by paper type."""
    return frozenset(_TYPE_SPECIFIC_APPLICABILITY)


def skip_reason(hook_id: str, paper_type: str) -> str:
    """Human-readable explanation for why a hook was skipped."""
    allowed = ", ".join(sorted(applicable_types(hook_id)))
    return f"Hook {hook_id} is not applicable to paper_type='{paper_type}'. Applies to: {allowed}."


def not_applicable_result(hook_id: str, paper_type: str) -> HookResult:
    """Build a passing, audit-friendly :class:`HookResult` marking a skip.

    The hook key is preserved (so downstream consumers and tests still see it)
    but no issues are raised and ``stats`` records why it was skipped.
    """
    return HookResult(
        hook_id=hook_id,
        passed=True,
        issues=[],
        stats={
            "applicable": False,
            "skipped": True,
            "paper_type": paper_type,
            "reason": skip_reason(hook_id, paper_type),
        },
    )
