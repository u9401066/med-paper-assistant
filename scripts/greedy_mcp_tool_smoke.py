from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import sys
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from mcp import Client
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_PROJECTS_RESOURCE = "medpaper://workspace/projects"
TEMPLATE_CATALOG_RESOURCE = "medpaper://templates/catalog"
SKIP_CATEGORY_ORDER = ("interactive", "external", "other")
STABLE_SUMMARY_VERSION = "greedy-smoke-summary-v1"

SAFE_TOOL_ORDER = [
    "create_project",
    "start_exploration",
    "convert_exploration_to_project",
    "project_action",
    "switch_project",
    "workspace_state_action",
    "get_workspace_state",
    "validate_concept",
    "approve_concept_review",
    "patch_draft",
    "start_document_session",
    "insert_section",
    "verify_document",
    "save_document",
    "review_asset_for_insertion",
    "insert_figure",
    "insert_table",
    "start_review_round",
    "submit_review_round",
    "run_review_hooks",
    "run_quality_checks",
    "pipeline_action",
    "inspect_export",
    "export_document",
    "list_projects",
]
LIBRARY_PATH_TOOLS = {
    "library_action",
    "list_library_notes",
    "read_library_note",
    "write_library_note",
    "move_library_note",
    "triage_library_note",
    "update_library_note_metadata",
    "search_library_notes",
    "show_reading_queues",
    "create_concept_page",
    "materialize_concept_page",
    "explain_library_path",
    "build_library_dashboard",
}
PRECONDITION_MARKERS = (
    "concept file not found",
    "data file",
    "document session",
    "no manuscript found",
    "not found",
    "project context",
    "pandoc not available",
    "only allowed from phase 7",
    "use `/mdpaper",
    "valid project",
)


@dataclass(frozen=True, slots=True)
class SkipDecision:
    category: str
    reason: str


SKIP_TOOLS = {
    "setup_project_interactive": SkipDecision(
        category="interactive",
        reason="requires an elicitation-capable MCP client",
    ),
    "save_reference_mcp": SkipDecision(
        category="external",
        reason="requires live PubMed/network metadata",
    ),
    "retry_pdf_download": SkipDecision(
        category="external",
        reason="requires a previously saved reference and network access",
    ),
}


@dataclass(slots=True)
class SmokeContext:
    workspace_root: Path
    project_slug: str | None = None
    project_path: Path | None = None
    template_name: str | None = None
    sample_csv_name: str = "sample.csv"
    draft_name: str = "manuscript.md"
    concept_name: str = "concept.md"
    reference_pmid: str = "27345583"
    reference_citation_key: str = "greer2017_27345583"
    reference_target_text: str = "Synthetic CSV data were analyzed."
    fake_pdf_base64: str = "JVBERi0xLjQKU21va2UgcGRmIGZpeHR1cmUKJSVFT0Y="


@dataclass(slots=True)
class ToolOutcome:
    name: str
    status: str
    detail: str
    arguments: dict[str, Any] | None = None
    skip_category: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run MedPaper MCP tools one-by-one with a conservative greedy smoke strategy.",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Optional workspace directory. Defaults to an isolated temporary workspace.",
    )
    parser.add_argument(
        "--surface",
        choices=("compact", "full"),
        default="compact",
        help="MCP tool surface to exercise. Defaults to the production compact surface.",
    )
    parser.add_argument(
        "--match",
        default="",
        help="Only run tools whose names contain this substring.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max number of tools to run after filtering.",
    )
    parser.add_argument(
        "--stop-on",
        choices=("broken", "error", "precondition", "never"),
        default="broken",
        help="Fail-fast threshold. 'broken' stops only on transport/runtime failures.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of line-oriented text.",
    )
    return parser.parse_args()


@asynccontextmanager
async def open_mcp_session(workspace_root: Path, surface: str) -> AsyncIterator[Client]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    src_path = str(ROOT / "src")
    env["PYTHONPATH"] = src_path if not existing else os.pathsep.join([src_path, existing])
    env["MEDPAPER_BASE_DIR"] = str(workspace_root)
    env["MEDPAPER_TOOL_SURFACE"] = surface

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "med_paper_assistant.interfaces.mcp"],
        cwd=str(workspace_root),
        env=env,
    )

    async with Client(stdio_client(params), mode="2026-07-28") as client:
        yield client


def prioritize_tool_names(tool_names: list[str]) -> list[str]:
    priority = [name for name in SAFE_TOOL_ORDER if name in tool_names]
    remainder = sorted(name for name in tool_names if name not in SAFE_TOOL_ORDER)
    return priority + remainder


def extract_parameters_schema(tool: Any) -> dict[str, Any]:
    schema = getattr(tool, "parameters", None)
    if isinstance(schema, dict):
        return schema

    for candidate in ("input_schema", "schema"):
        value = getattr(tool, candidate, None)
        if isinstance(value, dict):
            return value

    return {}


def build_score_payload() -> str:
    return json.dumps(
        {
            "citation_quality": 7,
            "methodology_reproducibility": 7,
            "text_quality": 7,
            "concept_consistency": 7,
            "format_compliance": 7,
            "figure_table_quality": 7,
        }
    )


def default_string_value(tool_name: str, property_name: str, context: SmokeContext) -> str | None:
    if property_name == "project":
        return context.project_slug
    if property_name in {"slug", "project_slug"}:
        return context.project_slug
    if property_name in {"name", "project_name"}:
        if tool_name == "convert_exploration_to_project":
            return "Exploration Smoke Project"
        return "Greedy Smoke Project"
    if property_name == "description":
        return "Greedy MCP smoke sandbox"
    if property_name == "article":
        return json.dumps(
            {
                "pmid": context.reference_pmid,
                "title": "Synthetic academic-writing smoke reference",
                "authors": ["Greer JA", "Lee DH"],
                "year": "2017",
                "journal": "Smoke Test Journal",
                "abstract": "Synthetic metadata for an isolated MCP smoke test.",
            }
        )
    if property_name == "paper_type":
        return "other"
    if property_name == "workflow_mode":
        return "manuscript"
    if property_name == "authors_json":
        return "[]"
    if property_name == "memo":
        return "smoke test"
    if property_name == "filename":
        if tool_name == "save_diagram":
            return "smoke-diagram.drawio"
        if tool_name in {"insert_figure", "review_asset_for_insertion"}:
            return "smoke-figure.png"
        if tool_name == "insert_table":
            return context.sample_csv_name
        if tool_name in {"read_library_note", "write_library_note"}:
            return "smoke-note.md"
        if tool_name == "move_library_note":
            return "move-note.md"
        if tool_name in {"create_concept_page", "materialize_concept_page"}:
            return "smoke-concept.md"
        if "concept" in tool_name:
            return context.concept_name
        if any(
            token in tool_name for token in ("dataset", "plot", "table", "statistical", "variable")
        ):
            return context.sample_csv_name
        return context.draft_name
    if property_name == "draft_filename":
        return context.draft_name
    if property_name == "session_id":
        return "default"
    if property_name == "section_name":
        return "Introduction"
    if property_name == "target_text":
        return context.reference_target_text
    if property_name == "journal":
        return "generic"
    if property_name == "query":
        return "smoke test"
    if property_name == "note_ref" and tool_name == "update_library_note_metadata":
        return "inbox/related-note.md"
    if property_name in {"note_ref", "source_note"}:
        return "inbox/smoke-note.md"
    if property_name == "target_note":
        return "inbox/related-note.md"
    if property_name == "from_section":
        return "inbox"
    if property_name == "to_section":
        return "concepts"
    if property_name == "source_notes_csv":
        return "inbox/smoke-note.md"
    if property_name == "scores":
        return build_score_payload()
    if property_name == "hooks":
        return "all"
    if property_name == "hook_id":
        return "A1"
    if property_name == "event_type":
        return "trigger"
    if property_name == "section":
        if tool_name in LIBRARY_PATH_TOOLS:
            return "inbox"
        return "Introduction"
    if property_name == "sections":
        return "Introduction"
    if property_name == "objective":
        return "Smoke test objective"
    if property_name == "citation_keys":
        return ""
    if property_name == "draft_content":
        return "# Smoke Draft\n\nThis is a smoke-test draft."
    if property_name == "old_text" and tool_name == "patch_draft":
        return "Smoke test manuscript."
    if property_name == "new_text" and tool_name == "patch_draft":
        return "Smoke test manuscript revision."
    if property_name == "content":
        if tool_name == "save_diagram":
            return '<mxfile><diagram id="smoke" name="Page-1">smoke</diagram></mxfile>'
        return "Smoke test content"
    if property_name == "markdown_text":
        return "# Smoke Source\n\nEvidence-grounded synthetic source."
    if property_name == "template_name":
        return context.template_name or ""
    if property_name == "output_filename":
        return "smoke-output.docx"
    if property_name == "variables":
        return "value,age"
    if property_name == "test_type":
        return "correlation"
    if property_name == "plot_type":
        return "histogram"
    if property_name == "x_var":
        return "age"
    if property_name == "y_var":
        return "value"
    if property_name in {"group_var", "group_col"}:
        return "group"
    if property_name == "continuous_cols":
        return "value,age"
    if property_name == "categorical_cols":
        return "group"
    if property_name == "asset_type":
        return "figure"
    if property_name == "caption":
        if tool_name == "insert_figure":
            return "Synthetic figure used for protocol smoke testing."
        if tool_name == "insert_table":
            return "Synthetic table used for protocol smoke testing."
        return "Synthetic smoke-test asset."
    if property_name == "observations":
        return "The synthetic fixture is readable | Labels and values are internally consistent."
    if property_name == "rationale":
        if tool_name == "approve_concept_review":
            return "Smoke-test approval after deterministic offline validation."
        return "Exercises the content-integrity and insertion review gate."
    if property_name == "proposed_caption":
        return "Synthetic figure used for protocol smoke testing."
    if property_name == "visible_watermark_review":
        return "Human-reviewed fixture; no visible watermark observed."
    if property_name == "feedback":
        return "smoke test"
    if property_name == "reason":
        return "Smoke-test precondition and audit trail"
    if property_name == "reference_id":
        return f"pmid:{context.reference_pmid}"
    if property_name == "category":
        return "boundary"
    if property_name == "constraint_id":
        return "B999"
    if property_name == "rule":
        return "Synthetic smoke constraints must remain isolated."
    if property_name == "title":
        return "Smoke Test Note"
    if property_name == "summary":
        return "Synthetic smoke-test summary."
    if tool_name == "save_reference_analysis" and property_name == "methodology":
        return "Synthetic cohort methodology with deterministic offline fixtures."
    if tool_name == "save_reference_analysis" and property_name == "key_findings":
        return "The controlled smoke workflow completed its expected reference checks."
    if tool_name == "save_reference_analysis" and property_name == "limitations":
        return "Synthetic evidence cannot support real clinical or scientific claims."
    if tool_name == "save_reference_analysis" and property_name == "usage_sections":
        return "Introduction,Discussion"
    if property_name == "action":
        tool_actions = {
            "run_quality_checks": "writing_hooks",
            "pipeline_action": "heartbeat",
            "project_action": "create" if context.project_slug is None else "current",
            "workspace_state_action": "get",
            "export_document": "session_start",
            "inspect_export": "list_templates",
            "analysis_action": "list_assets",
            "draft_action": "list_drafts",
            "library_action": "list_notes",
            "reference_action": "list",
            "validation_action": "list",
        }
        return tool_actions.get(tool_name, "approve")
    if property_name == "pmid":
        return context.reference_pmid
    if property_name == "pmids":
        return context.reference_pmid
    if property_name == "pdf_content":
        return context.fake_pdf_base64
    if property_name == "prefer_language":
        return "american"
    if property_name == "target_journal":
        return ""
    return "smoke-test"


def build_value_from_schema(
    tool_name: str,
    property_name: str,
    property_schema: dict[str, Any],
    context: SmokeContext,
) -> Any:
    curated_strings = {
        ("approve_concept_review", "rationale"),
        ("convert_exploration_to_project", "workflow_mode"),
        ("ingest_markdown_source", "markdown_text"),
        ("project_action", "name"),
        ("resolve_reference_identity", "pmid"),
        ("review_asset_for_insertion", "visible_watermark_review"),
        ("save_reference_analysis", "key_findings"),
        ("save_reference_analysis", "limitations"),
        ("save_reference_analysis", "methodology"),
        ("save_reference_analysis", "usage_sections"),
        ("update_library_note_metadata", "title"),
        ("write_draft", "content"),
        ("write_draft", "filename"),
        ("write_pipeline_retrospective", "summary"),
    }
    if property_name in {"project", "project_slug", "slug"} and context.project_slug:
        return default_string_value(tool_name, property_name, context)
    if (tool_name, property_name) in curated_strings:
        return default_string_value(tool_name, property_name, context)
    if property_name == "skip_validation" and tool_name in {"draft_section", "write_draft"}:
        return True
    if property_name == "run_novelty_check":
        return False
    if property_name == "structure_only":
        # The full concept path writes the machine-readable review artifact
        # required by approve_concept_review; novelty remains disabled so this
        # smoke stays deterministic and offline.
        return tool_name != "validate_concept"
    if tool_name == "run_review_hooks" and property_name == "round_num":
        return 1
    if tool_name == "save_reference_analysis" and property_name == "relevance_score":
        return 3

    enum_values = property_schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        return enum_values[0]

    if "default" in property_schema:
        return property_schema["default"]

    value_type = property_schema.get("type")
    if isinstance(value_type, list):
        value_type = next((item for item in value_type if item != "null"), value_type[0])

    if value_type == "boolean":
        if property_name == "run_novelty_check":
            return False
        if property_name == "structure_only":
            return True
        return False

    if value_type == "integer":
        if property_name in {"issues_found", "issues_fixed"}:
            return 0
        return 1

    if value_type == "number":
        return 1

    if value_type == "array":
        if property_name == "sections":
            return ["Introduction"]
        return []

    if value_type == "object":
        return {}

    return default_string_value(tool_name, property_name, context)


def build_tool_arguments(
    tool_name: str,
    schema: dict[str, Any],
    context: SmokeContext,
) -> dict[str, Any] | None:
    if tool_name in SKIP_TOOLS:
        return None

    raw_properties = schema.get("properties")
    properties: dict[str, Any] = raw_properties if isinstance(raw_properties, dict) else {}
    raw_required = schema.get("required")
    required: list[str] = (
        [item for item in raw_required if isinstance(item, str)]
        if isinstance(raw_required, list)
        else []
    )

    arguments: dict[str, Any] = {}
    forced_optional_inputs = {
        ("approve_concept_review", "rationale"),
        ("convert_exploration_to_project", "workflow_mode"),
        ("draft_section", "skip_validation"),
        ("ingest_markdown_source", "markdown_text"),
        ("resolve_reference_identity", "pmid"),
        ("review_asset_for_insertion", "visible_watermark_review"),
        ("run_review_hooks", "round_num"),
        ("save_reference_analysis", "key_findings"),
        ("save_reference_analysis", "limitations"),
        ("save_reference_analysis", "methodology"),
        ("save_reference_analysis", "relevance_score"),
        ("save_reference_analysis", "usage_sections"),
        ("update_library_note_metadata", "title"),
        ("write_draft", "content"),
        ("write_draft", "filename"),
        ("write_draft", "skip_validation"),
        ("write_pipeline_retrospective", "summary"),
    }
    for property_name, property_schema in properties.items():
        if not isinstance(property_schema, dict):
            property_schema = {}

        if (
            property_name in required
            or property_name
            in {
                "project",
                "run_novelty_check",
                "structure_only",
                "check_submission",
            }
            or (tool_name == "project_action" and property_name == "name")
            or (tool_name, property_name) in forced_optional_inputs
        ):
            value = build_value_from_schema(tool_name, property_name, property_schema, context)
            if value is None and property_name in required:
                return None
            if value is not None:
                arguments[property_name] = value

    for property_name in required:
        if property_name not in arguments:
            return None

    return arguments


def should_skip_tool(tool_name: str, schema: dict[str, Any]) -> SkipDecision | None:
    if tool_name in SKIP_TOOLS:
        return SKIP_TOOLS[tool_name]

    return None


def render_call_result(result: Any) -> str:
    parts: list[str] = []
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        parts.append(json.dumps(structured, ensure_ascii=False, sort_keys=True))

    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text:
            parts.append(text)

    if not parts:
        message = getattr(result, "message", None)
        if message:
            parts.append(str(message))

    return "\n".join(part for part in parts if part).strip()


def classify_call_outcome(result: Any, rendered_text: str) -> tuple[str, str]:
    if getattr(result, "is_error", False):
        return "broken", rendered_text or "MCP call marked as error"

    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        structured_status = str(structured.get("status", "")).strip().casefold()
        declares_failure = (
            structured.get("ok") is False
            or structured.get("success") is False
            or structured_status in {"error", "failed", "failure", "broken"}
        )
        if declares_failure:
            detail = rendered_text or json.dumps(structured, ensure_ascii=False, sort_keys=True)
            lowered_detail = detail.casefold()
            if any(marker in lowered_detail for marker in PRECONDITION_MARKERS):
                return "precondition", detail
            return "error", detail

        for field in ("error", "message", "detail", "result"):
            value = structured.get(field)
            if not isinstance(value, str) or not value.strip():
                continue
            lowered_value = value.casefold().lstrip()
            if not lowered_value.startswith(("❌", "error:", "failed:", "failure:")):
                continue
            if any(marker in lowered_value for marker in PRECONDITION_MARKERS):
                return "precondition", value
            return "error", value

    lowered = rendered_text.casefold()
    error_prefixes = ("❌", "error:", "failed:", "failure:")
    if lowered.lstrip().startswith(error_prefixes):
        if any(marker in lowered for marker in PRECONDITION_MARKERS):
            return "precondition", rendered_text
        return "error", rendered_text

    return "ok", rendered_text or "call succeeded"


def prepare_project_fixtures(context: SmokeContext) -> None:
    if context.project_path is None:
        return

    drafts_dir = context.project_path / "drafts"
    data_dir = context.project_path / "data"
    refs_dir = context.project_path / "references"
    figures_dir = context.project_path / "results" / "figures"
    tables_dir = context.project_path / "results" / "tables"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    refs_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    for section in ("inbox", "concepts", "projects", "review", "daily"):
        (context.project_path / section).mkdir(parents=True, exist_ok=True)

    (context.project_path / context.concept_name).write_text(
        "# Research Concept\n\n"
        "## Research Question\n"
        "Does smoke-test exposure improve smoke-test outcomes?\n\n"
        "## Novelty\n"
        "This is a synthetic concept for tool smoke testing.\n\n"
        "## Methods\n"
        "Retrospective synthetic cohort.\n",
        encoding="utf-8",
    )
    (drafts_dir / context.draft_name).write_text(
        "# Introduction\n\nSmoke test manuscript.\n\n"
        "# Methods\n\nSynthetic CSV data were analyzed.\n\n"
        "# Results\n\nThe smoke runner produced deterministic fixtures.\n",
        encoding="utf-8",
    )
    (drafts_dir / "draft.md").write_text("# Smoke Draft\n", encoding="utf-8")
    sample_csv = "group,value,age\nA,1,30\nA,2,31\nB,3,29\nB,4,28\n"
    (data_dir / context.sample_csv_name).write_text(sample_csv, encoding="utf-8")
    (tables_dir / context.sample_csv_name).write_text(sample_csv, encoding="utf-8")
    (figures_dir / "smoke-figure.png").write_bytes(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAUAAAAFACAIAAABC8jL9AAACtUlEQVR42u3TMQ0AMAgAwVL/"
            "EllY0IEHNpI7CZ98ZPUDbvoSgIEBAwMGBgMDBgYMDBgYDAwYGDAwGBgwMGBgwMBgYMDAgIEB"
            "A4OBAQMDBgYDAwYGDAwYGAwMGBgwMGBgMDBgYMDAYGDAwICBAQODgQEDAwYGAwMGBgwMGBgM"
            "DBgYMDBgYDAwYGDAwGBgwMCAgQEDg4EBAwMGBgwMBgYMDBgYDAwYGDAwYGAwMGBgwMCAgcHA"
            "gIEBA4OBAQMDBgYMDAYGDAwYGAwMGBgwMGBgMDBgYMDAgIHBwICBAQODgQEDAwYGDAwGBgwMG"
            "BgwMBgYMDBgYDAwYGDAwICBwcCAgQEDAwYGAwMGBgwMBgYMDBgYMDAYGDAwYGAwMGBgwMCAg"
            "cHAgIEBAwMGBgMDBgYMDAYGDAwYGDAwGBgwMGBgwMBgYMDAgIHBwICBAQMDBgYDAwYGDAwGBg"
            "wMGBgwMBgYMDBgYMDAYGDAwICBwcCAgQEDAwYGAwMGBgwMGBgMDBgYMDAYGDAwYGDAwGBgwMC"
            "AgQEDg4EBAwMGBgMDBgYMDBgYDAwYGDAwGBgwMGBgwMBgYMDAgIEBA4OBAQMDBgYDAwYGDAwY"
            "GAwMGBgwMGBgMDBgYMDAYGDAwICBAQODgQEDAwYGDAwGBgwMGBgMDBgYMDBgYDAwYGDAwGBgw"
            "MCAgQEDg4EBAwMGBgwMBgYMDBgYDAwYGDAwYGAwMGBgwMCAgcHAgIEBA4OBAQMDBgYMDAYGDA"
            "wYGAwsARgYMDBgYDAwYGDAwICBwcCAgQEDg4EBAwMGBgwMBgYMDBgYMDAYGDAwYGAwMGBgwMC"
            "AgcHAgIEBAwMGBgMDBgYMDAYGDAwYGDAwGBgwMGBgMDBgYMDAgIHBwICBAQMDBgYDAwYGDAwG"
            "BgwMGBgwMBgYMDBgYMDAYGDAwMDOAKmOBSMxLNaMAAAAAElFTkSuQmCC"
        )
    )
    for note_name in ("smoke-note.md", "move-note.md", "related-note.md"):
        (context.project_path / "inbox" / note_name).write_text(
            "---\ntitle: Smoke Fixture\nstatus: inbox\n---\n\nSynthetic library note.\n",
            encoding="utf-8",
        )

    ref_dir = refs_dir / context.reference_pmid
    ref_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "pmid": context.reference_pmid,
        "title": "Review of remimazolam sedation in ICU patients",
        "authors": ["Greer JA", "Lee DH"],
        "authors_full": [
            {"last_name": "Greer", "first_name": "Joseph A"},
            {"last_name": "Lee", "first_name": "Dong H"},
        ],
        "year": "2017",
        "journal": "British Journal of Anaesthesia",
        "doi": "10.1093/bja/aex001",
        "abstract": "Synthetic abstract used by greedy MCP smoke fixtures.",
        "fulltext_ingested": False,
        "fulltext_unavailable_reason": "synthetic_fixture_has_no_fulltext_source",
        "citation_key": context.reference_citation_key,
        "citation": {
            "vancouver": "Greer JA, Lee DH. Review of remimazolam sedation in ICU patients. Br J Anaesth. 2017;118(1):1-5. PMID:27345583",
            "apa": "Greer, J. A., & Lee, D. H. (2017). Review of remimazolam sedation in ICU patients. British Journal of Anaesthesia, 118(1), 1-5.",
            "nature": "Greer, J. A. & Lee, D. H. Review of remimazolam sedation in ICU patients. Br. J. Anaesth. 118, 1-5 (2017).",
            "in_text": "Greer & Lee, 2017",
        },
        "analysis_completed": False,
    }
    (ref_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (ref_dir / f"{context.reference_citation_key}.md").write_text(
        "---\n"
        f'title: "{metadata["title"]}"\n'
        f'pmid: "{context.reference_pmid}"\n'
        f'aliases: [{context.reference_citation_key}, "PMID:{context.reference_pmid}"]\n'
        "---\n\n"
        "Synthetic reference fixture for greedy MCP smoke tests.\n",
        encoding="utf-8",
    )


def prepare_review_fixtures(context: SmokeContext) -> None:
    """Create deterministic Phase 7 artifacts after the review round starts."""
    if context.project_path is None:
        return

    audit_dir = context.project_path / ".audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    review_body = " ".join(
        [
            "Methodology domain statistics writing editor review identifies one major issue and "
            "one minor issue. Evidence, reproducibility, transparent reporting, and citation "
            "traceability are evaluated with a concrete correction recommendation."
        ]
        * 18
    )
    (audit_dir / "review-report-1.md").write_text(
        "---\nround: 1\ntotal:\n  major: 1\n  minor: 1\n  optional: 0\n---\n"
        "# Review Report\n\n## Major issue 1\n\n"
        f"{review_body}\n\n## Minor issue 1\n\nClarify the synthetic fixture wording.\n",
        encoding="utf-8",
    )
    (audit_dir / "author-response-1.md").write_text(
        "# Author Response\n\n"
        "## Major issue 1 — ACCEPT\n\n"
        "Implemented the correction with evidence from [[greer2017_27345583]].\n\n"
        "## Minor issue 1 — ACCEPT\n\nClarified wording using the fixture data.\n",
        encoding="utf-8",
    )
    (audit_dir / "equator-compliance-1.md").write_text(
        "# EQUATOR Compliance\n\n"
        "- [x] Item 1: title\n- [x] Item 2: abstract\n- [x] Item 3: methods\n"
        "- [x] Item 4: results\n- [x] Item 5: limitations\n",
        encoding="utf-8",
    )
    manuscript = context.project_path / "drafts" / context.draft_name
    with manuscript.open("a", encoding="utf-8") as stream:
        stream.write("\n\nReview round 1 clarified the synthetic evidence trail.\n")


def serialize_outcome(outcome: ToolOutcome) -> dict[str, Any]:
    payload = asdict(outcome)
    if outcome.skip_category is None:
        payload.pop("skip_category")
    return payload


def should_stop(stop_on: str, status: str) -> bool:
    if stop_on == "never":
        return False
    if stop_on == "broken":
        return status == "broken"
    if stop_on == "error":
        return status in {"broken", "error"}
    return status in {"broken", "error", "precondition"}


def summarize_counts(outcomes: list[ToolOutcome]) -> dict[str, int]:
    counts = {
        "total": len(outcomes),
        "ok": 0,
        "skipped": 0,
        "skipped_interactive": 0,
        "skipped_external": 0,
        "skipped_other": 0,
        "precondition": 0,
        "error": 0,
        "broken": 0,
    }
    for outcome in outcomes:
        counts[outcome.status] = counts.get(outcome.status, 0) + 1
        if outcome.status == "skipped":
            category = outcome.skip_category or "other"
            counts[f"skipped_{category}"] = counts.get(f"skipped_{category}", 0) + 1
    return counts


def normalize_detail_for_summary(detail: str, workspace_root: Path) -> str:
    first_line = detail.splitlines()[0].strip() if detail else ""
    workspace_variants = {
        str(workspace_root),
        str(workspace_root).replace("\\", "/"),
    }
    normalized = first_line
    for variant in workspace_variants:
        normalized = normalized.replace(variant, "<workspace>")
    return normalized.replace("\\", "/")


def build_stable_summary(
    outcomes: list[ToolOutcome],
    counts: dict[str, int],
    args: argparse.Namespace,
    workspace_root: Path,
    workspace_mode: str,
) -> dict[str, Any]:
    grouped_tools: dict[str, Any] = {
        "ok": [],
        "precondition": [],
        "error": [],
        "broken": [],
        "skipped": {category: [] for category in SKIP_CATEGORY_ORDER},
    }
    execution: list[dict[str, Any]] = []

    for outcome in outcomes:
        execution_item: dict[str, Any] = {
            "tool": outcome.name,
            "status": outcome.status,
        }

        if outcome.status == "skipped":
            skip_category = outcome.skip_category or "other"
            grouped_tools["skipped"][skip_category].append(outcome.name)
            execution_item["skip_category"] = skip_category
            execution_item["detail"] = normalize_detail_for_summary(outcome.detail, workspace_root)
        else:
            grouped_tools[outcome.status].append(outcome.name)
            if outcome.status != "ok":
                execution_item["detail"] = normalize_detail_for_summary(
                    outcome.detail, workspace_root
                )

        execution.append(execution_item)

    for status in ("ok", "precondition", "error", "broken"):
        grouped_tools[status].sort()
    for category in SKIP_CATEGORY_ORDER:
        grouped_tools["skipped"][category].sort()

    return {
        "summary_format": STABLE_SUMMARY_VERSION,
        "workspace_mode": workspace_mode,
        "selection": {
            "surface": getattr(args, "surface", "compact"),
            "match": args.match or None,
            "limit": args.limit or None,
            "stop_on": args.stop_on,
        },
        "counts": counts,
        "execution": execution,
        "grouped_tools": grouped_tools,
    }


def build_json_report(
    outcomes: list[ToolOutcome],
    counts: dict[str, int],
    args: argparse.Namespace,
    workspace_root: Path,
    workspace_mode: str,
) -> dict[str, Any]:
    return {
        "format_version": "greedy-smoke-json-v2",
        "workspace": str(workspace_root),
        "workspace_mode": workspace_mode,
        "selection": {
            "surface": getattr(args, "surface", "compact"),
            "match": args.match or None,
            "limit": args.limit or None,
            "stop_on": args.stop_on,
        },
        "counts": counts,
        "stable_summary": build_stable_summary(
            outcomes, counts, args, workspace_root, workspace_mode
        ),
        "results": [serialize_outcome(outcome) for outcome in outcomes],
    }


def extract_text_resource(result: Any) -> str:
    contents = getattr(result, "contents", []) or []
    if not contents:
        return ""
    text = getattr(contents[0], "text", None)
    return text or ""


async def refresh_context(session: Client, context: SmokeContext) -> None:
    projects_result = await session.read_resource(WORKSPACE_PROJECTS_RESOURCE)
    payload = json.loads(extract_text_resource(projects_result) or "{}")
    current = payload.get("current")
    slug: str | None = None
    if isinstance(current, str):
        slug = current
    elif isinstance(current, dict):
        maybe_slug = current.get("slug")
        if isinstance(maybe_slug, str):
            slug = maybe_slug

    if slug is None:
        projects = payload.get("projects")
        if isinstance(projects, list) and projects:
            first = projects[0]
            if isinstance(first, dict):
                maybe_slug = first.get("slug")
                if isinstance(maybe_slug, str):
                    slug = maybe_slug

    context.project_slug = slug
    context.project_path = context.workspace_root / "projects" / slug if slug else None

    template_result = await session.read_resource(TEMPLATE_CATALOG_RESOURCE)
    template_payload = json.loads(extract_text_resource(template_result) or "{}")
    templates = template_payload.get("templates")
    if isinstance(templates, list) and templates:
        first_template = templates[0]
        if isinstance(first_template, str):
            context.template_name = first_template


async def smoke_tool(session: Client, tool: Any, context: SmokeContext) -> ToolOutcome:
    tool_name = getattr(tool, "name", "<unknown>")
    schema = extract_parameters_schema(tool)

    skip_reason = should_skip_tool(tool_name, schema)
    if skip_reason:
        return ToolOutcome(
            tool_name,
            "skipped",
            skip_reason.reason,
            skip_category=skip_reason.category,
        )

    arguments = build_tool_arguments(tool_name, schema, context)
    if arguments is None:
        return ToolOutcome(
            tool_name,
            "skipped",
            "no safe argument strategy",
            None,
            "other",
        )

    try:
        result = await session.call_tool(tool_name, arguments)
    except Exception as exc:
        return ToolOutcome(tool_name, "broken", f"{type(exc).__name__}: {exc}", arguments)

    rendered = render_call_result(result)
    status, detail = classify_call_outcome(result, rendered)
    return ToolOutcome(tool_name, status, detail, arguments)


async def set_smoke_workflow_mode(session: Client, workflow_mode: str) -> None:
    """Switch the fixture project so path-specific facades get a real smoke call."""
    result = await session.call_tool(
        "project_action",
        {"action": "update", "workflow_mode": workflow_mode},
    )
    rendered = render_call_result(result)
    status, detail = classify_call_outcome(result, rendered)
    if status != "ok":
        raise RuntimeError(f"Unable to switch smoke workflow to {workflow_mode}: {detail}")


async def review_smoke_table_asset(session: Client, context: SmokeContext) -> None:
    """Create the integrity receipt required before the table insertion smoke."""
    result = await session.call_tool(
        "review_asset_for_insertion",
        {
            "asset_type": "table",
            "filename": context.sample_csv_name,
            "observations": (
                "Synthetic CSV fixture is readable | Labels and values are internally consistent."
            ),
            "rationale": "Exercise the table content-integrity and insertion gate.",
            "proposed_caption": "Synthetic table used for protocol smoke testing.",
            "visible_watermark_review": "Human-reviewed fixture; no visible watermark observed.",
            "project": context.project_slug,
        },
    )
    rendered = render_call_result(result)
    status, detail = classify_call_outcome(result, rendered)
    if status != "ok":
        raise RuntimeError(f"Unable to review the smoke table fixture: {detail}")


async def run_smoke(
    args: argparse.Namespace, workspace_root: Path
) -> tuple[list[ToolOutcome], dict[str, int]]:
    context = SmokeContext(workspace_root=workspace_root)
    outcomes: list[ToolOutcome] = []

    async with open_mcp_session(workspace_root, args.surface) as session:
        listing = await session.list_tools()
        listed_tools = list(getattr(listing, "tools", listing))
        tools_by_name = {getattr(tool, "name", ""): tool for tool in listed_tools}
        ordered_names = prioritize_tool_names(list(tools_by_name.keys()))

        if args.match:
            ordered_names = [name for name in ordered_names if args.match in name]
        if args.limit > 0:
            ordered_names = ordered_names[: args.limit]

        for name in ordered_names:
            tool = tools_by_name[name]
            try:
                if name in LIBRARY_PATH_TOOLS:
                    await set_smoke_workflow_mode(session, "library-wiki")
                if name == "insert_table":
                    await review_smoke_table_asset(session, context)
                outcome = await smoke_tool(session, tool, context)
            except Exception as exc:
                outcome = ToolOutcome(name, "broken", f"{type(exc).__name__}: {exc}")
            finally:
                if name in LIBRARY_PATH_TOOLS:
                    try:
                        await set_smoke_workflow_mode(session, "manuscript")
                    except Exception as exc:
                        outcome = ToolOutcome(
                            name,
                            "broken",
                            f"Unable to restore manuscript workflow: {type(exc).__name__}: {exc}",
                        )
            outcomes.append(outcome)

            if name == "start_review_round" and outcome.status == "ok":
                prepare_review_fixtures(context)

            if (
                name
                in {
                    "create_project",
                    "convert_exploration_to_project",
                    "switch_project",
                    "project_action",
                }
                and outcome.status == "ok"
            ):
                await refresh_context(session, context)
                prepare_project_fixtures(context)

            if should_stop(args.stop_on, outcome.status):
                break

    return outcomes, summarize_counts(outcomes)


def print_text_report(
    outcomes: list[ToolOutcome], counts: dict[str, int], workspace_root: Path
) -> None:
    print(f"Workspace: {workspace_root}")
    for index, outcome in enumerate(outcomes, start=1):
        status_label = outcome.status
        if outcome.status == "skipped":
            status_label = f"skipped/{outcome.skip_category or 'other'}"
        print(f"[{index:02d}] {outcome.name}: {status_label}")
        if outcome.arguments is not None:
            print(f"  args: {json.dumps(outcome.arguments, ensure_ascii=False, sort_keys=True)}")
        if outcome.detail:
            first_line = outcome.detail.splitlines()[0]
            print(f"  detail: {first_line}")

    print("\nSummary:")
    for key in (
        "total",
        "ok",
        "skipped",
        "skipped_interactive",
        "skipped_external",
        "skipped_other",
        "precondition",
        "error",
        "broken",
    ):
        print(f"  {key}: {counts.get(key, 0)}")


def report_exit_code(stop_on: str, counts: dict[str, int]) -> int:
    """Return non-zero when the selected CI threshold is present in the report."""
    return int(
        any(
            counts.get(status, 0) > 0
            for status in ("broken", "error", "precondition")
            if should_stop(stop_on, status)
        )
    )


def main() -> int:
    args = parse_args()

    if args.workspace is None:
        with tempfile.TemporaryDirectory(prefix="medpaper-greedy-smoke-") as temp_dir:
            workspace_root = Path(temp_dir)
            outcomes, counts = asyncio.run(run_smoke(args, workspace_root))
            if args.json:
                print(
                    json.dumps(
                        build_json_report(outcomes, counts, args, workspace_root, "temporary"),
                        ensure_ascii=True,
                        indent=2,
                    )
                )
            else:
                print_text_report(outcomes, counts, workspace_root)
            return report_exit_code(args.stop_on, counts)

    workspace_root = args.workspace.resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)
    outcomes, counts = asyncio.run(run_smoke(args, workspace_root))
    if args.json:
        print(
            json.dumps(
                build_json_report(outcomes, counts, args, workspace_root, "explicit"),
                ensure_ascii=True,
                indent=2,
            )
        )
    else:
        print_text_report(outcomes, counts, workspace_root)
    return report_exit_code(args.stop_on, counts)


if __name__ == "__main__":
    raise SystemExit(main())
