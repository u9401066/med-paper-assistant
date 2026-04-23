# Foam Dependency Reference

This workspace uses Foam as the Markdown knowledge-base view layer.
MedPaper remains the canonical writer for references, notes, indexes, and
materialized wiki pages.

## Upstream References

- Repository: https://github.com/foambubble/foam
- Documentation: https://docs.foamnotes.com/

## Related Conceptual References

- `docs/reference/llm-wiki.md`

## Dependency Boundary

- Foam owns navigation and visualization in VS Code: wikilinks, backlinks,
  graph view, hover preview, link rename sync, daily notes, note embeds, and
  queries rendered in Markdown preview.
- MedPaper owns durable research state: reference identity, metadata,
  provenance, trust labels, analysis status, note generation, and project
  scoping.
- We do not fork Foam or reimplement its UI behavior. We emit Markdown and
  frontmatter that Foam can index reliably.

## Foam Features Relevant Here

| Feature | Upstream behavior | Current MedPaper usage |
| --- | --- | --- |
| Wikilinks | `[[note]]`, aliases, autocompletion | Primary citation and note linking surface |
| Backlinks | Shows inbound references to the active note | Used to inspect draft-to-reference usage |
| Graph visualization | Visual graph over notes and note types | Used as the reference and concept graph surface |
| Note properties | YAML frontmatter with `title`, `type`, `tags`, `alias(es)` | Used for reference metadata and graph labeling |
| Link reference definitions | Standard Markdown references generated from wikilinks | Enabled in workspace settings and materialized as publish-safe notes under `notes/publish/` |
| Daily notes | Timestamped note workflow | Library Wiki Path now provisions `daily/` templates plus `notes/` journaling |
| Note embeds | `![[note]]`, section, and block embeds | Used for figures/assets plus embedded evidence cards in knowledge maps and synthesis pages |
| Block anchors | `[[note#^block-id]]` and `![[note#^block-id]]` | Materialized for key findings and extracted/fulltext evidence blocks in reference notes |
| Foam queries | Dynamic lists/tables in preview via `foam-query` | Emitted in knowledge maps and synthesis pages for live counts and linked-reference tables |
| Resource filters | Filter commands/graph scope by tag/type/path | Standardized `type`, `tags`, and custom frontmatter now support project/domain/status-driven graph slices |
| Custom graph configs | Named graph views and group-based coloring/filtering | Managed views plus project-specific `graph_views_json` slices are written into `foam.graph.views` |

## Current Local Alignment

Aligned:

- Reference notes emit Foam-friendly YAML frontmatter with `title`, `type`,
  aliases, and domain metadata.
- Reference notes now emit standardized `tags` and stable `foam_type`
  frontmatter for better tag explorer and resource-filter behavior.
- Citation keys are normalized specifically for Foam wikilink completion.
- Workspace isolation is handled by `foam.files.ignore` so only the active
  project's note graph is exposed.
- `foam.edit.linkReferenceDefinitions` is enabled to keep wikilinks portable in
  non-Foam Markdown renderers.
- Reference notes materialize stable evidence anchors such as `^key-findings`
  and `^evidence-methods` for deep linking and embed targets.
- Knowledge maps and synthesis pages now emit `foam-query` blocks for live
  reference counts/tables and note-to-note evidence embeds.
- `notes/index.md` now emits live `foam-query` counts for references, draft
  sections, figures, and tables.
- Library Wiki Path now provisions `review/` and `daily/`, and
  `write_library_note` supports `capture`, `review`, and `daily` templates.
- `build_library_dashboard` now materializes graph-health, unread, metadata,
  review, assets, and synthesis dashboards, including a repair worklist under
  `notes/review/graph-repair-worklist.md`.
- Draft sections plus registered figures/tables are materialized as first-class
  graph notes under `notes/draft-sections/`, `notes/figures/`, and
  `notes/tables/`.
- Managed `foam.graph.views` are written automatically for Default, Evidence,
  Writing, Assets, and Review slices, and the VSIX exposes matching command
  palette commands.
- Project-specific `graph_views_json` values now flow into
  `settings.custom_graph_views` in `project.json` and are merged into the
  active `foam.graph.views` set.
- Publish-safe knowledge-base notes are now materialized under
  `notes/publish/reference-links.md` and `notes/publish/knowledge-base.md`.
- Reference tags now project project, journal, author, year, topic, MeSH,
  study-design, and lifecycle state metadata for richer graph grouping.
- Reference notes now emit explicit Graph Context links to materialized
  journal, author, topic, MeSH, and section hub notes, so imported articles do
  not remain graph isolates.
- Hover preview, backlinks, graph, and rename sync are intentionally delegated
  to Foam rather than duplicated in MedPaper.

Needs follow-up:

- Registered figure/table notes now emit summary, preview, review-observation,
  evidence-excerpt, table-row, and source-fragment block anchors backed by
  asset-aware manifest + blocks/segmentation artifacts when available.
- Asset notes still do not cover every underlying layout fragment inside a
  complex asset; current coverage is best-effort around the matched source
  block, bbox, and snippet.
- Cross-note embeds still favor key findings and summary excerpts rather than a
  broader multi-fragment embed strategy.
- VSIX graph commands cover the managed named views, and MedPaper now writes
  project-specific graph slices; fully ad hoc one-off inline Foam graph config
  shortcuts still rely on native Foam keybindings when needed.

## Recently Closed Copilot Alignments

| Upstream Foam feature | Current MedPaper state | Entry point |
| --- | --- | --- |
| Orphans / placeholders panels | Graph-health dashboards now surface orphan notes, unresolved wikilinks, placeholders, and metadata gaps | `build_library_dashboard(view="graph-health")` |
| Templates / daily notes | Inbox, review, and daily templates now ship through the MedPaper note writer | `write_library_note(template="capture|review|daily")` |
| Foam queries | Library dashboards now emit more live operational views | `build_library_dashboard(view="unread|metadata|review|assets|synthesis")` |
| Link reference definitions / publishing | Publish-safe reference packs are materialized for non-Foam renderers | `notes/publish/reference-links.md`, `notes/publish/knowledge-base.md` |
| Custom graph configs | Project-specific graph slices are merged into `foam.graph.views` | `update_project_settings(graph_views_json="...")` |

## Remaining Alignment Work

| Area | Remaining gap | Likely next step |
| --- | --- | --- |
| Asset fragments | Best-effort anchors still stop at the matched source block rather than a broader verified fragment set | Expand ETL-backed fragment identity and multi-block anchor emission |
| Taxonomy hubs | Journal/author/topic/MeSH nodes exist but are still intentionally lightweight | Add richer hub-note summaries and cross-hub navigation pages |
| Embed strategy | Embedded evidence still favors key findings and first-fragment summaries | Expand multi-fragment embeds and source-artifact embeds where note paths stay stable |

## Workspace Settings We Intentionally Use

```json
{
  "foam.edit.linkReferenceDefinitions": "withExtensions",
  "foam.links.hover.enable": true,
  "foam.links.sync.enable": true,
  "foam.openDailyNote.directory": "notes",
  "foam.preview.embedNoteType": "full-card"
}
```

`foam.preview.embedNoteType` matches the current Foam docs. Older references to
`foam.preview.embedNoteStyle` in this repo should be considered outdated.

Project-specific graph slices are stored in `project.json` under
`settings.custom_graph_views` and merged into `.vscode/settings.json` during
project switches or settings updates.

## Recommended Next Alignment Work

1. Expand source-fragment anchoring from the matched source block into broader
  multi-block asset coverage where the ETL can prove fragment identity.
2. Expand asset-note generation from registration-level cards into richer
  fragment-level evidence blocks where stable anchors are available.
3. Add more navigation notes beyond `notes/index.md` for opinionated entry
  points such as methodology maps or reviewer worklists.
4. Expand embed generation beyond the first evidence block, including direct
  source-artifact embeds where the underlying note path is stable.

## Relevant Local Files

- `ARCHITECTURE.md`
- `docs/design/citation-tools-architecture.md`
- `src/med_paper_assistant/infrastructure/persistence/reference_manager.py`
- `src/med_paper_assistant/infrastructure/services/foam_settings.py`
- `.vscode/settings.json`