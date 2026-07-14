"""Unit tests for the shared YAML escaper (med_paper_assistant.shared.yaml_escape)."""

from __future__ import annotations

import pytest
import yaml

from med_paper_assistant.shared.yaml_escape import escape_yaml_value


class TestEscapeYamlValue:
    """Backslash-first, then double-quote escaping for double-quoted YAML scalars."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("plain", "plain"),  # no special chars -> passthrough
            ("", ""),  # empty stays empty
            ('say "hi"', 'say \\"hi\\"'),  # quotes escaped
            ("a\\b", "a\\\\b"),  # backslash doubled
            ('a\\"b', 'a\\\\\\"b'),  # backslash escaped BEFORE quote
            ("C:\\path", "C:\\\\path"),
        ],
    )
    def test_escape(self, raw: str, expected: str) -> None:
        assert escape_yaml_value(raw) == expected

    def test_order_is_backslash_then_quote(self) -> None:
        # A lone quote must become \" (one backslash), NOT \\" (which would be a
        # doubled backslash + bare quote). This guards against reversing the order.
        assert escape_yaml_value('"') == '\\"'
        assert escape_yaml_value("\\") == "\\\\"

    @pytest.mark.parametrize(
        "raw",
        [
            "plain title",
            'title with "quotes"',
            "windows\\path\\name",
            'mixed \\ and " together',
            "edge: trailing backslash\\",
            'json-ish {"k": "v\\n"}',
        ],
    )
    def test_round_trips_through_yaml_parser(self, raw: str) -> None:
        # The whole point of the helper: embedding the escaped value inside a
        # double-quoted YAML scalar must parse back to the original string.
        document = f'value: "{escape_yaml_value(raw)}"'
        assert yaml.safe_load(document)["value"] == raw
