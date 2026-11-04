"""Citation style selection and in-text/reference formatting."""

from typing import Any, Dict, Optional


class CitationFormatMixin:
    """Citation style selection and in-text/reference formatting."""

    def _get_preferred_citation_style(self) -> Optional[str]:
        """
        Get the preferred citation style from project settings.

        Returns:
            Citation style string (e.g., 'apa', 'vancouver') or None if not set.
        """
        if self._project_manager:
            try:
                current_slug = self._project_manager.get_current_project()
                if current_slug:
                    project_info = self._project_manager.get_project_info(current_slug)
                    if project_info.get("success"):
                        settings = project_info.get("settings", {})
                        return settings.get("citation_style")
            except (ValueError, KeyError):
                pass
        return None

    def _format_citation(self, article: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate pre-formatted citation strings in multiple formats.

        Args:
            article: Article metadata dictionary.

        Returns:
            Dictionary with citation strings in different formats.
        """
        fields = self._citation_fields(article)
        doi = fields["doi"]

        return {
            "vancouver": self._build_vancouver_citation(fields),
            "apa": self._build_apa_citation(fields),
            "nature": self._build_nature_citation(fields),
            "in_text": self._build_in_text_citation(fields),
            "pmid": f"PMID: {fields['pmid']}",
            "doi": f"doi:{doi}" if doi else "",
        }

    def _citation_fields(self, article: Dict[str, Any]) -> Dict[str, Any]:
        journal = article.get("journal", "Unknown Journal")
        return {
            "authors": article.get("authors", []),
            "authors_full": article.get("authors_full", []),
            "title": article.get("title", "Unknown Title").rstrip("."),
            "journal": journal,
            "journal_abbrev": article.get("journal_abbrev", journal),
            "year": article.get("year", ""),
            "volume": article.get("volume", ""),
            "issue": article.get("issue", ""),
            "pages": article.get("pages", ""),
            "doi": article.get("doi", ""),
            "pmid": article.get("pmid", ""),
        }

    def _format_vancouver_authors(self, auth_list, max_authors=6):
        if not auth_list:
            return "Unknown Author"

        formatted = []
        for i, author in enumerate(auth_list[:max_authors]):
            if isinstance(author, dict):
                if "collective_name" in author:
                    formatted.append(author["collective_name"])
                else:
                    last = author.get("last_name", "")
                    initials = author.get("initials", "")
                    formatted.append(f"{last} {initials}")
            else:
                # Fallback for simple string format
                parts = author.split()
                if len(parts) >= 2:
                    formatted.append(f"{parts[0]} {''.join([p[0] for p in parts[1:]])}")
                else:
                    formatted.append(author)

        result = ", ".join(formatted)
        if len(auth_list) > max_authors:
            result += ", et al"
        return result

    def _format_apa_authors(self, auth_list, max_authors=7):
        if not auth_list:
            return "Unknown Author"

        formatted = []
        for author in auth_list[:max_authors]:
            if isinstance(author, dict):
                if "collective_name" in author:
                    formatted.append(author["collective_name"])
                else:
                    last = author.get("last_name", "")
                    initials = author.get("initials", "")
                    # APA: Last, F. M.
                    init_formatted = ". ".join(list(initials)) + "." if initials else ""
                    formatted.append(f"{last}, {init_formatted}")
            else:
                parts = author.split()
                if len(parts) >= 2:
                    init = ". ".join([p[0] for p in parts[1:]]) + "."
                    formatted.append(f"{parts[0]}, {init}")
                else:
                    formatted.append(author)

        if len(formatted) == 1:
            result = formatted[0]
        elif len(formatted) == 2:
            result = f"{formatted[0]} & {formatted[1]}"
        else:
            result = ", ".join(formatted[:-1]) + f", & {formatted[-1]}"

        if len(auth_list) > max_authors:
            result = ", ".join(formatted[:6]) + ", ... " + formatted[-1]

        return result

    def _build_vancouver_citation(self, fields: Dict[str, Any]) -> str:
        volume, issue, pages, doi = (fields[k] for k in ("volume", "issue", "pages", "doi"))
        vancouver_auth = self._format_vancouver_authors(fields["authors_full"] or fields["authors"])
        vancouver = (
            f"{vancouver_auth}. {fields['title']}. "
            f"{fields['journal_abbrev'] or fields['journal']}. {fields['year']}"
        )
        if volume:
            vancouver += f";{volume}"
            if issue:
                vancouver += f"({issue})"
            if pages:
                vancouver += f":{pages}"
        vancouver += "."
        if doi:
            vancouver += f" doi:{doi}"
        return vancouver

    def _build_apa_citation(self, fields: Dict[str, Any]) -> str:
        volume, issue, pages, doi = (fields[k] for k in ("volume", "issue", "pages", "doi"))
        apa_auth = self._format_apa_authors(fields["authors_full"] or fields["authors"])
        apa = f"{apa_auth} ({fields['year']}). {fields['title']}. *{fields['journal']}*"
        if volume:
            apa += f", *{volume}*"
            if issue:
                apa += f"({issue})"
            if pages:
                apa += f", {pages}"
        apa += "."
        if doi:
            apa += f" https://doi.org/{doi}"
        return apa

    def _build_nature_citation(self, fields: Dict[str, Any]) -> str:
        nature_auth = self._format_vancouver_authors(
            fields["authors_full"] or fields["authors"], max_authors=5
        )
        nature = (
            f"{nature_auth} {fields['title']}. *{fields['journal_abbrev'] or fields['journal']}* "
            f"**{fields['volume']}**, {fields['pages']} ({fields['year']})."
        )
        if fields["doi"]:
            nature += f" https://doi.org/{fields['doi']}"
        return nature

    def _build_in_text_citation(self, fields: Dict[str, Any]) -> str:
        authors, authors_full, year = fields["authors"], fields["authors_full"], fields["year"]
        first_author = ""
        if authors_full:
            first_author = (
                authors_full[0].get("last_name", "")
                if isinstance(authors_full[0], dict)
                else authors[0].split()[0]
                if authors
                else ""
            )
        elif authors:
            first_author = authors[0].split()[0] if authors else ""

        if len(authors) == 1:
            return f"{first_author}, {year}"
        if len(authors) == 2:
            second_author = ""
            if authors_full and len(authors_full) > 1:
                second_author = (
                    authors_full[1].get("last_name", "")
                    if isinstance(authors_full[1], dict)
                    else authors[1].split()[0]
                )
            elif len(authors) > 1:
                second_author = authors[1].split()[0]
            return f"{first_author} & {second_author}, {year}"
        return f"{first_author} et al., {year}"
