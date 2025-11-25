# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **Citation Styles**: Support for Vancouver, APA, Harvard, Nature, and AMA styles.
- **Local Search**: Ability to search saved references by title and abstract.
- **Section Prompts**: Writing guidelines for major paper sections.
- **Logging**: System-wide logging to `logs/` directory.
- **Search Strategies**: Configurable strategies for PubMed search (Recent, Most Cited, Relevance).

### Changed
- Refactored `LiteratureSearcher` to use `SearchStrategy` enum.
- Updated `Drafter` to support dynamic citation formatting.
- Moved `templates/` to project root for better accessibility.

## [0.1.0] - 2024-11-25

### Added
- **Literature Search**: Integration with PubMed API for searching and fetching paper details.
- **Reference Management**: Local storage for references with metadata and content.
- **Draft Generation**: Automated draft creation with citation placeholders `(PMID:xxxx)` and bibliography generation.
- **Data Analysis**: Module for loading CSV data, performing statistical tests (T-test, Correlation), and generating plots (Scatter, Bar, Box).
- **Word Export**: Functionality to export drafts and embedded images to `.docx` format using templates.
- **Workflows**:
    - `/mdpaper.concept`: Interactive research concept development.
    - `/mdpaper.draft`: Automated draft generation from concepts.
    - `/mdpaper.data_analysis`: Interactive data analysis and visualization.
    - `/mdpaper.clarify`: Interactive content refinement.
    - `/mdpaper.apply_format`: Export to formatted Word documents.
- **MCP Server**: FastMCP implementation exposing all tools to VSCode agents.
