from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from pydantic import AnyUrl

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_PROJECTS_RESOURCE = AnyUrl("medpaper://workspace/projects")
TEMPLATE_CATALOG_RESOURCE = AnyUrl("medpaper://templates/catalog")
SKIP_CATEGORY_ORDER = ("interactive", "external", "other")
STABLE_SUMMARY_VERSION = "greedy-smoke-summary-v1"

SAFE_TOOL_ORDER = [
    "create_project",
    "project_action",
    "switch_project",
    "workspace_state_action",
    "get_workspace_state",
    "run_quality_checks",
    "pipeline_action",
    "inspect_export",
    "export_document",
    "list_projects",
]
PRECONDITION_MARKERS = (
    "concept file not found",
    "data file",
    "document session",
    "no manuscript found",
    "not found",
    "project context",
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
async def open_mcp_session(workspace_root: Path) -> AsyncIterator[ClientSession]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    src_path = str(ROOT / "src")
    env["PYTHONPATH"] = src_path if not existing else os.pathsep.join([src_path, existing])
    env["MEDPAPER_BASE_DIR"] = str(workspace_root)

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "med_paper_assistant.interfaces.mcp"],
        cwd=str(workspace_root),
        env=env,
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def prioritize_tool_names(tool_names: list[str]) -> list[str]:
    priority = [name for name in SAFE_TOOL_ORDER if name in tool_names]
    remainder = sorted(name for name in tool_names if name not in SAFE_TOOL_ORDER)
    return priority + remainder


def extract_parameters_schema(tool: Any) -> dict[str, Any]:
    schema = getattr(tool, "parameters", None)
    if isinstance(schema, dict):
        return schema

    for candidate in ("inputSchema", "input_schema", "schema"):
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
    if property_name in {"name", "project_name"}:
        return "Greedy Smoke Project"
    if property_name == "description":
        return "Greedy MCP smoke sandbox"
    if property_name == "paper_type":
        return "other"
    if property_name == "authors_json":
        return "[]"
    if property_name == "memo":
        return "smoke test"
    if property_name == "filename":
        if "concept" in tool_name:
            return context.concept_name
        if any(token in tool_name for token in ("dataset", "plot", "table", "statistical")):
            return context.sample_csv_name
        return context.draft_name
    if property_name == "draft_filename":
        return context.draft_name
    if property_name == "target_text":
        return context.reference_target_text
    if property_name == "journal":
        return "generic"
    if property_name == "query":
        return "smoke test"
    if property_name == "scores":
        return build_score_payload()
    if property_name == "hooks":
        return "all"
    if property_name == "hook_id":
        return "A1"
    if property_name == "event_type":
        return "trigger"
    if property_name == "section":
        return "Introduction"
    if property_name == "sections":
        return "Introduction"
    if property_name == "objective":
        return "Smoke test objective"
    if property_name == "citation_keys":
        return ""
    if property_name == "draft_content":
        return "# Smoke Draft\n\nThis is a smoke-test draft."
    if property_name == "content":
        return "Smoke test content"
    if property_name == "template_name":
        return context.template_name or ""
    if property_name == "output_filename":
        return "smoke-output.docx"
    if property_name == "variables":
        return "group,value"
    if property_name == "test_type":
        return "correlation"
    if property_name == "feedback":
        return "smoke test"
    if property_name == "action":
        tool_actions = {
            "run_quality_checks": "writing_hooks",
            "pipeline_action": "heartbeat",
            "project_action": "current",
            "workspace_state_action": "get",
            "export_document": "session_start",
            "inspect_export": "list_templates",
        }
        return tool_actions.get(tool_name, "approve")
    if property_name == "pmid":
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
    for property_name, property_schema in properties.items():
        if not isinstance(property_schema, dict):
            property_schema = {}

        if property_name in required or property_name in {
            "project",
            "run_novelty_check",
            "structure_only",
            "check_submission",
        }:
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
    structured = getattr(result, "structuredContent", None)
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
    if getattr(result, "isError", False):
        return "broken", rendered_text or "MCP call marked as error"

    lowered = rendered_text.casefold()
    if rendered_text.startswith("❌"):
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
    drafts_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    refs_dir.mkdir(parents=True, exist_ok=True)

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
    (data_dir / context.sample_csv_name).write_text(
        "group,value,age\nA,1,30\nA,2,31\nB,3,29\nB,4,28\n",
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


async def refresh_context(session: ClientSession, context: SmokeContext) -> None:
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


async def smoke_tool(session: ClientSession, tool: Any, context: SmokeContext) -> ToolOutcome:
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


async def run_smoke(
    args: argparse.Namespace, workspace_root: Path
) -> tuple[list[ToolOutcome], dict[str, int]]:
    context = SmokeContext(workspace_root=workspace_root)
    outcomes: list[ToolOutcome] = []

    async with open_mcp_session(workspace_root) as session:
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
            outcome = await smoke_tool(session, tool, context)
            outcomes.append(outcome)

            if name in {"create_project", "switch_project"} and outcome.status == "ok":
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
            return 1 if counts.get("broken", 0) else 0

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
    return 1 if counts.get("broken", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
