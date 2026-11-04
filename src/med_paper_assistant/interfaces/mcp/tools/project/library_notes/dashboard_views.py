"""Per-view renderers and note statistics for library dashboards."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .constants import QUEUE_LABELS
from .index import _format_note_label, _materialize_dashboard_note

Note = dict[str, Any]


@dataclass
class DashboardData:
    notes: list[Note]
    section_counts: Counter[str]
    status_counts: Counter[str]
    tag_counts: Counter[str]
    connected_notes: list[Note]
    orphans: list[Note]
    cross_section_edges: int
    unresolved_notes: list[Note]
    placeholder_notes: list[Note]
    metadata_gaps: list[Note]
    unread_notes: list[Note]
    review_notes: list[Note]
    asset_notes: list[Note]


def _count_cross_section_edges(notes: list[Note]) -> int:
    notes_by_id = {note["id"]: note for note in notes}
    cross_section_edges = 0
    for note in notes:
        for linked_note_id in note.get("linked_note_ids", []):
            if notes_by_id[linked_note_id]["section"] != note["section"]:
                cross_section_edges += 1
    return cross_section_edges


def summarize_notes(notes: list[Note]) -> DashboardData:
    return DashboardData(
        notes=notes,
        section_counts=Counter(note["section"] for note in notes),
        status_counts=Counter(note["status_display"] or note["status"] for note in notes),
        tag_counts=Counter(tag for note in notes for tag in note.get("tags", [])),
        connected_notes=sorted(
            notes,
            key=lambda note: (
                len(note.get("linked_note_ids", [])) + len(note.get("backlink_ids", [])),
                note["title"],
            ),
            reverse=True,
        ),
        orphans=[
            note
            for note in notes
            if not note.get("linked_note_ids") and not note.get("backlink_ids")
        ],
        cross_section_edges=_count_cross_section_edges(notes),
        unresolved_notes=[note for note in notes if note.get("unresolved_links")],
        placeholder_notes=[note for note in notes if note.get("placeholder_markers")],
        metadata_gaps=[
            note
            for note in notes
            if not note.get("tags")
            or not note.get("related_notes")
            or not note.get("updated_at")
            or note.get("type", "") == "library-note"
        ],
        unread_notes=[
            note for note in notes if note["queue_bucket"] in {"capture", "active-reading", "daily"}
        ],
        review_notes=[
            note
            for note in notes
            if note["queue_bucket"] in {"review", "blocked"} or note["section"] == "review"
        ],
        asset_notes=[note for note in notes if note.get("asset_links")],
    )


def _view_overview(lines: list[str], data: DashboardData, limit: int) -> None:
    lines.extend(["## Section Counts", ""])
    lines.extend(f"- {section}: {count}" for section, count in sorted(data.section_counts.items()))
    lines.extend(["", "## Status Counts", ""])
    lines.extend(f"- {status}: {count}" for status, count in data.status_counts.most_common(limit))
    lines.extend(["", "## Top Tags", ""])
    if data.tag_counts:
        lines.extend(f"- {tag}: {count}" for tag, count in data.tag_counts.most_common(limit))
    else:
        lines.append("- [No tags yet]")
    lines.extend(["", "## Most Connected Notes", ""])
    lines.extend(_format_note_label(note) for note in data.connected_notes[: max(1, limit)])
    lines.extend(["", "## Orphan Notes", ""])
    if data.orphans:
        lines.extend(_format_note_label(note) for note in data.orphans[: max(1, limit)])
    else:
        lines.append("- [No orphan notes]")


def _view_queues(lines: list[str], data: DashboardData, limit: int) -> None:
    queue_counts = Counter(note["queue_bucket"] for note in data.notes)
    lines.extend(["## Queue Counts", ""])
    for bucket, label in QUEUE_LABELS.items():
        lines.append(f"- {label}: {queue_counts.get(bucket, 0)}")
    lines.extend(["", "## Active Items", ""])
    active_notes = [
        note
        for note in data.notes
        if note["queue_bucket"] in {"active-reading", "concept-build", "synthesis"}
    ]
    if active_notes:
        lines.extend(_format_note_label(note) for note in active_notes[: max(1, limit)])
    else:
        lines.append("- [No active items]")


def _view_concepts(lines: list[str], data: DashboardData, limit: int) -> None:
    concept_notes = [note for note in data.notes if note["section"] == "concepts"]
    lines.extend(["## Concept Pages", ""])
    if concept_notes:
        for note in concept_notes[: max(1, limit)]:
            lines.append(
                f"- {note['title']} ({note['filename']}) | sources: {len(note.get('linked_note_ids', []))} | backlinks: {len(note.get('backlink_ids', []))}"
            )
    else:
        lines.append("- [No concept pages yet]")


def _view_links(lines: list[str], data: DashboardData, limit: int) -> None:
    lines.extend(["## Link Health", ""])
    lines.append(f"- Cross-section edges: {data.cross_section_edges}")
    lines.append(f"- Orphan notes: {len(data.orphans)}")
    lines.append(
        f"- Unresolved wikilinks: {sum(len(note.get('unresolved_links', [])) for note in data.unresolved_notes)}"
    )
    lines.extend(["", "## Most Connected Notes", ""])
    lines.extend(_format_note_label(note) for note in data.connected_notes[: max(1, limit)])


def _shared_tag_clusters(notes: list[Note]) -> list[tuple[str, int]]:
    tag_to_notes: dict[str, set[str]] = defaultdict(set)
    for note in notes:
        for tag in note.get("tags", []):
            tag_to_notes[tag].add(note["id"])

    shared_tag_clusters = [
        (tag, len(note_ids)) for tag, note_ids in tag_to_notes.items() if len(note_ids) >= 2
    ]
    shared_tag_clusters.sort(key=lambda item: (item[1], item[0]), reverse=True)
    return shared_tag_clusters


def _view_synthesis(lines: list[str], data: DashboardData, limit: int) -> None:
    notes = data.notes
    synthesis_notes = [note for note in notes if note["queue_bucket"] == "synthesis"]
    concept_notes = [note for note in notes if note["section"] == "concepts"]
    backlog = [
        note for note in notes if note["queue_bucket"] in {"active-reading", "concept-build"}
    ]
    shared_tag_clusters = _shared_tag_clusters(notes)

    lines.extend(["## Synthesis Throughput", ""])
    lines.append(f"- Synthesis queue: {len(synthesis_notes)}")
    lines.append(f"- Concept nodes: {len(concept_notes)}")
    lines.append(f"- Pre-synthesis backlog: {len(backlog)}")
    lines.extend(["", "## Synthesis Candidates", ""])
    if shared_tag_clusters:
        for tag, size in shared_tag_clusters[: max(1, limit)]:
            lines.append(f"- tag:{tag} -> {size} linked notes")
    else:
        lines.append("- [No cross-note tag clusters yet]")

    lines.extend(["", "## Ready-To-Synthesize Notes", ""])
    if synthesis_notes:
        lines.extend(_format_note_label(note) for note in synthesis_notes[: max(1, limit)])
    else:
        lines.append("- [No synthesis notes yet]")


def repair_candidates(notes: list[Note]) -> list[Note]:
    return sorted(
        notes,
        key=lambda note: (
            len(note.get("unresolved_links", [])) * 3
            + len(note.get("placeholder_markers", [])) * 2
            + (2 if note.get("is_orphan") else 0)
            + (1 if not note.get("tags") else 0),
            note["title"],
        ),
        reverse=True,
    )


def _repair_reasons(note: Note) -> list[str]:
    reasons: list[str] = []
    if note.get("is_orphan"):
        reasons.append("orphan")
    if note.get("unresolved_links"):
        reasons.append(f"missing links: {', '.join(note['unresolved_links'][:3])}")
    if note.get("placeholder_markers"):
        reasons.append(f"placeholders: {', '.join(note['placeholder_markers'][:2])}")
    if not note.get("tags"):
        reasons.append("missing tags")
    return reasons


def _view_graph_health(lines: list[str], data: DashboardData, limit: int) -> None:
    lines.extend(["## Graph Health", ""])
    lines.append(f"- Orphan notes: {len(data.orphans)}")
    lines.append(
        f"- Unresolved wikilinks: {sum(len(note.get('unresolved_links', [])) for note in data.unresolved_notes)}"
    )
    lines.append(
        f"- Placeholder markers: {sum(len(note.get('placeholder_markers', [])) for note in data.placeholder_notes)}"
    )
    lines.append(f"- Metadata gaps: {len(data.metadata_gaps)}")
    lines.extend(["", "## Repair Priority", ""])

    for note in repair_candidates(data.notes)[: max(1, limit)]:
        reasons = _repair_reasons(note)
        if not reasons:
            continue
        lines.append(f"- [{note['section']}] {note['title']} -> {'; '.join(reasons)}")

    lines.extend(["", "## Unresolved Wikilinks", ""])
    if data.unresolved_notes:
        for note in data.unresolved_notes[: max(1, limit)]:
            lines.append(
                f"- [{note['section']}] {note['filename']}: {', '.join(note['unresolved_links'][:4])}"
            )
    else:
        lines.append("- [No unresolved wikilinks]")

    lines.extend(["", "## Placeholder Markers", ""])
    if data.placeholder_notes:
        for note in data.placeholder_notes[: max(1, limit)]:
            lines.append(
                f"- [{note['section']}] {note['filename']}: {', '.join(note['placeholder_markers'][:4])}"
            )
    else:
        lines.append("- [No placeholder markers]")


def _repair_checklist(note: Note) -> list[str]:
    checklist: list[str] = []
    if note.get("is_orphan"):
        checklist.append("link this note to at least one concept, project, or review page")
    if note.get("unresolved_links"):
        checklist.append(f"resolve missing wikilinks: {', '.join(note['unresolved_links'][:4])}")
    if note.get("placeholder_markers"):
        checklist.append(f"replace placeholders: {', '.join(note['placeholder_markers'][:3])}")
    if not note.get("tags"):
        checklist.append("add tags")
    return checklist


def materialize_graph_health(
    info: Note, lines: list[str], data: DashboardData, limit: int
) -> tuple[Path, Path]:
    dashboard_path = _materialize_dashboard_note(
        info,
        directory="library",
        slug="dashboard-graph-health",
        title="Graph Health Dashboard",
        body_lines=lines,
        note_type="library-dashboard",
        tags=["dashboard/library", "dashboard/graph-health", "workflow/library-first"],
        extra_fields={"note_class": "library-dashboard", "note_domain": "library"},
    )

    repair_lines = [
        "# Graph Repair Worklist",
        "",
        "## Highest Priority Notes",
        "",
    ]
    for note in repair_candidates(data.notes)[: max(1, limit)]:
        checklist = _repair_checklist(note)
        if not checklist:
            continue
        repair_lines.append(f"## [{note['section']}] {note['title']}")
        repair_lines.append("")
        repair_lines.extend(f"- [ ] {item}" for item in checklist)
        repair_lines.append("")

    repair_path = _materialize_dashboard_note(
        info,
        directory="review",
        slug="graph-repair-worklist",
        title="Graph Repair Worklist",
        body_lines=repair_lines,
        note_type="library-review",
        tags=["workflow/review", "dashboard/graph-health", "repair-worklist"],
        extra_fields={
            "note_class": "library-review",
            "note_domain": "library",
            "review_state": "pending",
        },
    )
    return dashboard_path, repair_path


def _view_unread(lines: list[str], data: DashboardData, limit: int) -> None:
    lines.extend(["## Unread / Intake Backlog", ""])
    if data.unread_notes:
        for note in sorted(
            data.unread_notes,
            key=lambda item: (item.get("updated_at", ""), item["filename"]),
            reverse=True,
        )[: max(1, limit)]:
            lines.append(_format_note_label(note))
    else:
        lines.append("- [No unread intake notes]")


def _metadata_gap_names(note: Note) -> list[str]:
    gaps: list[str] = []
    if not note.get("tags"):
        gaps.append("tags")
    if not note.get("related_notes"):
        gaps.append("related_notes")
    if not note.get("updated_at"):
        gaps.append("updated_at")
    if note.get("type", "") == "library-note":
        gaps.append("specialized note type")
    return gaps


def _view_metadata(lines: list[str], data: DashboardData, limit: int) -> None:
    lines.extend(["## Metadata Gaps", ""])
    if data.metadata_gaps:
        for note in data.metadata_gaps[: max(1, limit)]:
            gaps = _metadata_gap_names(note)
            lines.append(f"- [{note['section']}] {note['filename']}: {', '.join(gaps)}")
    else:
        lines.append("- [No metadata gaps]")


def _view_review(lines: list[str], data: DashboardData, limit: int) -> None:
    lines.extend(["## Review Queue", ""])
    if data.review_notes:
        for note in data.review_notes[: max(1, limit)]:
            lines.append(_format_note_label(note))
    else:
        lines.append("- [No review notes yet]")
    lines.extend(["", "## Review Inputs", ""])
    lines.append(
        f"- Blocked notes: {sum(1 for note in data.notes if note['queue_bucket'] == 'blocked')}"
    )
    lines.append(f"- Placeholder-bearing notes: {len(data.placeholder_notes)}")


def _view_assets(lines: list[str], data: DashboardData, limit: int) -> None:
    lines.extend(["## Asset-Linked Notes", ""])
    if data.asset_notes:
        for note in data.asset_notes[: max(1, limit)]:
            lines.append(
                f"- [{note['section']}] {note['filename']}: {', '.join(note['asset_links'][:4])}"
            )
    else:
        lines.append("- [No asset links yet]")


ViewRenderer = Callable[[list[str], DashboardData, int], None]

VIEW_RENDERERS: dict[str, ViewRenderer] = {
    "overview": _view_overview,
    "queues": _view_queues,
    "concepts": _view_concepts,
    "links": _view_links,
    "synthesis": _view_synthesis,
    "graph-health": _view_graph_health,
    "unread": _view_unread,
    "metadata": _view_metadata,
    "review": _view_review,
    "assets": _view_assets,
}
