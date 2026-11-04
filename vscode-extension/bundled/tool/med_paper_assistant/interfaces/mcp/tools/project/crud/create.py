"""Handler for the ``create_project`` tool."""

import json

from med_paper_assistant.domain.paper_types import get_paper_type_dict
from med_paper_assistant.shared.constants import DEFAULT_WORKFLOW_MODE, WORKFLOW_MODES

from ..._shared import log_tool_call, log_tool_error, log_tool_result
from .._deps import PROJECT_MANAGER


def create_project(
    name: str,
    description: str = "",
    target_journal: str = "",
    paper_type: str = "",
    workflow_mode: str = DEFAULT_WORKFLOW_MODE,
    authors_json: str = "",
    memo: str = "",
) -> str:
    """
    Create new research project. Name MUST be English (translate if needed).

    Args:
        name: English project name (e.g., "Mortality Prediction Study")
        description: Brief research description
        target_journal: Target journal (optional)
        paper_type: Use get_paper_types; supports journal manuscripts, proposals,
            closeout reports, student papers, conference papers, theses, and preprints.
        workflow_mode: manuscript|library-wiki
        authors_json: JSON array of authors. Each entry can be a name string or structured object:
            [{"name": "Jane Doe", "affiliations": ["Dept X, Uni Y"], "orcid": "0000-...", "email": "jane@example.com", "is_corresponding": true}]
        memo: Initial notes
    """
    project_manager = PROJECT_MANAGER.get()
    log_tool_call(
        "create_project",
        {
            "name": name,
            "description": description,
            "paper_type": paper_type,
            "workflow_mode": workflow_mode,
        },
    )

    # Parse authors
    authors: list[object] = []
    if authors_json:
        try:
            authors_payload = json.loads(authors_json)
        except json.JSONDecodeError as e:
            return f"❌ Error parsing authors_json: {e}"
        if not isinstance(authors_payload, list):
            return "❌ Error: authors_json must be a JSON array."
        authors = authors_payload

    try:
        result = project_manager.create_project(
            name=name,
            description=description,
            authors=authors,
            target_journal=target_journal,
            paper_type=paper_type,
            workflow_mode=workflow_mode,
            memo=memo,
        )

        if result.get("success"):
            resolved_workflow_mode = result.get("workflow_mode", workflow_mode)
            workflow_info = WORKFLOW_MODES.get(
                resolved_workflow_mode,
                WORKFLOW_MODES[DEFAULT_WORKFLOW_MODE],
            )
            type_info = get_paper_type_dict(paper_type) if paper_type else {}
            type_name = (
                type_info.get("name", "Optional later")
                if resolved_workflow_mode == "library-wiki"
                else type_info.get("name", "Not specified")
            )
            concept_label = (
                "Library workspace seed"
                if resolved_workflow_mode == "library-wiki"
                else "Research concept (type-specific template)"
            )
            if resolved_workflow_mode == "library-wiki":
                structure_block = f"""```
{result["slug"]}/
├── project.json    ← Settings & metadata
├── concept.md      ← {concept_label}
├── .memory/        ← Project AI memory
│   ├── activeContext.md
│   └── progress.md
├── inbox/          ← Raw captured notes and triage queue
├── concepts/       ← Atomic concept pages
├── projects/       ← Synthesis pages / emerging workstreams
└── references/     ← Literature (by PMID)
```"""
            else:
                structure_block = f"""```
{result["slug"]}/
├── project.json    ← Settings & metadata
├── concept.md      ← {concept_label}
├── .memory/        ← Project AI memory
│   ├── activeContext.md
│   └── progress.md
├── drafts/         ← Paper sections
├── references/     ← Literature (by PMID)
├── data/           ← Analysis data
└── results/        ← Exported documents
```"""
            if resolved_workflow_mode == "library-wiki":
                next_steps = """1. Use `/mdpaper.search` to ingest and triage literature
2. Save references with `save_reference_mcp(pmid=...)`
3. Capture or curate markdown notes with `write_library_note`, `move_library_note`, and `search_library_notes`
4. Build knowledge pages or dashboards (`materialize_agent_wiki`, `build_knowledge_map`)
5. Switch to manuscript mode later with `project_action(action=\"update\", workflow_mode=\"manuscript\", paper_type=\"...\")` if you want to draft a paper
"""
            else:
                next_steps = """1. Use `/mdpaper.project` to configure paper type and preferences (if not set)
2. Edit `concept.md` to define your research
3. Use `/mdpaper.concept` to develop with literature support
"""

            log_tool_result(
                "create_project", f"created project slug={result['slug']}", success=True
            )
            return f"""✅ Project Created Successfully!

📁 **Project:** {name}
🔖 **Slug:** {result["slug"]}
🧭 **Workflow:** {workflow_info.get("name", resolved_workflow_mode)}
📝 **Paper Type:** {type_name}
📂 **Location:** {result["path"]}

**Structure:**
{structure_block}

**Next Steps:**
{next_steps}
"""
        else:
            log_tool_result("create_project", result.get("error", "Unknown error"), success=False)
            return f"❌ Error: {result.get('error', 'Unknown error')}"
    except Exception as e:
        log_tool_error(
            "create_project",
            e,
            {"name": name, "paper_type": paper_type, "workflow_mode": workflow_mode},
        )
        return f"❌ Error creating project: {str(e)}"
