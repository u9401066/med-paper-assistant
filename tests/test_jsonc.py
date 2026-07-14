from __future__ import annotations

import json

import pytest

from med_paper_assistant.shared.jsonc import loads_jsonc


def test_loads_jsonc_preserves_url_and_comment_markers_inside_strings() -> None:
    parsed = loads_jsonc(
        r"""
        {
          // endpoint used by the local model
          "url": "http://localhost:11434/api/*/generate",
          "note": "escaped quote: \" // still text",
        }
        """
    )

    assert parsed == {
        "url": "http://localhost:11434/api/*/generate",
        "note": 'escaped quote: " // still text',
    }


def test_loads_jsonc_supports_block_comments_and_trailing_array_comma() -> None:
    parsed = loads_jsonc(
        """
        {
          /* multi-line\n+             rationale */
          "servers": ["mdpaper", "pubmed-search",],
        }
        """
    )

    assert parsed == {"servers": ["mdpaper", "pubmed-search"]}


@pytest.mark.parametrize("text", ["not json", "{/* unterminated", "[1,,2]"])
def test_loads_jsonc_rejects_invalid_documents(text: str) -> None:
    with pytest.raises(json.JSONDecodeError):
        loads_jsonc(text)
