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

1. **Loading**: When the extension activates, all `SKILL.md` files are loaded
2. **Injection**: Skills are combined into MCP server instructions
3. **Usage**: The AI agent references these skills when processing requests

## Adding New Skills

1. Create a new directory: `skills/my-skill/`
2. Add `SKILL.md` with the skill definition
3. Rebuild the extension
