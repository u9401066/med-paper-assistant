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
| Link reference definitions | Standard Markdown references generated from wikilinks | Enabled in workspace settings for export compatibility |
| Daily notes | Timestamped note workflow | Routed to `notes/` for research journaling |
| Note embeds | `![[note]]`, section, and block embeds | Used for figures/assets plus embedded evidence cards in knowledge maps and synthesis pages |
| Block anchors | `[[note#^block-id]]` and `![[note#^block-id]]` | Materialized for key findings and extracted/fulltext evidence blocks in reference notes |
| Foam queries | Dynamic lists/tables in preview via `foam-query` | Emitted in knowledge maps and synthesis pages for live counts and linked-reference tables |
| Resource filters | Filter commands/graph scope by tag/type/path | Standardized `type` and `tags` now support more reliable filtering; project scoping still uses `foam.files.ignore` |

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
- Hover preview, backlinks, graph, and rename sync are intentionally delegated
  to Foam rather than duplicated in MedPaper.

Needs follow-up:

- Block anchors are still not emitted for table/figure snippets or richer
  asset-aware evidence fragments beyond section-level blocks.
- `foam-query` is now used in knowledge maps and synthesis pages, but not yet in
  `notes/index.md` or other top-level navigation notes.
- Tags are standardized at the note-class level, but we do not yet project more
  granular topic tags, study-design tags, or project-specific tags for richer
  filtered graph views.
- Cross-note embeds now cover key findings and the first evidence block, but we
  do not yet materialize a broader embed strategy for multiple evidence blocks
  or direct source-artifact embeds.

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

## Recommended Next Alignment Work

1. Extend block-anchor generation to table/figure snippets and richer
  asset-aware evidence fragments.
2. Emit `foam-query` blocks in `notes/index.md` and other navigation notes for
  workspace-level live discovery.
3. Add richer tag taxonomy so Foam tag explorer can distinguish topic,
  methodology, and project scope beyond basic note-class tags.
4. Expand embed generation beyond the first evidence block, including direct
  source-artifact embeds where the underlying note path is stable.

## Relevant Local Files

- `ARCHITECTURE.md`
- `docs/design/citation-tools-architecture.md`
- `src/med_paper_assistant/infrastructure/persistence/reference_manager.py`
- `src/med_paper_assistant/infrastructure/services/foam_settings.py`
- `.vscode/settings.json`