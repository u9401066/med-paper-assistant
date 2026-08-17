#!/usr/bin/env python3
"""Enforce the auditable line-count ratchet for legacy Python code-quality debt.

The hard limits come from ``.github/bylaws/ddd-architecture.md``.  Existing
exceptions are recorded at their *current* size, so an exception may shrink or
disappear only after regenerating the authority.  It may never grow, and new
exceptions must be refactored instead of added to the baseline.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = REPO_ROOT / "code-quality-authority.json"
SOURCE_DIRECTORY = Path("src/med_paper_assistant")
SOURCE_SCOPE = "src/med_paper_assistant/**/*.py"
SCHEMA_VERSION = 1
LIMITS = {"file": 400, "class": 300, "function": 50}
MEASUREMENT = {
    "file": "physical source lines (splitlines)",
    "definition": "first decorator or definition through AST end_lineno, inclusive",
    "parser": "Python ast",
}
KIND_ORDER = {"file": 0, "class": 1, "function": 2}


@dataclass(frozen=True)
class Metric:
    """One line-span measurement from the source tree."""

    kind: str
    path: str
    qualified_symbol: str
    lines: int

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.kind, self.path, self.qualified_symbol)

    def as_exception(self) -> dict[str, str | int]:
        return {
            "kind": self.kind,
            "path": self.path,
            "qualifiedSymbol": self.qualified_symbol,
            "allowedLines": self.lines,
        }

    def as_maximum(self) -> dict[str, str | int]:
        return {"path": self.path, "qualifiedSymbol": self.qualified_symbol, "lines": self.lines}


@dataclass(frozen=True)
class ScanResult:
    """Deterministic measurements and parse failures for one source scan."""

    files_scanned: int
    measurements: tuple[Metric, ...]
    parse_errors: tuple[str, ...] = ()

    @property
    def violations(self) -> tuple[Metric, ...]:
        return tuple(metric for metric in self.measurements if metric.lines > LIMITS[metric.kind])


class _DefinitionVisitor(ast.NodeVisitor):
    """Collect qualified class and function spans from an AST."""

    def __init__(self, relative_path: str) -> None:
        self.relative_path = relative_path
        self.metrics: list[Metric] = []
        self._scope: list[str] = []

    @staticmethod
    def _span(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        if node.end_lineno is None:
            raise ValueError(f"AST node {node.name!r} has no end_lineno")
        starts = [node.lineno, *(decorator.lineno for decorator in node.decorator_list)]
        return node.end_lineno - min(starts) + 1

    def _visit_definition(
        self,
        node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
        kind: str,
    ) -> None:
        qualified_symbol = ".".join([*self._scope, node.name])
        self.metrics.append(Metric(kind, self.relative_path, qualified_symbol, self._span(node)))
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802 - ast API
        self._visit_definition(node, "class")

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802 - ast API
        self._visit_definition(node, "function")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._visit_definition(node, "function")


def _metric_sort_key(metric: Metric) -> tuple[str, int, str]:
    return (metric.path, KIND_ORDER[metric.kind], metric.qualified_symbol)


def scan_repository(repo_root: Path = REPO_ROOT) -> ScanResult:
    """Parse and measure only ``src/med_paper_assistant/**/*.py``."""
    source_root = repo_root / SOURCE_DIRECTORY
    if not source_root.is_dir():
        return ScanResult(
            0,
            (),
            parse_errors=(f"source directory is missing: {SOURCE_DIRECTORY.as_posix()}",),
        )
    paths = sorted(path for path in source_root.rglob("*.py") if path.is_file())
    if not paths:
        return ScanResult(
            0,
            (),
            parse_errors=(f"source scope contains no Python files: {SOURCE_SCOPE}",),
        )
    measurements: list[Metric] = []
    parse_errors: list[str] = []

    for path in paths:
        relative_path = path.relative_to(repo_root).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=relative_path)
            visitor = _DefinitionVisitor(relative_path)
            visitor.visit(tree)
        except (OSError, SyntaxError, UnicodeError, ValueError) as exc:
            parse_errors.append(f"{relative_path}: {type(exc).__name__}: {exc}")
            continue

        measurements.append(Metric("file", relative_path, "<module>", len(source.splitlines())))
        measurements.extend(visitor.metrics)

    return ScanResult(
        files_scanned=len(paths),
        measurements=tuple(sorted(measurements, key=_metric_sort_key)),
        parse_errors=tuple(sorted(parse_errors)),
    )


def _maximum_for_kind(scan: ScanResult, kind: str) -> dict[str, str | int] | None:
    candidates = [metric for metric in scan.measurements if metric.kind == kind]
    if not candidates:
        return None
    maximum = min(candidates, key=lambda item: (-item.lines, item.path, item.qualified_symbol))
    return maximum.as_maximum()


def build_authority(scan: ScanResult) -> dict[str, Any]:
    """Build the canonical authority document for a successful scan."""
    if scan.parse_errors:
        joined = "\n".join(scan.parse_errors)
        raise ValueError(f"cannot build authority from an unparseable tree:\n{joined}")

    violations = scan.violations
    counts = {kind: sum(item.kind == kind for item in violations) for kind in KIND_ORDER}
    definition_counts = {
        kind: sum(item.kind == kind for item in scan.measurements) for kind in ("class", "function")
    }
    return {
        "schemaVersion": SCHEMA_VERSION,
        "scope": SOURCE_SCOPE,
        "measurement": MEASUREMENT,
        "limits": LIMITS,
        "summary": {
            "filesScanned": scan.files_scanned,
            "definitionsScanned": definition_counts,
            "violations": {**counts, "total": len(violations)},
            "maximum": {kind: _maximum_for_kind(scan, kind) for kind in KIND_ORDER},
        },
        "exceptions": [item.as_exception() for item in violations],
    }


def render_authority(scan: ScanResult) -> str:
    """Render canonical JSON without timestamps or environment-dependent data."""
    return json.dumps(build_authority(scan), ensure_ascii=False, indent=2) + "\n"


def _load_authority(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        loaded: object = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, [f"authority file is missing: {path}"]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, [f"cannot parse authority {path}: {type(exc).__name__}: {exc}"]
    if not isinstance(loaded, dict):
        return None, ["authority root must be a JSON object"]
    return loaded, []


def _parse_exceptions(authority: dict[str, Any]) -> tuple[list[Metric], list[str]]:
    raw_exceptions = authority.get("exceptions")
    if not isinstance(raw_exceptions, list):
        return [], ["authority exceptions must be a list"]

    parsed: list[Metric] = []
    errors: list[str] = []
    expected_keys = {"kind", "path", "qualifiedSymbol", "allowedLines"}
    for index, raw in enumerate(raw_exceptions):
        if not isinstance(raw, dict):
            errors.append(f"authority exception #{index} must be an object")
            continue
        if set(raw) != expected_keys:
            errors.append(f"authority exception #{index} has non-canonical fields")
            continue
        kind = raw.get("kind")
        path = raw.get("path")
        symbol = raw.get("qualifiedSymbol")
        lines = raw.get("allowedLines")
        if kind not in KIND_ORDER:
            errors.append(f"authority exception #{index} has invalid kind: {kind!r}")
            continue
        if not isinstance(path, str) or not path.startswith(f"{SOURCE_DIRECTORY.as_posix()}/"):
            errors.append(f"authority exception #{index} has an out-of-scope path")
            continue
        if not isinstance(symbol, str) or not symbol:
            errors.append(f"authority exception #{index} has an invalid qualified symbol")
            continue
        if not isinstance(lines, int) or isinstance(lines, bool) or lines <= LIMITS[kind]:
            errors.append(f"authority exception #{index} is not above the {kind} limit")
            continue
        parsed.append(Metric(kind, path, symbol, lines))

    keys = [item.key for item in parsed]
    if len(keys) != len(set(keys)):
        errors.append("authority contains duplicate exceptions")
    canonical = [item.as_exception() for item in sorted(parsed, key=_metric_sort_key)]
    if not errors and raw_exceptions != canonical:
        errors.append("authority exceptions are not in deterministic canonical order")
    return parsed, errors


def _validate_header(authority: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_keys = {"schemaVersion", "scope", "measurement", "limits", "summary", "exceptions"}
    if set(authority) != expected_keys:
        errors.append("authority top-level fields differ from schema version 1")
    if authority.get("schemaVersion") != SCHEMA_VERSION:
        errors.append(
            f"schema version drift: expected {SCHEMA_VERSION}, "
            f"got {authority.get('schemaVersion')!r}"
        )
    if authority.get("scope") != SOURCE_SCOPE:
        errors.append(f"scope drift: expected {SOURCE_SCOPE!r}")
    if authority.get("measurement") != MEASUREMENT:
        errors.append("measurement drift: AST line-count rules must not change")
    if authority.get("limits") != LIMITS:
        errors.append(f"threshold drift: expected {LIMITS}, got {authority.get('limits')!r}")
    return errors


def validate_authority(authority: dict[str, Any], scan: ScanResult) -> list[str]:
    """Return every baseline-ratchet violation without mutating the authority."""
    errors = [f"source parse failure: {item}" for item in scan.parse_errors]
    errors.extend(_validate_header(authority))
    baseline, exception_errors = _parse_exceptions(authority)
    errors.extend(exception_errors)

    baseline_by_key = {item.key: item for item in baseline}
    current_by_key = {item.key: item for item in scan.violations}

    for key, current in current_by_key.items():
        allowed = baseline_by_key.get(key)
        if allowed is None:
            errors.append(
                f"new {current.kind} violation: {current.path}::{current.qualified_symbol} "
                f"is {current.lines} lines (limit {LIMITS[current.kind]})"
            )
        elif current.lines > allowed.lines:
            errors.append(
                f"known {current.kind} violation grew: "
                f"{current.path}::{current.qualified_symbol} is {current.lines} lines, "
                f"authority allows {allowed.lines}"
            )
        elif current.lines < allowed.lines:
            errors.append(
                f"known {current.kind} violation decreased: "
                f"{current.path}::{current.qualified_symbol} is {current.lines} lines, "
                f"authority still allows {allowed.lines}; run --write"
            )

    for key, allowed in baseline_by_key.items():
        if key not in current_by_key:
            errors.append(
                f"resolved/stale {allowed.kind} exception: "
                f"{allowed.path}::{allowed.qualified_symbol}; run --write"
            )

    if not scan.parse_errors:
        expected_summary = build_authority(scan)["summary"]
        if authority.get("summary") != expected_summary:
            errors.append("authority summary is stale; run --write after resolving ratchet errors")
    return errors


def _refresh_blockers(authority: dict[str, Any], scan: ScanResult) -> list[str]:
    """Reject ``--write`` when it would bless added or enlarged debt."""
    errors = _validate_header(authority)
    baseline, exception_errors = _parse_exceptions(authority)
    errors.extend(exception_errors)
    if errors:
        return errors

    baseline_by_key = {item.key: item for item in baseline}
    for current in scan.violations:
        allowed = baseline_by_key.get(current.key)
        if allowed is None:
            errors.append(
                f"refusing --write for new {current.kind} violation: "
                f"{current.path}::{current.qualified_symbol} ({current.lines} lines)"
            )
        elif current.lines > allowed.lines:
            errors.append(
                f"refusing --write because {current.path}::{current.qualified_symbol} "
                f"grew from {allowed.lines} to {current.lines} lines"
            )
    return errors


def _print_summary(scan: ScanResult) -> None:
    authority = build_authority(scan)
    summary = authority["summary"]
    counts = summary["violations"]
    print(
        "Code-quality exceptions: "
        f"file={counts['file']}, class={counts['class']}, "
        f"function={counts['function']}, total={counts['total']}"
    )
    for kind, maximum in summary["maximum"].items():
        if maximum is not None:
            print(
                f"Maximum {kind}: {maximum['lines']} lines — "
                f"{maximum['path']}::{maximum['qualifiedSymbol']}"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write", action="store_true", help="create or deterministically tighten the baseline"
    )
    args = parser.parse_args(argv)

    scan = scan_repository()
    if scan.parse_errors:
        for item in scan.parse_errors:
            print(f"❌ Source parse failure: {item}")
        return 1

    if args.write:
        existing, load_errors = _load_authority(AUTHORITY_PATH)
        if existing is not None:
            blockers = _refresh_blockers(existing, scan)
            if blockers:
                for item in blockers:
                    print(f"❌ {item}")
                return 1
        elif load_errors and AUTHORITY_PATH.exists():
            for item in load_errors:
                print(f"❌ {item}")
            return 1
        AUTHORITY_PATH.write_text(render_authority(scan), encoding="utf-8")
        print(f"✅ Wrote deterministic authority: {AUTHORITY_PATH.relative_to(REPO_ROOT)}")

    authority, load_errors = _load_authority(AUTHORITY_PATH)
    if authority is None:
        for item in load_errors:
            print(f"❌ {item}")
        return 1

    errors = validate_authority(authority, scan)
    if errors:
        for item in errors:
            print(f"❌ {item}")
        return 1

    print(f"✅ Code-quality authority is in sync ({scan.files_scanned} Python files scanned).")
    _print_summary(scan)
    return 0


if __name__ == "__main__":
    sys.exit(main())
