# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2025-11-25

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
