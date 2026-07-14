# Skills Directory

This directory contains the Agent knowledge base (Skills) that are embedded into the MCP server instructions.

## Structure

Each skill is a directory containing:

- `SKILL.md` - The skill definition and workflow

## Available Skills

### Research Skills

- `literature-review/` - Systematic literature search and review
- `concept-development/` - Research concept development and validation
- `parallel-search/` - Multi-query parallel search

### Writing Skills

- `draft-writing/` - Paper section drafting
- `reference-management/` - Citation and reference management
- `word-export/` - Word document export

### Project Skills

- `project-management/` - Research project management
- `concept-validation/` - Novelty validation

## How Skills Work

1. **Loading**: When the extension activates, only skills listed in `bundle-manifest.json` are copied/registered for the packaged surface
2. **Injection**: Manifest-listed skills are available to the agent; authoring-only skill directories excluded by `.vscodeignore` stay out of the VSIX
3. **Usage**: The AI agent references these skills when processing requests

## Adding New Skills

1. Create a new directory: `skills/my-skill/`
2. Add `SKILL.md` with the skill definition
3. Rebuild the extension
