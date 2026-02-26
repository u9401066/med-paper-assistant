from unittest.mock import MagicMock

import pytest

from med_paper_assistant.infrastructure.persistence.reference_manager import ReferenceManager
from med_paper_assistant.infrastructure.services.drafter import Drafter


@pytest.fixture
def mock_ref_manager():
    rm = MagicMock(spec=ReferenceManager)
    # Mock metadata for PMID 12345
    rm.get_metadata.return_value = {
        "title": "Test Paper",
        "authors": ["Smith J", "Doe A"],
        "journal": "J Test",
        "year": "2023",
    }
    return rm


def test_citation_styles(mock_ref_manager, tmp_path):
    drafter = Drafter(mock_ref_manager, drafts_dir=str(tmp_path))
    content = "This is a claim (PMID:12345)."

    # 1. Test Vancouver (Default)
    drafter.set_citation_style("vancouver")
    path = drafter.create_draft("test_vancouver", content)
    with open(path, "r") as f:
        text = f.read()
    assert "This is a claim [1]." in text
    assert "[1] Smith J, Doe A. Test Paper. J Test. 2023." in text

    # 2. Test APA
    drafter.set_citation_style("apa")
    path = drafter.create_draft("test_apa", content)
    with open(path, "r") as f:
        text = f.read()
    assert "This is a claim (Smith & Doe, 2023)." in text
    assert "Smith J, Doe A (2023). Test Paper. J Test." in text

    # 3. Test Harvard
    drafter.set_citation_style("harvard")
    path = drafter.create_draft("test_harvard", content)
    with open(path, "r") as f:
        text = f.read()
    assert "This is a claim (Smith and Doe 2023)." in text
    assert "Smith J, Doe A (2023) 'Test Paper', J Test." in text

    # 4. Test Nature
    drafter.set_citation_style("nature")
    path = drafter.create_draft("test_nature", content)
    with open(path, "r") as f:
        text = f.read()
    assert "This is a claim ^1^." in text
    assert "1. Smith J, Doe A. Test Paper. J Test 2023." in text


def test_invalid_style(mock_ref_manager, tmp_path):
    drafter = Drafter(mock_ref_manager, drafts_dir=str(tmp_path))
    with pytest.raises(ValueError):
        drafter.set_citation_style("invalid_style")
