from pathlib import Path

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence.project_manager import ProjectManager
from med_paper_assistant.interfaces.mcp.tools.project.library_notes import (
    register_library_note_tools,
)


def test_library_note_tools_round_trip(tmp_path):
    pm = ProjectManager(base_path=str(tmp_path))
    pm.create_project(name="Library", workflow_mode="library-wiki")

    funcs = register_library_note_tools(FastMCP("library-note-test"), pm)

    write_result = funcs["write_library_note"](
        section="inbox",
        filename="study-idea",
        content="This is a captured note about sedation signals.",
        tags_csv="sedation,rct",
    )
    assert "Library note created successfully" in write_result

    list_result = funcs["list_library_notes"](section="inbox")
    assert "study-idea.md" in list_result

    read_result = funcs["read_library_note"](section="inbox", filename="study-idea")
    assert "This is a captured note about sedation signals." in read_result
    assert 'section: "inbox"' in read_result

    search_result = funcs["search_library_notes"](query="sedation signals")
    assert "study-idea.md" in search_result
    assert "captured note about sedation signals" in search_result

    move_result = funcs["move_library_note"](
        filename="study-idea",
        from_section="inbox",
        to_section="concepts",
    )
    assert "Library note moved successfully" in move_result

    moved_note = tmp_path / "projects" / "library" / "concepts" / "study-idea.md"
    assert moved_note.exists()
    moved_text = moved_note.read_text(encoding="utf-8")
    assert 'section: "concepts"' in moved_text
    assert 'status: "curated"' in moved_text


def test_library_first_queue_dashboard_and_path_tools(tmp_path):
    pm = ProjectManager(base_path=str(tmp_path))
    pm.create_project(name="Library", workflow_mode="library-wiki")

    funcs = register_library_note_tools(FastMCP("library-dashboard-test"), pm)

    funcs["write_library_note"](
        section="inbox",
        filename="paper-a",
        content="This note links to [[sedation-concept]] and captures an RCT finding.",
        tags_csv="sedation,rct",
        status="reading",
    )
    concept_result = funcs["create_concept_page"](
        filename="sedation-concept",
        title="Sedation Concept",
        summary="Connects sedation signals across the saved reading queue.",
        source_notes_csv="paper-a",
        tags_csv="sedation,concept",
        open_questions="What dose-response pattern is consistent?",
    )
    assert "Concept page created successfully" in concept_result
    funcs["write_library_note"](
        section="projects",
        filename="sedation-review",
        content="This synthesis page builds on [[sedation-concept]].",
        tags_csv="sedation,review",
    )

    queue_result = funcs["show_reading_queues"]()
    assert "Active Reading" in queue_result
    assert "Concept Building" in queue_result
    assert "Synthesis Queue" in queue_result

    path_result = funcs["explain_library_path"]("paper-a", "sedation-review")
    assert "Library Path" in path_result
    assert "Sedation Concept" in path_result
    assert "links to [[sedation-concept]]" in path_result

    dashboard_result = funcs["build_library_dashboard"](view="overview")
    assert "Section Counts" in dashboard_result
    assert "Top Tags" in dashboard_result
    assert "Most Connected Notes" in dashboard_result

    synthesis_view = funcs["build_library_dashboard"](view="synthesis")
    assert "Synthesis Throughput" in synthesis_view
    assert "Synthesis Candidates" in synthesis_view
    assert "Ready-To-Synthesize Notes" in synthesis_view

    concept_path = tmp_path / "projects" / "library" / "concepts" / "sedation-concept.md"
    concept_text = concept_path.read_text(encoding="utf-8")
    assert 'type: "library-concept"' in concept_text
    assert "[[paper-a]]" in concept_text


def test_library_note_metadata_patch_and_triage_progression(tmp_path):
    pm = ProjectManager(base_path=str(tmp_path))
    pm.create_project(name="Library", workflow_mode="library-wiki")

    funcs = register_library_note_tools(FastMCP("library-triage-test"), pm)

    funcs["write_library_note"](
        section="inbox",
        filename="signal-note",
        content="Captured signal without explicit body links.",
        tags_csv="sedation",
    )
    funcs["write_library_note"](
        section="projects",
        filename="review-hub",
        content="Synthesis target for the signal cluster.",
        tags_csv="review",
    )

    metadata_result = funcs["update_library_note_metadata"](
        note_ref="signal-note",
        add_tags_csv="alpha2,signal",
        related_notes_csv="projects:review-hub",
        status="reading",
    )
    assert "Library note metadata updated successfully" in metadata_result

    signal_note = tmp_path / "projects" / "library" / "inbox" / "signal-note.md"
    signal_text = signal_note.read_text(encoding="utf-8")
    assert 'status: "reading"' in signal_text
    assert '  - "alpha2"' in signal_text
    assert '  - "projects:review-hub"' in signal_text

    path_result = funcs["explain_library_path"]("signal-note", "review-hub")
    assert "frontmatter related_notes" in path_result

    first_triage = funcs["triage_library_note"]("signal-note")
    assert "Library note triaged successfully" in first_triage
    assert "**From:** inbox/" in first_triage
    assert "**To:** concepts/" in first_triage

    curated_note = tmp_path / "projects" / "library" / "concepts" / "signal-note.md"
    assert curated_note.exists()
    curated_text = curated_note.read_text(encoding="utf-8")
    assert 'section: "concepts"' in curated_text
    assert 'status: "curated"' in curated_text
    assert '  - "alpha2"' in curated_text
    assert '  - "projects:review-hub"' in curated_text

    second_triage = funcs["triage_library_note"]("signal-note")
    assert "**From:** concepts/" in second_triage
    assert "**To:** projects/" in second_triage

    synthesized_note = tmp_path / "projects" / "library" / "projects" / "signal-note.md"
    assert synthesized_note.exists()
    synthesized_text = synthesized_note.read_text(encoding="utf-8")
    assert 'section: "projects"' in synthesized_text
    assert 'status: "synthesized"' in synthesized_text


def test_materialize_concept_page_derives_from_existing_notes(tmp_path):
    pm = ProjectManager(base_path=str(tmp_path))
    pm.create_project(name="Library", workflow_mode="library-wiki")

    funcs = register_library_note_tools(FastMCP("library-materialize-test"), pm)

    funcs["write_library_note"](
        section="inbox",
        filename="dexmedetomidine-trend",
        content="Repeated dexmedetomidine observations suggest a stable sedation thread.",
        tags_csv="sedation,alpha2",
    )

    materialize_result = funcs["materialize_concept_page"](
        source_notes_csv="dexmedetomidine-trend",
    )
    assert "Concept page materialized successfully" in materialize_result
    assert "dexmedetomidine-trend-concept.md" in materialize_result

    concept_path = (
        tmp_path / "projects" / "library" / "concepts" / "dexmedetomidine-trend-concept.md"
    )
    assert concept_path.exists()
    concept_text = concept_path.read_text(encoding="utf-8")
    assert 'type: "library-concept"' in concept_text
    assert '  - "inbox:dexmedetomidine-trend"' in concept_text
    assert '  - "concept"' in concept_text
    assert "Derived from Dexmedetomidine Trend in inbox" in concept_text

    source_path = tmp_path / "projects" / "library" / "inbox" / "dexmedetomidine-trend.md"
    source_text = source_path.read_text(encoding="utf-8")
    assert 'status: "triaged"' in source_text
    assert '  - "concepts:dexmedetomidine-trend-concept"' in source_text


def test_library_note_tools_reject_manuscript_projects(tmp_path):
    pm = ProjectManager(base_path=str(tmp_path))
    pm.create_project(name="Paper", paper_type="review-article")

    funcs = register_library_note_tools(FastMCP("library-note-guard-test"), pm)

    result = funcs["list_library_notes"]()

    assert "only available for Library Wiki Path projects" in result


def test_template_capture_and_graph_health_dashboards(tmp_path):
    pm = ProjectManager(base_path=str(tmp_path))
    created = pm.create_project(name="Library", workflow_mode="library-wiki")

    assert Path(created["structure"]["review"]).exists()
    assert Path(created["structure"]["daily"]).exists()

    funcs = register_library_note_tools(FastMCP("library-template-test"), pm)

    daily_result = funcs["write_library_note"](
        section="daily",
        filename="2026-04-22-log",
        title="2026-04-22 Sedation Log",
        content="Observed a remimazolam signal worth promoting.",
        template="daily",
        tags_csv="sedation,icu",
    )
    assert "Library note created successfully" in daily_result
    assert "**Template:** daily" in daily_result

    review_result = funcs["write_library_note"](
        section="review",
        filename="sedation-review",
        title="Sedation Repair Review",
        content="Check unresolved claim links before synthesis.",
        template="review",
        source_notes_csv="daily:2026-04-22-log",
    )
    assert "**Template:** review" in review_result

    funcs["write_library_note"](
        section="inbox",
        filename="orphan-signal",
        content="Need to connect [[missing-signal-map]].\n\nTODO: resolve sedation contradiction.",
        template="capture",
        tags_csv="sedation",
    )

    graph_health = funcs["build_library_dashboard"](view="graph-health")
    assert "Graph Health" in graph_health
    assert "Unresolved Wikilinks" in graph_health
    assert "Placeholder Markers" in graph_health
    assert "Repair Worklist" in graph_health

    review_note = tmp_path / "projects" / "library" / "review" / "sedation-review.md"
    daily_note = tmp_path / "projects" / "library" / "daily" / "2026-04-22-log.md"
    graph_dashboard = (
        tmp_path / "projects" / "library" / "notes" / "library" / "dashboard-graph-health.md"
    )
    graph_worklist = (
        tmp_path / "projects" / "library" / "notes" / "review" / "graph-repair-worklist.md"
    )

    assert review_note.exists()
    assert daily_note.exists()
    assert graph_dashboard.exists()
    assert graph_worklist.exists()

    review_text = review_note.read_text(encoding="utf-8")
    daily_text = daily_note.read_text(encoding="utf-8")
    graph_text = graph_dashboard.read_text(encoding="utf-8")
    worklist_text = graph_worklist.read_text(encoding="utf-8")

    assert 'type: "library-review"' in review_text
    assert "## Repair Checklist" in review_text
    assert 'type: "library-daily"' in daily_text
    assert "## Reading Log" in daily_text
    assert 'type: "library-dashboard"' in graph_text
    assert "## Graph Health" in graph_text
    assert "## Highest Priority Notes" in worklist_text
