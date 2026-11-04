"""Note body templates for library notes."""

from __future__ import annotations

from datetime import datetime

from .content import _refs_to_links
from .normalize import _normalize_template_name


def _link_lines(note_links: list[str], placeholder: str) -> list[str]:
    if note_links:
        return [f"- {link}" for link in note_links]
    return [placeholder]


def _render_capture_template(title: str, summary: str, note_links: list[str]) -> str:
    lines = [
        f"# {title}",
        "",
        "## Capture",
        "",
        summary or "[Add captured insight]",
        "",
        "## Signals",
        "",
        "- [Key finding or claim]",
        "",
        "## Follow-Up Links",
        "",
        *_link_lines(note_links, "- [Add linked note]"),
        "",
        "## Next Moves",
        "",
        "- [Promote this note into concepts after linking evidence]",
    ]
    return "\n".join(lines)


def _render_concept_template(title: str, summary: str, note_links: list[str]) -> str:
    lines = [
        f"# {title}",
        "",
        "## Summary",
        "",
        summary or "[Add concept summary]",
        "",
        "## Source Notes",
        "",
        *_link_lines(note_links, "- [Add linked source notes]"),
        "",
        "## Key Claims",
        "",
        "- [Claim 1]",
        "",
        "## Evidence Gaps",
        "",
        "- [Gap or contradiction]",
        "",
        "## Open Questions",
        "",
        "- [Open question]",
    ]
    return "\n".join(lines)


def _render_review_template(title: str, summary: str, note_links: list[str]) -> str:
    lines = [
        f"# {title}",
        "",
        "## Review Goal",
        "",
        summary or "[Describe what should be reviewed or repaired]",
        "",
        "## Repair Checklist",
        "",
        "- [ ] Resolve orphan or missing links",
        "- [ ] Confirm tags, status, and note type",
        "- [ ] Connect this note to a concept or synthesis page",
        "",
        "## Related Notes",
        "",
        *_link_lines(note_links, "- [Add related note]"),
        "",
        "## Decision",
        "",
        "- [Keep / merge / retire]",
    ]
    return "\n".join(lines)


def _render_daily_template(title: str, summary: str, note_links: list[str]) -> str:
    lines = [
        f"# {title}",
        "",
        "## Date",
        "",
        f"- {datetime.now().date().isoformat()}",
        "",
        "## Captures",
        "",
        summary or "- [Observation, quote, or intake note]",
        "",
        "## Reading Log",
        "",
        *_link_lines(note_links, "- [Paper or note reviewed today]"),
        "",
        "## Follow-Ups",
        "",
        "- [Next action]",
    ]
    return "\n".join(lines)


_TEMPLATE_RENDERERS = {
    "capture": _render_capture_template,
    "concept": _render_concept_template,
    "review": _render_review_template,
    "daily": _render_daily_template,
}


def _render_template_body(
    template: str,
    *,
    title: str,
    content: str,
    source_refs: list[str],
    related_refs: list[str],
) -> str:
    normalized_template = _normalize_template_name(template)
    note_links = _refs_to_links(source_refs or related_refs)
    summary = content.strip()

    renderer = _TEMPLATE_RENDERERS.get(normalized_template)
    if renderer is not None:
        return renderer(title, summary, note_links)

    if summary and not summary.startswith("#"):
        return f"# {title}\n\n{summary}"
    if summary:
        return summary
    return f"# {title}\n"
