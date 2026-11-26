#!/usr/bin/env python3
"""Build the portable Agent Plugins package for MedPaper Assistant.

Generates ``plugins/med-paper-assistant/`` (Agent Plugins 1.0.0 layout plus
Claude Code and Google Antigravity compatibility files) and the repository
discovery manifests from the authoritative sources:

* ``pyproject.toml``            -> plugin identity and the mdpaper MCP pin
* ``mcp-integration-lock.json`` -> companion MCP server pins
* ``.claude/skills/<name>/``    -> bundled research skills
* ``.github/agents/*.agent.md`` -> GitHub Copilot & Antigravity subagents

Usage:
    python scripts/build_agent_plugin.py          # (re)generate
    python scripts/build_agent_plugin.py --check  # fail if generated files drift
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAME = "med-paper-assistant"
PLUGIN_REL = Path("plugins") / PLUGIN_NAME
MARKETPLACE_NAME = "medpaper"
SCHEMA_DIR = ROOT / "schemas" / "agent-plugins" / "1.0.0"
PLUGIN_SCHEMA_ID = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA_ID = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
REPOSITORY_URL = "https://github.com/u9401066/med-paper-assistant"
PYTHON_VERSION = "3.12"
MDPAPER_EXTRAS = "provenance,watermark"
COPILOT_NAMESPACE = "com.github.copilot"

# Research skills shipped to end users. Repository-maintenance skills
# (git/readme/changelog/refactor/test/memory-bank) stay development-only.
PLUGIN_SKILLS: tuple[str, ...] = (
    "academic-debate",
    "academic-writing-harness",
    "auto-paper",
    "concept-development",
    "concept-validation",
    "draft-writing",
    "idea-validation",
    "literature-review",
    "manuscript-review",
    "parallel-search",
    "pdf-asset-extractor",
    "pipeline-persistence",
    "project-management",
    "pubmed-export-citations",
    "pubmed-fulltext-access",
    "pubmed-gene-drug-research",
    "pubmed-mcp-tools-reference",
    "pubmed-multi-source-search",
    "pubmed-paper-exploration",
    "pubmed-pico-search",
    "pubmed-quick-search",
    "pubmed-systematic-search",
    "reference-management",
    "submission-preparation",
    "word-export",
)

PLUGIN_AGENTS: tuple[str, ...] = (
    "concept-challenger",
    "domain-reviewer",
    "literature-searcher",
    "meta-learner",
    "methodology-reviewer",
    "paper-reviewer",
    "reference-analyzer",
    "review-orchestrator",
    "statistics-reviewer",
)

# MCP server name in the plugin -> key in mcp-integration-lock.json.
COMPANION_SERVERS: tuple[tuple[str, str], ...] = (
    ("pubmed-search", "pubmed-search"),
    ("asset-aware", "asset-aware"),
    ("cgu", "cgu"),
    ("drawio", "drawio"),
    ("zotero-keeper", "zotero-keeper"),
)

COMPANION_ENV: dict[str, dict[str, str]] = {
    "cgu": {"CGU_PROVIDER": "passthrough"},
}

COPILOT_TO_ANTIGRAVITY_TOOLS: dict[str, tuple[str, ...]] = {
    "readFile": ("read_file",),
    "textSearch": ("read_file",),
    "fileSearch": ("read_file",),
    "listDirectory": ("read_file",),
    "problems": ("read_file",),
    "fetch": ("search_web",),
    "editFiles": ("edit_file", "write_file"),
    "runCommands": ("run_command", "manage_task"),
    "runTasks": ("run_command", "manage_task"),
    "agent": ("invoke_subagent", "send_message", "manage_subagents"),
}

ANTIGRAVITY_ALLOWED_MCP_KEYS = frozenset(
    {"command", "args", "env", "cwd", "url", "headers", "disabled", "variables"}
)

ALLOWED_SKILL_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
SKILL_NAME_RE = re.compile(r"^(?!.*--)[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---", re.S)


def _dump_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _load_project() -> dict[str, Any]:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]


def _load_lock() -> dict[str, Any]:
    text = (ROOT / "mcp-integration-lock.json").read_text(encoding="utf-8")
    return json.loads(text)["integrations"]


def _uvx_server(
    package_source: str, entrypoint: str, env: dict[str, str] | None = None
) -> dict[str, Any]:
    server: dict[str, Any] = {
        "type": "stdio",
        "command": "uvx",
        "args": ["--python", PYTHON_VERSION, "--from", package_source, entrypoint],
    }
    if env:
        server["env"] = env
    return server


def build_mcp_servers(project: dict[str, Any], lock: dict[str, Any]) -> dict[str, Any]:
    """Return Agent Plugins stdio server entries keyed by server name."""
    mdpaper_source = f"{project['name']}[{MDPAPER_EXTRAS}]=={project['version']}"
    servers: dict[str, Any] = {
        "mdpaper": _uvx_server(
            mdpaper_source, project["name"], {"MEDPAPER_TOOL_SURFACE": "compact"}
        ),
    }
    for server_name, lock_key in COMPANION_SERVERS:
        entry = lock[lock_key]
        if entry.get("mcp_sdk_major") != 2:
            raise SystemExit(f"{lock_key}: plugin requires MCP SDK v2 pins")
        servers[server_name] = _uvx_server(
            entry["package_source"], entry["entrypoint"], COMPANION_ENV.get(server_name)
        )
    return servers


def build_antigravity_mcp(servers: dict[str, Any]) -> dict[str, Any]:
    """Return Antigravity-native ``mcp_config.json`` (no ``type`` or ``$schema``)."""
    return {
        "mcpServers": {
            name: {
                key: value for key, value in server.items() if key in ANTIGRAVITY_ALLOWED_MCP_KEYS
            }
            for name, server in servers.items()
        }
    }


def _plugin_rules_markdown(manifest: dict[str, Any]) -> str:
    return f"""# MedPaper Assistant Plugin Rules (v{manifest["version"]})

> Generated by `scripts/build_agent_plugin.py` — always active while the plugin is enabled.

## Workspace Binding (Required First Step)

1. At the start of a research session, call `workspace_state_action(action="get")`.
2. If the response includes a non-empty `workspace.binding_hint` (for example the MCP server started inside `PLUGIN_ROOT` or fell back to `PLUGIN_DATA`), call `workspace_state_action(action="bind", workspace_dir="<absolute path to the user's research folder>")` before creating or editing projects.
3. Never store user projects inside the plugin installation directory.

## Project Context & Dual Workflow

- Before modifying drafts, references, concepts, or exports, confirm the active project with `project_action(action="current")`.
- Respect `project.json.workflow_mode`:
  - `library-wiki`: literature ingestion, atomic notes, knowledge maps, dashboards (`library_action`). Do **not** force manuscript concept-validation or export gates unless the user switches to `manuscript`.
  - `manuscript`: formal research writing (`concept` → `draft` → `review` → `export`) with phase gates and quality hooks.

## Evidence Integrity & Verified References

- Always prefer `save_reference_mcp(pmid)` over `save_reference(article)` so PubMed metadata is retrieved directly via MCP-to-MCP rather than agent transcription.
- Preserve layered trust: `🔒 VERIFIED` (immutable PubMed source) → `🤖 AGENT` (`agent_notes`) → `✏️ USER` (human notes; never overwrite).
- Never translate academic English titles, journal names, author names, medical terminology, or abstracts unless the user explicitly asks.

## Manuscript Quality Gates & Protected Content

- In `manuscript` mode, run `validation_action(action="concept")` before drafting any section.
- Never weaken or remove `🔒 NOVELTY STATEMENT` or `🔒 KEY SELLING POINTS` in `concept.md` or drafts.
- Route manuscript edits through `draft_action`, `run_quality_checks`, and `pipeline_action` rather than bypassing writing hooks with raw file writes.
"""


def _render_antigravity_agent(name: str, source: Path) -> str:
    text = source.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise SystemExit(f"{source.name}: missing YAML frontmatter")
    front = yaml.safe_load(match.group(1)) or {}
    body = text[match.end() :].lstrip("\n")
    description = str(front.get("description") or "").strip()
    if not description:
        raise SystemExit(f"{source.name}: missing description in frontmatter")

    mapped_tools: list[str] = []
    for raw_tool in front.get("tools") or []:
        if not isinstance(raw_tool, str) or raw_tool.endswith("/*"):
            continue
        for native_tool in COPILOT_TO_ANTIGRAVITY_TOOLS.get(raw_tool, ()):
            if native_tool not in mapped_tools:
                mapped_tools.append(native_tool)
    if not mapped_tools:
        mapped_tools = ["read_file"]

    # Emit Prettier-compatible YAML frontmatter (no wrapping, 2-space list indent).
    desc_yaml = (
        json.dumps(description, ensure_ascii=False)
        if any(ch in description for ch in (":", "#", "{", "}", "[", "]", '"', "'"))
        else description
    )
    tool_lines = "\n".join(f"  - {tool}" for tool in mapped_tools)
    header = (
        f"name: {name}\n"
        f"description: {desc_yaml}\n"
        "subagent: true\n"
        "mainAgent: false\n"
        f"tools:\n{tool_lines}"
    )
    return f"---\n{header}\n---\n\n{body.rstrip()}\n"


def build_plugin_manifest(project: dict[str, Any]) -> dict[str, Any]:
    author = project.get("authors", [{}])[0]
    return {
        "$schema": PLUGIN_SCHEMA_ID,
        "name": PLUGIN_NAME,
        "version": project["version"],
        "description": project["description"],
        "author": {"name": author.get("name", "u9401066"), "url": "https://github.com/u9401066"},
        "homepage": REPOSITORY_URL,
        "repository": REPOSITORY_URL,
        "license": project["license"],
        "keywords": sorted(
            {*project.get("keywords", []), "manuscript", "academic-writing", "agent-skills"}
        ),
    }


def build_claude_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    claude = {key: value for key, value in manifest.items() if key != "$schema"}
    claude["mcpServers"] = "./.mcp.json"
    return claude


def build_claude_mcp(servers: dict[str, Any]) -> dict[str, Any]:
    return {
        "mcpServers": {
            name: {key: value for key, value in server.items() if key != "type"}
            for name, server in servers.items()
        }
    }


def build_marketplaces(manifest: dict[str, Any]) -> dict[Path, dict[str, Any]]:
    source = f"./{PLUGIN_REL.as_posix()}"
    claude_style = {
        "name": MARKETPLACE_NAME,
        "owner": {"name": "u9401066", "url": "https://github.com/u9401066"},
        "metadata": {"description": "MedPaper Assistant agent plugins"},
        "plugins": [
            {
                "name": PLUGIN_NAME,
                "source": source,
                "description": manifest["description"],
                "version": manifest["version"],
            }
        ],
    }
    codex_style = {
        "name": MARKETPLACE_NAME,
        "interface": {"displayName": "MedPaper Assistant"},
        "plugins": [
            {
                "name": PLUGIN_NAME,
                "source": {"source": "local", "path": source},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": "Productivity",
            }
        ],
    }
    antigravity_plugins = {
        "entries": [
            {
                "path": "plugins",
            }
        ]
    }
    antigravity_skills = {
        "entries": [
            {
                "path": ".claude/skills",
                "exclude": sorted(PLUGIN_SKILLS),
            }
        ]
    }
    return {
        Path(".claude-plugin") / "marketplace.json": claude_style,
        Path(".agents") / "plugins" / "marketplace.json": codex_style,
        Path(".agents") / "plugins.json": antigravity_plugins,
        Path(".agents") / "skills.json": antigravity_skills,
    }


def validate_skill(skill_dir: Path) -> None:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise SystemExit(f"{skill_dir.name}: SKILL.md is missing YAML frontmatter")
    front = yaml.safe_load(match.group(1)) or {}
    unknown = set(front) - ALLOWED_SKILL_FIELDS
    description = str(front.get("description") or "")
    problems = []
    if front.get("name") != skill_dir.name or not SKILL_NAME_RE.match(skill_dir.name):
        problems.append("name must equal the lowercase-hyphen directory name")
    if not 1 <= len(description) <= 1024:
        problems.append("description must be 1-1024 characters")
    if unknown:
        problems.append(f"unsupported frontmatter fields {sorted(unknown)}")
    if problems:
        raise SystemExit(f"{skill_dir.name}: " + "; ".join(problems))


def _plugin_readme(manifest: dict[str, Any], servers: dict[str, Any]) -> str:
    server_lines = "\n".join(f"- `{name}`" for name in servers)
    skill_lines = "\n".join(f"- `{name}`" for name in PLUGIN_SKILLS)
    return f"""# MedPaper Assistant Agent Plugin

> Generated by `scripts/build_agent_plugin.py` — do not edit by hand.

Portable [Agent Plugins](https://agent-plugins.org/) package (v{manifest["version"]}) for
GitHub Copilot (CLI / VS Code), Claude Code, Codex, and Google Antigravity
(App / IDE / CLI). Requires [`uv`](https://docs.astral.sh/uv/) on `PATH`;
MCP servers are launched with version-pinned `uvx` commands.

## Install

- GitHub Copilot CLI: `copilot plugin marketplace add u9401066/med-paper-assistant`
  then `copilot plugin install {PLUGIN_NAME}@{MARKETPLACE_NAME}`
- Claude Code: `/plugin marketplace add u9401066/med-paper-assistant`
  then `/plugin install {PLUGIN_NAME}@{MARKETPLACE_NAME}`
- Codex: `codex plugin marketplace add u9401066/med-paper-assistant`
- Google Antigravity:
  - **In this repository**: discovered automatically via `.agents/plugins.json` (loads `mcp_config.json`, `rules/AGENTS.md`, `skills/`, and `agents/`).
  - **Global across all research folders**: copy or symlink `plugins/{PLUGIN_NAME}/` to `~/.gemini/config/plugins/{PLUGIN_NAME}/` (or add its parent folder to `~/.gemini/config/plugins.json`).

## Workspace

Projects are stored under `MEDPAPER_BASE_DIR` when set, otherwise the client's
project directory. If the client starts the server inside the plugin folder,
data goes to the client-managed plugin data directory instead.

To point a running server at your research folder, call
`workspace_state_action(action="bind", workspace_dir="/absolute/path")`.
`workspace_state_action(action="get")` reports the active root and its source.

## MCP servers

{server_lines}

## Skills

{skill_lines}
"""


def generate(out_root: Path) -> list[Path]:
    """Write all generated files below ``out_root`` and return relative paths."""
    project = _load_project()
    lock = _load_lock()
    manifest = build_plugin_manifest(project)
    servers = build_mcp_servers(project, lock)
    plugin_dir = out_root / PLUGIN_REL
    files: dict[Path, str] = {
        PLUGIN_REL / "plugin.json": _dump_json(manifest),
        PLUGIN_REL / "mcp.json": _dump_json({"$schema": MCP_SCHEMA_ID, "mcpServers": servers}),
        PLUGIN_REL / "mcp_config.json": _dump_json(build_antigravity_mcp(servers)),
        PLUGIN_REL / ".claude-plugin" / "plugin.json": _dump_json(build_claude_manifest(manifest)),
        PLUGIN_REL / ".mcp.json": _dump_json(build_claude_mcp(servers)),
        PLUGIN_REL / "rules" / "AGENTS.md": _plugin_rules_markdown(manifest),
        PLUGIN_REL / "README.md": _plugin_readme(manifest, servers),
    }
    for rel, data in build_marketplaces(manifest).items():
        files[rel] = _dump_json(data)
    for name in PLUGIN_AGENTS:
        source = ROOT / ".github" / "agents" / f"{name}.agent.md"
        files[PLUGIN_REL / "agents" / f"{name}.md"] = _render_antigravity_agent(name, source)
    for rel, content in files.items():
        target = out_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")

    written = list(files)
    for name in PLUGIN_SKILLS:
        source = ROOT / ".claude" / "skills" / name
        validate_skill(source)
        written.extend(_copy_tree(source, plugin_dir / "skills" / name, out_root))
    agents_dir = plugin_dir / COPILOT_NAMESPACE / "agents"
    for name in PLUGIN_AGENTS:
        source = ROOT / ".github" / "agents" / f"{name}.agent.md"
        written.extend(_copy_tree(source, agents_dir / source.name, out_root))
    return sorted(written)


def _copy_tree(source: Path, target: Path, out_root: Path) -> list[Path]:
    sources = [source] if source.is_file() else sorted(p for p in source.rglob("*") if p.is_file())
    copied = []
    for item in sources:
        dest = target if source.is_file() else target / item.relative_to(source)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(_normalize(item.read_bytes()))
        copied.append(dest.relative_to(out_root))
    return copied


def _normalize(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def validate_schemas(out_root: Path) -> None:
    try:
        import jsonschema
    except ImportError:  # pragma: no cover - jsonschema ships with the mcp SDK
        print("WARNING: jsonschema unavailable; skipped schema validation", file=sys.stderr)
        return
    pairs = (("plugin.schema.json", "plugin.json"), ("mcp.schema.json", "mcp.json"))
    for schema_name, file_name in pairs:
        schema = json.loads((SCHEMA_DIR / schema_name).read_text(encoding="utf-8"))
        document = json.loads((out_root / PLUGIN_REL / file_name).read_text(encoding="utf-8"))
        jsonschema.validate(document, schema)


def _tracked_outputs() -> set[Path]:
    outputs = {p.relative_to(ROOT) for p in (ROOT / PLUGIN_REL).rglob("*") if p.is_file()}
    for rel in build_marketplaces(build_plugin_manifest(_load_project())):
        if (ROOT / rel).is_file():
            outputs.add(rel)
    return outputs


def check() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        expected = set(generate(tmp_root))
        validate_schemas(tmp_root)
        actual = _tracked_outputs()
        drift = sorted(str(p) for p in expected ^ actual)
        for rel in sorted(expected & actual):
            if _normalize((tmp_root / rel).read_bytes()) != _normalize((ROOT / rel).read_bytes()):
                drift.append(str(rel))
    if drift:
        print(
            "ERROR: Agent plugin is out of date; run python scripts/build_agent_plugin.py",
            file=sys.stderr,
        )
        for item in drift:
            print(f"  - {item}", file=sys.stderr)
        return 1
    print(f"OK: Agent plugin up to date ({len(expected)} files)")
    return 0


def build() -> int:
    shutil.rmtree(ROOT / PLUGIN_REL, ignore_errors=True)
    written = generate(ROOT)
    validate_schemas(ROOT)
    print(f"OK: Generated {len(written)} files in {PLUGIN_REL.as_posix()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verify generated files are current")
    args = parser.parse_args(argv)
    return check() if args.check else build()


if __name__ == "__main__":
    raise SystemExit(main())
