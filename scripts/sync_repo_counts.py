#!/usr/bin/env python3
"""
Repo Count Synchroniser — dynamically count metrics and sync into documentation.

Counts:
  - MCP tools (via AST parse of @mcp.tool() decorators)
  - Skills (.claude/skills/* directories)
  - Prompt workflows (.github/prompts/*.prompt.md)
  - Agents (.github/agents/*.agent.md)
  - Pre-commit hooks (.pre-commit-config.yaml  "- id:" lines)
  - Quality hooks (from AGENTS.md Hook 架構 table heading)
  - Pipeline phases (11 — semantic constant)

Modes:
  --check  : CI mode — exit 1 if any doc is stale (default)
  --fix    : Auto-update all documentation files
  --json   : Print counts as JSON and exit
  --verbose: Show details during check

Usage:
  uv run python scripts/sync_repo_counts.py --check
  uv run python scripts/sync_repo_counts.py --fix
  uv run python scripts/sync_repo_counts.py --json
"""

from __future__ import annotations

import ast
import io
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Config ────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "med_paper_assistant"
TOOLS_DIR = SRC / "interfaces" / "mcp" / "tools"

# External MCP counts (not in our codebase — maintained manually)
EXTERNAL_MCP = {
    "pubmed-search": 37,
    "cgu": 13,
}


# ── Data Classes ──────────────────────────────────────────────────────


@dataclass
class RepoCounts:
    """All dynamically counted repo metrics."""

    # mdpaper tool counts per module
    tool_groups: dict[str, int] = field(default_factory=dict)
    mdpaper_total: int = 0

    # External MCP
    pubmed_tools: int = EXTERNAL_MCP["pubmed-search"]
    cgu_tools: int = EXTERNAL_MCP["cgu"]

    # Derived
    total_tools: int = 0

    # Other counts
    skills: int = 0
    prompts: int = 0
    agents: int = 0
    precommit_hooks: int = 0
    quality_hooks: int = 0
    quality_hooks_code_enforced: int = 0
    quality_hooks_agent_driven: int = 0

    # Constants (semantic — don't auto-count)
    phases: int = 11
    mcp_servers: int = 3


# ── Counting Functions ────────────────────────────────────────────────


def count_mcp_tools() -> dict[str, int]:
    """Count @mcp.tool() decorators per group using AST (ignores docstrings)."""
    groups: dict[str, int] = {}
    skip_dirs = {"_shared", "__pycache__"}

    for py_file in sorted(TOOLS_DIR.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue
        if any(sd in py_file.parts for sd in skip_dirs):
            continue

        group = py_file.parent.name
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content)

        count = 0
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    if dec.func.attr == "tool":
                        count += 1

        if count > 0:
            groups[group] = groups.get(group, 0) + count

    return groups


def count_dir_entries(directory: Path, pattern: str = "*") -> int:
    """Count matching entries in a directory."""
    if not directory.exists():
        return 0
    return len(list(directory.glob(pattern)))


def count_skill_dirs() -> int:
    """Count skill directories under .claude/skills/."""
    skills_dir = ROOT / ".claude" / "skills"
    if not skills_dir.exists():
        return 0
    return len([d for d in skills_dir.iterdir() if d.is_dir()])


def count_precommit_hooks() -> int:
    """Count '- id:' entries in .pre-commit-config.yaml."""
    config = ROOT / ".pre-commit-config.yaml"
    if not config.exists():
        return 0
    content = config.read_text(encoding="utf-8")
    return len(re.findall(r"^\s+- id:", content, re.MULTILINE))


def parse_hook_counts_from_agents() -> tuple[int, int, int]:
    """Parse hook counts from AGENTS.md heading pattern.

    Returns (total, code_enforced, agent_driven).
    """
    agents_md = ROOT / "AGENTS.md"
    if not agents_md.exists():
        return 0, 0, 0
    content = agents_md.read_text(encoding="utf-8")
    m = re.search(
        r"Hook 架構[（(](\d+)\s*checks\s*[—–-]+\s*(\d+)\s*Code-Enforced\s*/\s*(\d+)\s*Agent-Driven[）)]",
        content,
    )
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return 0, 0, 0


def gather_counts() -> RepoCounts:
    """Gather all counts from the repo."""
    counts = RepoCounts()

    # MCP tools
    counts.tool_groups = count_mcp_tools()
    counts.mdpaper_total = sum(counts.tool_groups.values())
    counts.total_tools = counts.mdpaper_total + counts.pubmed_tools + counts.cgu_tools

    # Skills, Prompts, Agents
    counts.skills = count_skill_dirs()
    counts.prompts = count_dir_entries(ROOT / ".github" / "prompts", "*.prompt.md")
    counts.agents = count_dir_entries(ROOT / ".github" / "agents", "*.agent.md")

    # Pre-commit hooks
    counts.precommit_hooks = count_precommit_hooks()

    # Quality hooks (from AGENTS.md — single source of truth)
    total, ce, ad = parse_hook_counts_from_agents()
    counts.quality_hooks = total
    counts.quality_hooks_code_enforced = ce
    counts.quality_hooks_agent_driven = ad

    return counts


# ── Document Replacement Rules ────────────────────────────────────────


@dataclass
class ReplaceRule:
    """A pattern to find and replace in documentation."""

    file: Path
    pattern: str  # regex with group(s) to match the number
    replacement: str  # format string using counts
    description: str


def build_replace_rules(c: RepoCounts) -> list[ReplaceRule]:
    """Build all replacement rules from current counts."""
    rules: list[ReplaceRule] = []

    # ── README.md and README.zh-TW.md ──

    for readme in [ROOT / "README.md", ROOT / "README.zh-TW.md"]:
        is_zh = "zh-TW" in readme.name

        # Tagline: "3 MCP Servers · ~131 Tools · 26 Skills · 14 Prompt Workflows"
        if is_zh:
            rules.append(ReplaceRule(
                readme,
                r"(\d+)\s*個\s*MCP\s*Server\s*·\s*~?(\d+)\s*個工具\s*·\s*(\d+)\s*個技能\s*·\s*(\d+)\s*個\s*Prompt\s*工作流",
                f"{c.mcp_servers} 個 MCP Server · ~{c.total_tools} 個工具 · {c.skills} 個技能 · {c.prompts} 個 Prompt 工作流",
                "zh tagline counts",
            ))
        else:
            rules.append(ReplaceRule(
                readme,
                r"(\d+)\s*MCP\s*Servers?\s*·\s*~?(\d+)\s*Tools?\s*·\s*(\d+)\s*Skills?\s*·\s*(\d+)\s*Prompt\s*Workflows?",
                f"{c.mcp_servers} MCP Servers · ~{c.total_tools} Tools · {c.skills} Skills · {c.prompts} Prompt Workflows",
                "en tagline counts",
            ))

        # Quality hooks line: "42 Quality Hooks" / "42 項品質檢查"
        if is_zh:
            rules.append(ReplaceRule(
                readme,
                r"(\d+)\s*項品質檢查",
                f"{c.quality_hooks} 項品質檢查",
                "zh quality hook count",
            ))
        else:
            rules.append(ReplaceRule(
                readme,
                r"(\d+)\s*Quality\s*Hooks?",
                f"{c.quality_hooks} Quality Hooks",
                "en quality hook count",
            ))

        # Mermaid MCP subgraph: "MCP Servers (~131 tools)" / "MCP Server（~131 工具）"
        if is_zh:
            rules.append(ReplaceRule(
                readme,
                r'MCP\s*Server[（(]~?\d+\s*工具[）)]',
                f'MCP Server（~{c.total_tools} 工具）',
                "zh mermaid MCP subgraph label",
            ))
        else:
            rules.append(ReplaceRule(
                readme,
                r'MCP\s*Servers?\s*\(~?\d+\s*tools?\)',
                f'MCP Servers (~{c.total_tools} tools)',
                "en mermaid MCP subgraph label",
            ))

        # mdpaper node in mermaid: 'mdpaper["mdpaper<br/>81 tools<br/>'
        if is_zh:
            rules.append(ReplaceRule(
                readme,
                r'mdpaper\["mdpaper<br/>\d+\s*工具',
                f'mdpaper["mdpaper<br/>{c.mdpaper_total} 工具',
                "zh mermaid mdpaper node",
            ))
        else:
            rules.append(ReplaceRule(
                readme,
                r'mdpaper\["mdpaper<br/>\d+\s*tools',
                f'mdpaper["mdpaper<br/>{c.mdpaper_total} tools',
                "en mermaid mdpaper node",
            ))

        # pubmed node in mermaid
        if is_zh:
            rules.append(ReplaceRule(
                readme,
                r'pubmed\["pubmed-search<br/>\d+\s*工具',
                f'pubmed["pubmed-search<br/>{c.pubmed_tools} 工具',
                "zh mermaid pubmed node",
            ))
        else:
            rules.append(ReplaceRule(
                readme,
                r'pubmed\["pubmed-search<br/>\d+\s*tools',
                f'pubmed["pubmed-search<br/>{c.pubmed_tools} tools',
                "en mermaid pubmed node",
            ))

        # CGU node in mermaid
        if is_zh:
            rules.append(ReplaceRule(
                readme,
                r'cgu\["CGU<br/>\d+\s*工具',
                f'cgu["CGU<br/>{c.cgu_tools} 工具',
                "zh mermaid CGU node",
            ))
        else:
            rules.append(ReplaceRule(
                readme,
                r'cgu\["CGU<br/>\d+\s*tools',
                f'cgu["CGU<br/>{c.cgu_tools} tools',
                "en mermaid CGU node",
            ))

        # ASCII art box: "│  81 tools" / "│  81 工具" for mdpaper
        word = "工具" if is_zh else "tools"
        rules.append(ReplaceRule(
            readme,
            rf"(│\s*📝\s*mdpaper\s*│.*\n│)\s*\d+\s*{word}",
            rf"\g<1>  {c.mdpaper_total} {word}",
            f"{'zh' if is_zh else 'en'} ASCII mdpaper tools",
        ))

        # "All-in-one: ~131 tools in VS Code" / "一站式：~131 個工具在 VS Code 裡"
        if is_zh:
            rules.append(ReplaceRule(
                readme,
                r"一站式[：:]\s*~?\d+\s*個工具",
                f"一站式：~{c.total_tools} 個工具",
                "zh all-in-one",
            ))
        else:
            rules.append(ReplaceRule(
                readme,
                r"All-in-one:\s*~?\d+\s*tools",
                f"All-in-one: ~{c.total_tools} tools",
                "en all-in-one",
            ))

        # "26 Skills + 14 Prompt Workflows" / "26 技能 + 14 Prompt 工作流"
        if is_zh:
            rules.append(ReplaceRule(
                readme,
                r"\d+\s*技能\s*\+\s*\d+\s*Prompt\s*工作流",
                f"{c.skills} 技能 + {c.prompts} Prompt 工作流",
                "zh skills + prompts",
            ))
        else:
            rules.append(ReplaceRule(
                readme,
                r"\d+\s*Skills?\s*\+\s*\d+\s*Prompt\s*Workflows?",
                f"{c.skills} Skills + {c.prompts} Prompt Workflows",
                "en skills + prompts",
            ))

        # "26 Skills · 14 Prompts" in mermaid
        if is_zh:
            rules.append(ReplaceRule(
                readme,
                r"\d+\s*技能\s*·\s*\d+\s*Prompts?",
                f"{c.skills} 技能 · {c.prompts} Prompts",
                "zh mermaid skills prompts",
            ))
        else:
            rules.append(ReplaceRule(
                readme,
                r"\d+\s*Skills?\s*·\s*\d+\s*Prompts?",
                f"{c.skills} Skills · {c.prompts} Prompts",
                "en mermaid skills prompts",
            ))

        # "**26 Skills** covering" for README.md only
        if not is_zh:
            rules.append(ReplaceRule(
                readme,
                r"\*\*\d+\s*Skills?\*\*\s*covering",
                f"**{c.skills} Skills** covering",
                "en bold skills covering",
            ))

        # mdpaper per-section headings: "### 📁 Project Management (16 tools)"
        section_map = {
            "project": ("Project Management", "專案管理"),
            "reference": ("Reference Management", "參考文獻管理"),
            "draft": ("Draft & Editing", "草稿與編輯"),
            "validation": ("Validation", "驗證"),
            "analysis": ("Data Analysis", "資料分析"),
            "review": ("Review & Audit", "審查與審計"),
            "export": ("Export & Submission", "匯出與投稿"),
        }
        for group_key, (en_name, zh_name) in section_map.items():
            group_count = c.tool_groups.get(group_key, 0)
            if is_zh:
                rules.append(ReplaceRule(
                    readme,
                    rf"###\s*\S+\s*{re.escape(zh_name)}[（(]\d+\s*工具[）)]",
                    f"### {_section_emoji(group_key)} {zh_name}（{group_count} 工具）",
                    f"zh {group_key} section heading",
                ))
            else:
                rules.append(ReplaceRule(
                    readme,
                    rf"###\s*\S+\s*{re.escape(en_name)}\s*\(\d+\s*tools?\)",
                    f"### {_section_emoji(group_key)} {en_name} ({group_count} tools)",
                    f"en {group_key} section heading",
                ))

        # Summary table: "mdpaper (81) + pubmed-search (37) + CGU (13)"
        rules.append(ReplaceRule(
            readme,
            r"mdpaper\s*\(\d+\)\s*\+\s*pubmed-search\s*\(\d+\)\s*\+\s*CGU\s*\(\d+\)",
            f"mdpaper ({c.mdpaper_total}) + pubmed-search ({c.pubmed_tools}) + CGU ({c.cgu_tools})",
            f"{'zh' if is_zh else 'en'} MCP summary table",
        ))

        # "3 MCP Servers |" / "3 個 MCP Server |"
        if is_zh:
            rules.append(ReplaceRule(
                readme,
                r"\*\*\d+\s*個\s*MCP\s*Server\*\*",
                f"**{c.mcp_servers} 個 MCP Server**",
                "zh bold MCP server count",
            ))
        else:
            rules.append(ReplaceRule(
                readme,
                r"\*\*\d+\s*MCP\s*Servers?\*\*",
                f"**{c.mcp_servers} MCP Servers**",
                "en bold MCP server count",
            ))

        # Pre-commit hooks count
        if is_zh:
            rules.append(ReplaceRule(
                readme,
                r"\*\*\d+\s*個\s*pre-commit\s*hooks?\*\*",
                f"**{c.precommit_hooks} 個 pre-commit hooks**",
                "zh pre-commit count",
            ))
        else:
            rules.append(ReplaceRule(
                readme,
                r"\*\*\d+\s*pre-commit\s*hooks?\*\*",
                f"**{c.precommit_hooks} pre-commit hooks**",
                "en pre-commit count",
            ))

        # Pre-commit in table: "15 hooks"
        if is_zh:
            rules.append(ReplaceRule(
                readme,
                r"\d+\s*hooks?[（(]ruff",
                f"{c.precommit_hooks} hooks（ruff",
                "zh pre-commit hooks table",
            ))
        else:
            rules.append(ReplaceRule(
                readme,
                r"\d+\s*hooks?\s*\(ruff",
                f"{c.precommit_hooks} hooks (ruff",
                "en pre-commit hooks table",
            ))

        # Tree view: "MCP server, 81 tools in 8 groups"
        if is_zh:
            rules.append(ReplaceRule(
                readme,
                r"MCP\s*Server[，,]\s*\d+\s*工具分\s*\d+\s*大類",
                f"MCP Server，{c.mdpaper_total} 工具分 {len(c.tool_groups)} 大類",
                "zh tree view tools",
            ))
        else:
            rules.append(ReplaceRule(
                readme,
                r"MCP\s*server,\s*\d+\s*tools\s*in\s*\d+\s*groups?",
                f"MCP server, {c.mdpaper_total} tools in {len(c.tool_groups)} groups",
                "en tree view tools",
            ))

        # Tree view: pubmed-search and CGU lines
        if is_zh:
            rules.append(ReplaceRule(
                readme,
                r"PubMed/PMC/CORE\s*搜尋[（(]\d+\s*工具[）)]",
                f"PubMed/PMC/CORE 搜尋（{c.pubmed_tools} 工具）",
                "zh tree pubmed",
            ))
            rules.append(ReplaceRule(
                readme,
                r"創意發想[（(]\d+\s*工具[）)]",
                f"創意發想（{c.cgu_tools} 工具）",
                "zh tree CGU",
            ))
        else:
            rules.append(ReplaceRule(
                readme,
                r"PubMed/PMC/CORE\s*search\s*\(\d+\s*tools?\)",
                f"PubMed/PMC/CORE search ({c.pubmed_tools} tools)",
                "en tree pubmed",
            ))
            rules.append(ReplaceRule(
                readme,
                r"Creative\s*generation\s*\(\d+\s*tools?\)",
                f"Creative generation ({c.cgu_tools} tools)",
                "en tree CGU",
            ))

        # Table row counts: "| 81 |" for mdpaper, "| 14 |" for Prompts, "| 26 |" for Skills
        # mdpaper row: match "Core MCP Server" or "核心 MCP Server" context
        rules.append(ReplaceRule(
            readme,
            rf"((?:Core|核心)\s*MCP\s*Server\s*\|\s*)\d+",
            rf"\g<1>{c.mdpaper_total}",
            f"{'zh' if is_zh else 'en'} table mdpaper tools",
        ))
        # Prompts row: "Prompt Files" context
        rules.append(ReplaceRule(
            readme,
            r"(Prompt\s*Files?\s*\|\s*)\d+",
            rf"\g<1>{c.prompts}",
            f"{'zh' if is_zh else 'en'} table prompts count",
        ))

        # Prompt tree: "14 Prompt workflow files" / "14 個 Prompt 工作流"
        if is_zh:
            rules.append(ReplaceRule(
                readme,
                r"\d+\s*個\s*Prompt\s*工作流",
                f"{c.prompts} 個 Prompt 工作流",
                "zh prompt tree",
            ))
        else:
            rules.append(ReplaceRule(
                readme,
                r"\d+\s*Prompt\s*workflow\s*files?",
                f"{c.prompts} Prompt workflow files",
                "en prompt tree",
            ))

    # ── ARCHITECTURE.md ──

    arch = ROOT / "ARCHITECTURE.md"
    if arch.exists():
        rules.append(ReplaceRule(
            arch,
            r"提供\s*\d+\s*個\s*tools",
            f"提供 {c.mdpaper_total} 個 tools",
            "ARCHITECTURE mdpaper tool count",
        ))
        rules.append(ReplaceRule(
            arch,
            r"Hook 架構[（(]\d+\s*checks\s*[—–-]+\s*\d+\s*Code-Enforced\s*/\s*\d+\s*Agent-Driven[）)]",
            f"Hook 架構（{c.quality_hooks} checks — {c.quality_hooks_code_enforced} Code-Enforced / {c.quality_hooks_agent_driven} Agent-Driven）",
            "ARCHITECTURE hook heading",
        ))
        rules.append(ReplaceRule(
            arch,
            r"追蹤\s*\d+\s*個\s*Hook",
            f"追蹤 {c.quality_hooks} 個 Hook",
            "ARCHITECTURE hook tracking count",
        ))
        rules.append(ReplaceRule(
            arch,
            r"Copilot\s*Skills[（(]\d+\s*個[）)]",
            f"Copilot Skills（{c.skills} 個）",
            "ARCHITECTURE skills count",
        ))
        rules.append(ReplaceRule(
            arch,
            r"Copilot\s*Prompts[（(]\d+\s*個[）)]",
            f"Copilot Prompts（{c.prompts} 個）",
            "ARCHITECTURE prompts count",
        ))

    # ── copilot-instructions.md (both .github/ and vscode-extension/) ──

    for ci_path in [
        ROOT / ".github" / "copilot-instructions.md",
        ROOT / "vscode-extension" / "copilot-instructions.md",
    ]:
        if not ci_path.exists():
            continue

        # Header: "## MCP Server（89 tools, ..."
        rules.append(ReplaceRule(
            ci_path,
            r"MCP\s*Server[（(]\d+\s*tools",
            f"MCP Server（{c.mdpaper_total} tools",
            f"copilot-instructions MCP header ({ci_path.parent.name})",
        ))

        # Hook heading
        rules.append(ReplaceRule(
            ci_path,
            r"Hook 架構[（(]\d+\s*checks\s*[—–-]+\s*\d+\s*Code-Enforced\s*/\s*\d+\s*Agent-Driven[）)]",
            f"Hook 架構（{c.quality_hooks} checks — {c.quality_hooks_code_enforced} Code-Enforced / {c.quality_hooks_agent_driven} Agent-Driven）",
            f"copilot-instructions hook heading ({ci_path.parent.name})",
        ))

        # Module breakdown table rows: match "| group/ " then capture spaces and "| N"
        for group_key in ["project", "reference", "draft", "validation", "analysis", "review", "export"]:
            group_count = c.tool_groups.get(group_key, 0)
            rules.append(ReplaceRule(
                ci_path,
                rf"(\|\s*{group_key}/\s*\|\s*)\d+",
                rf"\g<1>{group_count}",
                f"copilot-instructions {group_key} count ({ci_path.parent.name})",
            ))

    # ── ROADMAP.md ──

    roadmap = ROOT / "ROADMAP.md"
    if roadmap.exists():
        rules.append(ReplaceRule(
            roadmap,
            r"\d+\s*個品質檢查",
            f"{c.quality_hooks} 個品質檢查",
            "ROADMAP quality check count",
        ))

    # ── CONSTITUTION.md ──

    constitution = ROOT / "CONSTITUTION.md"
    if constitution.exists():
        rules.append(ReplaceRule(
            constitution,
            r"\d+\s*個品質檢查",
            f"{c.quality_hooks} 個品質檢查",
            "CONSTITUTION quality check count",
        ))
        rules.append(ReplaceRule(
            constitution,
            r"\d+/\d+\s*Code-Enforced",
            f"{c.quality_hooks_code_enforced}/{c.quality_hooks} Code-Enforced",
            "CONSTITUTION code-enforced ratio",
        ))

    # ── AGENTS.md ──

    agents_md = ROOT / "AGENTS.md"
    if agents_md.exists():
        # L1 hooks line
        rules.append(ReplaceRule(
            agents_md,
            r"\d+\s*個品質檢查[（(]\d+\s*Code-Enforced\s*/\s*\d+\s*Agent-Driven[）)]",
            f"{c.quality_hooks} 個品質檢查（{c.quality_hooks_code_enforced} Code-Enforced / {c.quality_hooks_agent_driven} Agent-Driven）",
            "AGENTS.md L1 hooks detail",
        ))
        # Hook heading (already in co-pilot instructions rules but AGENTS.md is separate)
        rules.append(ReplaceRule(
            agents_md,
            r"Hook 架構[（(]\d+\s*checks\s*[—–-]+\s*\d+\s*Code-Enforced\s*/\s*\d+\s*Agent-Driven[）)]",
            f"Hook 架構（{c.quality_hooks} checks — {c.quality_hooks_code_enforced} Code-Enforced / {c.quality_hooks_agent_driven} Agent-Driven）",
            "AGENTS.md hook heading",
        ))

    # ── docs/auto-paper-guide.md ──
    # NOTE: auto-paper-guide.md uses "42 項自動品質檢查（Hook A-D）"
    # which is the Agent-Driven subset (42), NOT total hooks (76).
    # This is intentional — do NOT auto-replace.

    return rules


def _section_emoji(group: str) -> str:
    """Return the emoji for a tool group section."""
    return {
        "project": "📁",
        "reference": "📚",
        "draft": "✍️",
        "validation": "✅",
        "analysis": "📊",
        "review": "🔍",
        "export": "📄",
    }.get(group, "📦")


# ── Apply / Check ────────────────────────────────────────────────────


def apply_rules(rules: list[ReplaceRule], *, fix: bool, verbose: bool) -> list[str]:
    """Apply all replacement rules. Returns list of issues found."""
    issues: list[str] = []
    files_modified: set[Path] = set()

    # Group rules by file for efficiency
    by_file: dict[Path, list[ReplaceRule]] = {}
    for rule in rules:
        by_file.setdefault(rule.file, []).append(rule)

    for fpath, file_rules in by_file.items():
        if not fpath.exists():
            issues.append(f"⚠️  File not found: {fpath.relative_to(ROOT)}")
            continue

        content = fpath.read_text(encoding="utf-8")
        new_content = content

        for rule in file_rules:
            matches = list(re.finditer(rule.pattern, new_content))
            if not matches:
                if verbose:
                    print(f"  ℹ️  No match for [{rule.description}] in {fpath.relative_to(ROOT)}")
                continue

            for match in matches:
                old_text = match.group(0)
                # Build replacement (handle backrefs)
                new_text = re.sub(rule.pattern, rule.replacement, old_text)
                if old_text != new_text:
                    issues.append(
                        f"{'🔧' if fix else '❌'} {fpath.relative_to(ROOT)}: "
                        f"[{rule.description}] {old_text!r} → {new_text!r}"
                    )
                    if fix:
                        new_content = new_content.replace(old_text, new_text, 1)
                        files_modified.add(fpath)

        if fix and fpath in files_modified:
            fpath.write_text(new_content, encoding="utf-8")

    if fix and files_modified:
        print(f"\n✅ Updated {len(files_modified)} file(s):")
        for f in sorted(files_modified):
            print(f"   {f.relative_to(ROOT)}")

    return issues


# ── Main ──────────────────────────────────────────────────────────────


def main() -> int:
    # Ensure UTF-8 output on Windows
    if os.name == "nt":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    args = sys.argv[1:]
    fix_mode = "--fix" in args
    json_mode = "--json" in args
    verbose = "--verbose" in args or "-v" in args

    counts = gather_counts()

    if json_mode:
        data = {
            "mdpaper_tools": {
                "total": counts.mdpaper_total,
                "groups": counts.tool_groups,
            },
            "external_mcp": {
                "pubmed-search": counts.pubmed_tools,
                "cgu": counts.cgu_tools,
            },
            "total_tools": counts.total_tools,
            "skills": counts.skills,
            "prompts": counts.prompts,
            "agents": counts.agents,
            "precommit_hooks": counts.precommit_hooks,
            "quality_hooks": {
                "total": counts.quality_hooks,
                "code_enforced": counts.quality_hooks_code_enforced,
                "agent_driven": counts.quality_hooks_agent_driven,
            },
            "mcp_servers": counts.mcp_servers,
            "phases": counts.phases,
        }
        print(json.dumps(data, indent=2))
        return 0

    # Print summary
    print("📊 Repository Counts (dynamic)")
    print("=" * 50)
    print(f"  MCP Tools (mdpaper) : {counts.mdpaper_total}")
    for g in sorted(counts.tool_groups):
        print(f"    {g + '/':<14s}: {counts.tool_groups[g]}")
    print(f"  pubmed-search       : {counts.pubmed_tools} (external)")
    print(f"  CGU                 : {counts.cgu_tools} (external)")
    print(f"  Total tools         : ~{counts.total_tools}")
    print(f"  Skills              : {counts.skills}")
    print(f"  Prompts             : {counts.prompts}")
    print(f"  Agents              : {counts.agents}")
    print(f"  Pre-commit hooks    : {counts.precommit_hooks}")
    print(f"  Quality hooks       : {counts.quality_hooks} ({counts.quality_hooks_code_enforced} CE / {counts.quality_hooks_agent_driven} AD)")
    print(f"  Pipeline phases     : {counts.phases}")
    print()

    rules = build_replace_rules(counts)

    if fix_mode:
        print("🔧 Fix mode — updating documentation...")
        issues = apply_rules(rules, fix=True, verbose=verbose)
    else:
        print("🔍 Check mode — scanning for stale counts...")
        issues = apply_rules(rules, fix=False, verbose=verbose)

    stale = [i for i in issues if i.startswith("❌")]
    fixed = [i for i in issues if i.startswith("🔧")]
    warnings = [i for i in issues if i.startswith("⚠️")]

    if verbose or stale or fixed:
        print()
        for issue in issues:
            print(f"  {issue}")

    if fix_mode:
        if fixed:
            print(f"\n🔧 Fixed {len(fixed)} stale count(s).")
        else:
            print("\n✅ All counts already up to date.")
        return 0
    else:
        if stale:
            print(f"\n❌ {len(stale)} stale count(s) found. Run with --fix to update.")
            return 1
        else:
            print("\n✅ All documentation counts are in sync.")
            return 0


if __name__ == "__main__":
    sys.exit(main())
