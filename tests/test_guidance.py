"""Tests for ProactiveGuidanceEngine (build_guidance_hint)."""

from med_paper_assistant.interfaces.mcp.tools._shared.guidance import build_guidance_hint


def test_no_hints_returns_original() -> None:
    """No hints → result unchanged."""
    result = build_guidance_hint("some output")
    assert result == "some output"


def test_empty_result_passthrough() -> None:
    """Empty string returns unchanged."""
    assert build_guidance_hint("") == ""


def test_next_tool_appended() -> None:
    result = build_guidance_hint("output", next_tool="run_writing_hooks")
    assert result.startswith("output")
    assert "\nGUIDANCE:" in result
    assert "next→run_writing_hooks" in result


def test_warnings_appended() -> None:
    result = build_guidance_hint("out", warnings=["novelty below 75"])
    assert "warn: novelty below 75" in result


def test_multiple_warnings() -> None:
    result = build_guidance_hint("r", warnings=["warn1", "warn2"])
    assert "warn: warn1" in result
    assert "warn: warn2" in result


def test_context_hints_appended() -> None:
    result = build_guidance_hint("r", context_hints=["3 suggestions require confirmation"])
    assert "3 suggestions require confirmation" in result


def test_full_guidance_format() -> None:
    result = build_guidance_hint(
        "Draft saved.",
        next_tool="run_writing_hooks",
        warnings=["novelty 68/100"],
        context_hints=["3 hooks available"],
    )
    assert result.startswith("Draft saved.")
    assert "\nGUIDANCE: " in result
    assert "next→run_writing_hooks" in result
    assert "warn: novelty 68/100" in result
    assert "3 hooks available" in result
    # All parts delimited by " | "
    guidance_line = result.split("\nGUIDANCE: ")[1]
    parts = guidance_line.split(" | ")
    assert len(parts) == 3


def test_guidance_appended_on_single_newline() -> None:
    """Guidance is always on a new line, separated from main output."""
    result = build_guidance_hint("output", next_tool="validate_concept")
    lines = result.split("\n")
    assert lines[-1].startswith("GUIDANCE:")


def test_only_warnings_no_next_tool() -> None:
    result = build_guidance_hint("result", warnings=["low word count"])
    assert "GUIDANCE:" in result
    assert "next→" not in result
    assert "warn: low word count" in result


def test_none_warnings_ignored() -> None:
    result = build_guidance_hint("r", next_tool="some_tool", warnings=None)
    assert "warn:" not in result
    assert "next→some_tool" in result


def test_empty_warnings_list_ignored() -> None:
    """Empty list should not add warnings section."""
    result = build_guidance_hint("r", warnings=[])
    assert result == "r"


def test_empty_context_hints_ignored() -> None:
    result = build_guidance_hint("r", context_hints=[])
    assert result == "r"


def test_all_none_no_guidance() -> None:
    result = build_guidance_hint("r", next_tool=None, warnings=None, context_hints=None)
    assert result == "r"
