"""
Author Value Object - Structured author information for manuscripts.

Stores name, affiliations, ORCID, email, and corresponding author flag.
Used in project.json and manuscript title page generation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Author:
    """
    Structured author information for a research paper.

    Attributes:
        name: Full name (e.g., "Tz-Ping Gau")
        affiliations: List of institutional affiliations
        orcid: ORCID identifier (e.g., "0000-0001-2345-6789")
        email: Contact email
        is_corresponding: Whether this is the corresponding author
        order: Author order position (1-based)
    """

    name: str
    affiliations: List[str] = field(default_factory=list)
    orcid: str = ""
    email: str = ""
    is_corresponding: bool = False
    order: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return {
            "name": self.name,
            "affiliations": list(self.affiliations),
            "orcid": self.orcid,
            "email": self.email,
            "is_corresponding": self.is_corresponding,
            "order": self.order,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Author":
        """Deserialize from dictionary.

        Handles both structured dicts and legacy plain-string entries.
        """
        if isinstance(data, str):
            # Legacy format: just a name string
            return cls(name=data)
        return cls(
            name=data.get("name", ""),
            affiliations=data.get("affiliations", []),
            orcid=data.get("orcid", ""),
            email=data.get("email", ""),
            is_corresponding=data.get("is_corresponding", False),
            order=data.get("order", 0),
        )

    def format_for_manuscript(self, affiliation_numbers: Optional[List[int]] = None) -> str:
        """Format author name with affiliation superscripts for manuscript.

        Args:
            affiliation_numbers: Superscript numbers for affiliations.

        Returns:
            Formatted string like "Tz-Ping Gau^{1,2}*"
        """
        result = self.name
        if affiliation_numbers:
            nums = ",".join(str(n) for n in affiliation_numbers)
            result += f"^{{{nums}}}"
        if self.is_corresponding:
            result += "*"
        return result


def generate_author_block(authors: List[Author]) -> str:
    """Generate a complete author block for manuscript title page.

    Produces:
    - Author line with affiliation superscripts
    - Numbered affiliation list
    - Corresponding author line with email

    Args:
        authors: List of Author objects, ordered by `order` field.

    Returns:
        Formatted markdown string for title page.
    """
    if not authors:
        return ""

    # Sort by order
    sorted_authors = sorted(authors, key=lambda a: a.order or 999)

    # Collect unique affiliations in order
    affiliation_list: List[str] = []
    author_aff_map: Dict[str, List[int]] = {}

    for author in sorted_authors:
        nums = []
        for aff in author.affiliations:
            if aff not in affiliation_list:
                affiliation_list.append(aff)
            nums.append(affiliation_list.index(aff) + 1)
        author_aff_map[author.name] = nums

    # Build author line
    author_parts = []
    for author in sorted_authors:
        author_parts.append(author.format_for_manuscript(author_aff_map.get(author.name)))
    author_line = ", ".join(author_parts)

    # Build affiliation list
    aff_lines = []
    for i, aff in enumerate(affiliation_list, 1):
        aff_lines.append(f"^{i}^ {aff}")

    # Build corresponding author line
    corresponding = [a for a in sorted_authors if a.is_corresponding]

    lines = ["## Authors", "", author_line, ""]
    if aff_lines:
        lines.append("## Affiliations")
        lines.append("")
        lines.extend(aff_lines)
        lines.append("")

    if corresponding:
        ca = corresponding[0]
        lines.append("## Corresponding Author")
        lines.append("")
        ca_line = f"**{ca.name}**"
        if ca.email:
            ca_line += f", Email: {ca.email}"
        if ca.orcid:
            ca_line += f", ORCID: {ca.orcid}"
        lines.append(ca_line)
        lines.append("")

    return "\n".join(lines)
