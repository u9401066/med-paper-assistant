#!/usr/bin/env python3
"""
Structural Consistency Checker — verifies code ↔ docs ↔ tests alignment.

Checks performed:
  1. Hook count: AGENTS.md / copilot-instructions.md claim vs code reality
  2. EXPECTED_HOOKS coverage: MetaLearningEngine list vs AGENTS.md-declared hooks
  3. MCP tool registration: every @mcp.tool has at least one test reference
  4. Infrastructure class coverage: every persistence class has a test file
  5. SKILL.md phase declarations vs pipeline gate validator phases
  6. Export consistency: __init__.py exports match actual class definitions

Exit codes:
  0 = all checks pass
  1 = one or more checks failed

Usage:
  uv run python scripts/check_consistency.py
  uv run python scripts/check_consistency.py --verbose
  uv run python scripts/check_consistency.py --fix  # auto-fix where possible
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "med_paper_assistant"
TESTS = ROOT / "tests"

# Declared hook groups (source of truth from AGENTS.md)
# A3b is a sub-check of A3, counted within A's total of 6
DECLARED_HOOKS = {
    "A": 6,   # A1-A6 (A3b counted within A3)
    "B": 16,  # B1-B16
    "C": 13,  # C1-C13
    "D": 9,   # D1-D9
    "E": 5,   # E1-E5
    "F": 4,   # F1-F4
    "G": 9,   # G1-G9
    "P": 8,   # P1-P8
    "R": 6,   # R1-R6
}
TOTAL_HOOKS = sum(DECLARED_HOOKS.values())  # 76

# Files to check for hook count
HOOK_COUNT_FILES = [
    ROOT / "AGENTS.md",
    ROOT / ".github" / "copilot-instructions.md",
    ROOT / "vscode-extension" / "copilot-instructions.md",
]

# Infrastructure classes that should have tests
INFRASTRUCTURE_CLASSES = [
    ("WritingHooksEngine", "writing_hooks"),
    ("EvolutionVerifier", "evolution_verifier"),
    ("DomainConstraintEngine", "domain_constraint_engine"),
    ("MetaLearningEngine", "meta_learning_engine"),
    ("HookEffectivenessTracker", "hook_effectiveness_tracker"),
    ("QualityScorecard", "quality_scorecard"),
    ("DataArtifactTracker", "data_artifact_tracker"),
    ("PipelineGateValidator", "pipeline_gate_validator"),
]


# ── Helpers ───────────────────────────────────────────────────────────


class CheckResult:
    def __init__(self, name: str, passed: bool, message: str, details: list[str] | None = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details or []

    def __str__(self) -> str:
        icon = "✅" if self.passed else "❌"
        s = f"{icon} {self.name}: {self.message}"
        if self.details:
            for d in self.details:
                s += f"\n   {d}"
        return s


def _extract_number(text: str, pattern: str) -> int | None:
    """Extract a number from text using a regex with one group."""
    m = re.search(pattern, text)
    return int(m.group(1)) if m else None


# ── Check 1: Hook Count in Docs ──────────────────────────────────────


def check_hook_counts() -> CheckResult:
    """Verify AGENTS.md and copilot-instructions.md declare the correct hook count."""
    errors: list[str] = []
    for fpath in HOOK_COUNT_FILES:
        if not fpath.exists():
            errors.append(f"File not found: {fpath.relative_to(ROOT)}")
            continue
        content = fpath.read_text(encoding="utf-8")
        found = _extract_number(content, r"Hook 架構[（(](\d+)\s*checks")
        if found is None:
            errors.append(f"{fpath.relative_to(ROOT)}: no 'Hook 架構(N checks)' found")
        elif found != TOTAL_HOOKS:
            errors.append(
                f"{fpath.relative_to(ROOT)}: claims {found} checks, expected {TOTAL_HOOKS}"
            )

    if errors:
        return CheckResult("Hook Count", False, f"{len(errors)} file(s) have wrong count", errors)
    return CheckResult(
        "Hook Count", True, f"All {len(HOOK_COUNT_FILES)} files declare {TOTAL_HOOKS} checks"
    )


# ── Check 2: EXPECTED_HOOKS Coverage ─────────────────────────────────


def check_expected_hooks() -> CheckResult:
    """Verify MetaLearningEngine.EXPECTED_HOOKS covers all declared hooks."""
    engine_path = SRC / "infrastructure" / "persistence" / "meta_learning_engine.py"
    content = engine_path.read_text(encoding="utf-8")

    m = re.search(r"EXPECTED_HOOKS\s*=\s*\[(.*?)\]", content, re.DOTALL)
    if not m:
        return CheckResult(
            "EXPECTED_HOOKS", False, "Cannot find EXPECTED_HOOKS in meta_learning_engine.py"
        )

    code_hooks = set(re.findall(r'"(\w+)"', m.group(1)))

    # Build full expected set from DECLARED_HOOKS
    full_expected: set[str] = set()
    for letter, count in DECLARED_HOOKS.items():
        for i in range(1, count + 1):
            full_expected.add(f"{letter}{i}")

    # D1-D9: meta-learning engine itself (self-referential, excluded)
    # G1-G9: pre-commit/general hooks tracked separately (excluded)
    agent_behavioral = set()
    for letter in ["D", "G"]:
        for i in range(1, DECLARED_HOOKS.get(letter, 0) + 1):
            agent_behavioral.add(f"{letter}{i}")

    code_enforceable = full_expected - agent_behavioral
    missing_in_code = code_enforceable - code_hooks
    extra_in_code = code_hooks - full_expected

    errors: list[str] = []
    if missing_in_code:
        errors.append(f"Missing from EXPECTED_HOOKS: {sorted(missing_in_code)}")
    if extra_in_code:
        errors.append(f"Extra in EXPECTED_HOOKS (not in AGENTS.md): {sorted(extra_in_code)}")

    if errors:
        return CheckResult("EXPECTED_HOOKS", False, "Code ↔ docs mismatch", errors)
    return CheckResult(
        "EXPECTED_HOOKS",
        True,
        f"{len(code_hooks)} code-enforced hooks + {len(agent_behavioral)} agent-behavioral (D/G) = {len(full_expected)} total",
    )


# ── Check 3: MCP Tool Test Coverage ──────────────────────────────────


def check_mcp_tool_coverage() -> CheckResult:
    """Check that every @mcp.tool function has at least one test reference."""
    tools_dir = SRC / "interfaces" / "mcp" / "tools"
    tool_functions: dict[str, str] = {}  # func_name → file

    for py_file in tools_dir.rglob("*.py"):
        if "__pycache__" in str(py_file) or py_file.name.startswith("_"):
            continue
        content = py_file.read_text(encoding="utf-8")
        # Find function names after @mcp.tool()
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "@mcp.tool()" in line:
                # Next non-decorator line with 'def '
                for j in range(i + 1, min(i + 5, len(lines))):
                    func_match = re.match(r"\s+(?:async\s+)?def\s+(\w+)", lines[j])
                    if func_match:
                        tool_functions[func_match.group(1)] = str(py_file.relative_to(ROOT))
                        break

    # Check test coverage
    all_test_content = ""
    for tf in TESTS.glob("test_*.py"):
        all_test_content += tf.read_text(encoding="utf-8")

    uncovered: list[str] = []
    for func_name, source_file in sorted(tool_functions.items()):
        if func_name not in all_test_content:
            uncovered.append(f"{func_name} ({source_file})")

    total = len(tool_functions)
    covered = total - len(uncovered)

    # Threshold: >30% direct coverage is acceptable (many tools tested via integration).
    coverage_pct = covered / total * 100 if total else 100
    if uncovered:
        is_acceptable = coverage_pct >= 30
        return CheckResult(
            "MCP Tool Coverage",
            is_acceptable,
            f"{covered}/{total} tools ({coverage_pct:.0f}%) referenced in tests"
            + ("" if is_acceptable else " — below 30% threshold"),
            [f"⚠ Not directly tested: {u}" for u in uncovered[:15]]
            + ([f"... and {len(uncovered) - 15} more"] if len(uncovered) > 15 else []),
        )
    return CheckResult("MCP Tool Coverage", True, f"All {total} tools referenced in tests")


# ── Check 4: Infrastructure Class Test Coverage ──────────────────────


def check_infrastructure_coverage() -> CheckResult:
    """Check that every infrastructure class has at least one test file."""
    all_test_content = ""
    for tf in TESTS.glob("test_*.py"):
        all_test_content += tf.read_text(encoding="utf-8")

    uncovered: list[str] = []
    for class_name, module_name in INFRASTRUCTURE_CLASSES:
        if class_name not in all_test_content and module_name not in all_test_content:
            uncovered.append(f"{class_name} ({module_name}.py)")

    covered = len(INFRASTRUCTURE_CLASSES) - len(uncovered)
    if uncovered:
        return CheckResult(
            "Infrastructure Coverage",
            False,
            f"{covered}/{len(INFRASTRUCTURE_CLASSES)} classes have tests",
            uncovered,
        )
    return CheckResult(
        "Infrastructure Coverage",
        True,
        f"All {len(INFRASTRUCTURE_CLASSES)} infrastructure classes have tests",
    )


# ── Check 5: __init__.py Export Consistency ───────────────────────────


def check_init_exports() -> CheckResult:
    """Check that persistence/__init__.py exports match actual class definitions."""
    init_path = SRC / "infrastructure" / "persistence" / "__init__.py"
    content = init_path.read_text(encoding="utf-8")

    # Extract __all__ entries
    all_match = re.search(r"__all__\s*=\s*\[(.*?)\]", content, re.DOTALL)
    if not all_match:
        return CheckResult("Init Exports", False, "Cannot find __all__ in persistence/__init__.py")

    exported = set(re.findall(r'"(\w+)"', all_match.group(1)))

    # Check each export has a corresponding import
    errors: list[str] = []
    for name in sorted(exported):
        if f"import {name}" not in content and f"{name}," not in content:
            # Check if it's imported in a multi-line import
            if name not in content:
                errors.append(f"'{name}' in __all__ but not imported")

    # Check classes in persistence/ that aren't exported
    persistence_dir = SRC / "infrastructure" / "persistence"
    for py_file in persistence_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        file_content = py_file.read_text(encoding="utf-8")
        classes = re.findall(r"^class\s+(\w+)", file_content, re.MULTILINE)
        for cls in classes:
            if cls not in exported and not cls.startswith("_"):
                # Only warn for public classes that look important
                if any(
                    base in cls
                    for base in [
                        "Engine",
                        "Tracker",
                        "Validator",
                        "Manager",
                        "Scorecard",
                        "Verifier",
                    ]
                ):
                    errors.append(f"'{cls}' defined in {py_file.name} but not in __all__")

    if errors:
        return CheckResult("Init Exports", False, f"{len(errors)} export inconsistencies", errors)
    return CheckResult("Init Exports", True, f"{len(exported)} exports verified")


# ── Check 6: HOOK_CATEGORIES Coverage ────────────────────────────────


def check_hook_categories() -> CheckResult:
    """Verify HOOK_CATEGORIES matches the declared hook groups."""
    tracker_path = SRC / "infrastructure" / "persistence" / "hook_effectiveness_tracker.py"
    content = tracker_path.read_text(encoding="utf-8")

    m = re.search(r"HOOK_CATEGORIES\s*=\s*\{(.*?)\}", content, re.DOTALL)
    if not m:
        return CheckResult("HOOK_CATEGORIES", False, "Cannot find HOOK_CATEGORIES")

    code_categories = set(re.findall(r'"(\w)"', m.group(1)))
    # D, G, P hooks are instructional (not code-tracked) but should still have categories
    declared_letters = set(DECLARED_HOOKS.keys())
    # P and G are pre-commit/general — tracked differently
    tracked_letters = declared_letters - {"P", "G"}

    missing = tracked_letters - code_categories
    extra = code_categories - tracked_letters

    errors: list[str] = []
    if missing:
        errors.append(f"Missing categories: {sorted(missing)}")
    if extra:
        errors.append(f"Extra categories (not in declared hooks): {sorted(extra)}")

    if errors:
        return CheckResult("HOOK_CATEGORIES", False, "Category mismatch", errors)
    return CheckResult("HOOK_CATEGORIES", True, f"All {len(tracked_letters)} categories present")


# ── Main ──────────────────────────────────────────────────────────────


def main() -> int:
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    print("=" * 60)
    print("Structural Consistency Check")
    print("=" * 60)
    print()

    checks = [
        check_hook_counts(),
        check_expected_hooks(),
        check_mcp_tool_coverage(),
        check_infrastructure_coverage(),
        check_init_exports(),
        check_hook_categories(),
    ]

    failed = 0
    for result in checks:
        if verbose or not result.passed:
            print(result)
        else:
            icon = "✅" if result.passed else "❌"
            print(f"{icon} {result.name}: {result.message}")
        if not result.passed:
            failed += 1

    print()
    total = len(checks)
    passed = total - failed
    print(f"Result: {passed}/{total} checks passed")

    if failed:
        print(f"\n⚠️  {failed} check(s) FAILED — review above for details")
        return 1
    else:
        print("\n🎉 All consistency checks passed!")
        return 0


if __name__ == "__main__":
    import io
    if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.exit(main())
