"""Unit tests for the shared slug helpers (med_paper_assistant.shared.slug)."""

from __future__ import annotations

import pytest

from med_paper_assistant.shared.slug import slugify_name, slugify_token


class TestSlugifyName:
    """Variant A: spaces/underscores -> hyphen, other non-alnum DROPPED."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("Hello World", "hello-world"),
            ("Hello_World", "hello-world"),
            ("Hello   World", "hello-world"),
            ("Difficult Airway Prediction", "difficult-airway-prediction"),
            ("a.b.c", "abc"),  # dots are DROPPED (distinct from slugify_token)
            ("Foo!!Bar??", "foobar"),
            ("  Trim Me  ", "trim-me"),
            ("multi---hyphen", "multi-hyphen"),
        ],
    )
    def test_slugify_name(self, raw: str, expected: str) -> None:
        assert slugify_name(raw) == expected

    def test_empty_uses_fallback(self) -> None:
        assert slugify_name("") == "untitled"
        assert slugify_name("!!!") == "untitled"
        assert slugify_name("", fallback="custom") == "custom"


class TestSlugifyToken:
    """Variant B: every non-alnum run -> single hyphen (dots KEPT as separators)."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("Hello World", "hello-world"),
            ("a.b.c", "a-b-c"),  # dots become hyphens (distinct from slugify_name)
            ("New England J. Med.", "new-england-j-med"),
            ("Foo__Bar", "foo-bar"),
            ("trailing--", "trailing"),
        ],
    )
    def test_slugify_token(self, raw: str, expected: str) -> None:
        assert slugify_token(raw) == expected

    def test_empty_uses_fallback(self) -> None:
        assert slugify_token("") == "untitled"
        assert slugify_token("---") == "untitled"
        assert slugify_token("", fallback="view") == "view"


class TestVariantsDiffer:
    """The two algorithms must remain distinct on dot handling."""

    def test_dot_handling_differs(self) -> None:
        assert slugify_name("a.b.c") == "abc"
        assert slugify_token("a.b.c") == "a-b-c"
        assert slugify_name("a.b.c") != slugify_token("a.b.c")
