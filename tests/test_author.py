"""Tests for Author value object and author block generation."""

from med_paper_assistant.domain.value_objects.author import Author, generate_author_block


class TestAuthor:
    """Tests for Author dataclass."""

    def test_from_string(self):
        author = Author.from_dict("Jane Doe")
        assert author.name == "Jane Doe"
        assert author.affiliations == []
        assert author.orcid == ""
        assert author.is_corresponding is False

    def test_from_dict(self):
        data = {
            "name": "Tz-Ping Gau",
            "affiliations": [
                "Department of Anesthesiology, Kaohsiung Medical University Hospital",
                "Center for Big Data Research, Kaohsiung Medical University",
            ],
            "orcid": "0000-0001-2345-6789",
            "email": "gau@example.com",
            "is_corresponding": True,
            "order": 1,
        }
        author = Author.from_dict(data)
        assert author.name == "Tz-Ping Gau"
        assert len(author.affiliations) == 2
        assert author.orcid == "0000-0001-2345-6789"
        assert author.is_corresponding is True
        assert author.order == 1

    def test_to_dict_roundtrip(self):
        original = Author(
            name="Test",
            affiliations=["Uni A"],
            orcid="0000-0000-0000-0001",
            email="test@test.com",
            is_corresponding=True,
            order=1,
        )
        d = original.to_dict()
        restored = Author.from_dict(d)
        assert restored.name == original.name
        assert restored.affiliations == list(original.affiliations)
        assert restored.orcid == original.orcid
        assert restored.is_corresponding == original.is_corresponding

    def test_format_for_manuscript(self):
        author = Author(name="Jane Doe", is_corresponding=True)
        formatted = author.format_for_manuscript([1, 2])
        assert "Jane Doe" in formatted
        assert "^{1,2}" in formatted
        assert "*" in formatted

    def test_format_without_affiliations(self):
        author = Author(name="Jane Doe")
        formatted = author.format_for_manuscript()
        assert formatted == "Jane Doe"


class TestGenerateAuthorBlock:
    """Tests for generate_author_block function."""

    def test_empty_authors(self):
        assert generate_author_block([]) == ""

    def test_single_author(self):
        authors = [
            Author(
                name="Tz-Ping Gau",
                affiliations=["Dept of Anesthesiology, KMU Hospital"],
                is_corresponding=True,
                email="gau@example.com",
                order=1,
            )
        ]
        block = generate_author_block(authors)
        assert "Tz-Ping Gau" in block
        assert "Dept of Anesthesiology" in block
        assert "Corresponding Author" in block
        assert "gau@example.com" in block

    def test_multiple_authors_shared_affiliation(self):
        authors = [
            Author(
                name="Author A", affiliations=["Uni X", "Uni Y"], order=1, is_corresponding=True
            ),
            Author(name="Author B", affiliations=["Uni X"], order=2),
        ]
        block = generate_author_block(authors)
        assert "Author A" in block
        assert "Author B" in block
        # Uni X should be affiliation 1 (shared)
        assert "^1^" in block  # Uni X
        assert "^2^" in block  # Uni Y

    def test_order_respected(self):
        authors = [
            Author(name="Second", order=2),
            Author(name="First", order=1),
        ]
        block = generate_author_block(authors)
        # First should appear before Second
        first_pos = block.index("First")
        second_pos = block.index("Second")
        assert first_pos < second_pos
