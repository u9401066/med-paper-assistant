"""Regression tests for the auditable Python line-count debt ratchet."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import check_code_quality_authority as quality  # noqa: E402


def test_ddd_hard_limits_and_scope_cannot_drift() -> None:
    assert quality.LIMITS == {"file": 400, "class": 300, "function": 50}
    assert quality.SOURCE_SCOPE == "src/med_paper_assistant/**/*.py"


def _function_metric(lines: int, symbol: str = "legacy") -> quality.Metric:
    return quality.Metric(
        kind="function",
        path="src/med_paper_assistant/example.py",
        qualified_symbol=symbol,
        lines=lines,
    )


def _scan(*metrics: quality.Metric) -> quality.ScanResult:
    file_metric = quality.Metric(
        kind="file",
        path="src/med_paper_assistant/example.py",
        qualified_symbol="<module>",
        lines=100,
    )
    return quality.ScanResult(files_scanned=1, measurements=(file_metric, *metrics))


def test_real_code_quality_authority_check_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_code_quality_authority.py")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise AssertionError(result.stdout + "\n" + result.stderr)


@pytest.mark.parametrize(
    "relative_path",
    [
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
        "scripts/release.sh",
    ],
)
def test_code_quality_and_orphan_gates_are_release_wired(relative_path: str) -> None:
    content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")

    assert "python scripts/check_code_quality_authority.py" in content
    assert "vulture src/ --min-confidence 80" in content


def test_ast_scan_measures_files_and_qualified_definitions(tmp_path: Path) -> None:
    package = tmp_path / "src" / "med_paper_assistant"
    package.mkdir(parents=True)
    class_body = [f"    value_{index} = {index}" for index in range(301)]
    class_body.extend(["    def method(self):", "        return None"])
    function_body = [f"    value_{index} = {index}" for index in range(51)]
    source_lines = [
        "class Big:",
        *class_body,
        "",
        "@decorator",
        "def long_function():",
        *function_body,
        *[f"# padding {index}" for index in range(60)],
    ]
    source = "\n".join(source_lines) + "\n"
    (package / "large.py").write_text(source, encoding="utf-8")

    scan = quality.scan_repository(tmp_path)

    assert scan.parse_errors == ()
    metrics = {(item.kind, item.qualified_symbol): item.lines for item in scan.measurements}
    assert metrics[("file", "<module>")] == len(source.splitlines())
    assert metrics[("class", "Big")] == 304
    assert metrics[("function", "Big.method")] == 2
    assert metrics[("function", "long_function")] == 53
    assert {item.kind for item in scan.violations} == {"file", "class", "function"}


def test_check_rejects_growth_new_debt_and_unsynchronised_reductions() -> None:
    baseline_scan = _scan(_function_metric(60))
    authority = quality.build_authority(baseline_scan)

    growth_errors = quality.validate_authority(authority, _scan(_function_metric(61)))
    assert any("known function violation grew" in item for item in growth_errors)

    decrease_errors = quality.validate_authority(authority, _scan(_function_metric(59)))
    assert any("known function violation decreased" in item for item in decrease_errors)

    resolved_errors = quality.validate_authority(authority, _scan(_function_metric(50)))
    assert any("resolved/stale function exception" in item for item in resolved_errors)

    new_metric = quality.Metric(
        kind="class",
        path="src/med_paper_assistant/example.py",
        qualified_symbol="NewDebt",
        lines=301,
    )
    new_errors = quality.validate_authority(
        authority,
        _scan(_function_metric(60), new_metric),
    )
    assert any("new class violation" in item for item in new_errors)


def test_check_rejects_threshold_drift_parse_failures_and_stale_summary() -> None:
    scan = _scan(_function_metric(60))
    authority = quality.build_authority(scan)

    drifted = copy.deepcopy(authority)
    drifted["limits"]["function"] = 60
    assert any("threshold drift" in item for item in quality.validate_authority(drifted, scan))

    stale = copy.deepcopy(authority)
    stale["summary"]["violations"]["total"] = 0
    assert any("summary is stale" in item for item in quality.validate_authority(stale, scan))

    unparseable = quality.ScanResult(
        files_scanned=1,
        measurements=(),
        parse_errors=("src/med_paper_assistant/bad.py: SyntaxError",),
    )
    assert any(
        "source parse failure" in item
        for item in quality.validate_authority(authority, unparseable)
    )


def test_write_is_deterministic_and_cannot_bless_more_debt(tmp_path: Path) -> None:
    baseline_scan = _scan(_function_metric(60))
    authority = quality.build_authority(baseline_scan)
    rendered = quality.render_authority(baseline_scan)

    assert rendered == quality.render_authority(baseline_scan)
    assert json.loads(rendered) == authority
    assert quality._refresh_blockers(authority, _scan(_function_metric(59))) == []
    assert any(
        "grew from 60 to 61" in item
        for item in quality._refresh_blockers(authority, _scan(_function_metric(61)))
    )

    invalid_authority = tmp_path / "authority.json"
    invalid_authority.write_text("{not-json", encoding="utf-8")
    loaded, errors = quality._load_authority(invalid_authority)
    assert loaded is None
    assert any("cannot parse authority" in item for item in errors)
