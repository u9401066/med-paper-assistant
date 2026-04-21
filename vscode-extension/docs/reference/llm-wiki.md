# LLM Wiki Reference

This reference captures the conceptual model behind the current MedPaper
agent-wiki workflow and records the external source that motivated it.

## Primary Reference

- Andrej Karpathy, `llm-wiki.md`
  - Gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
  - Raw: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f/raw/ac46de1ad27f92b28ac95459c782c07f6b8c964a/llm-wiki.md

## Why It Matters Here

Karpathy's core idea is not "query raw files every time". It is:

1. Keep raw sources immutable.
2. Let the LLM maintain a persistent markdown wiki between the user and the
   sources.
3. Use a schema / operating document so the agent behaves like a disciplined
   wiki maintainer rather than a generic chatbot.

That maps directly onto the MedPaper design:

- Raw sources: PubMed records, local files, web captures, markdown intake,
  source artifacts, and extracted sections.
- Wiki layer: reference notes, knowledge maps, synthesis pages, `index.md`, and
  `log.md`.
- Schema layer: MCP instructions, skills, prompts, hooks, frontmatter
  conventions, and trust labels.

## The Parts We Reused

- Persistent compiled knowledge instead of one-shot RAG answers.
- `index.md` and `log.md` as first-class navigation and operational artifacts.
- A repeating loop of ingest, query, and lint / refresh.
- Human-guided source curation with LLM-owned markdown maintenance.

## The Parts We Tightened For MedPaper

Karpathy's gist is intentionally abstract. In MedPaper we make several parts
more explicit:

- MedPaper is the durable writer; Foam is the reading and navigation layer.
- Notes carry explicit trust labels, provenance, and canonical identifiers.
- Local or extracted sources can be upgraded into verified canonical identities.
- Reference notes now materialize stable block anchors for key findings and
  evidence sections.
- Knowledge maps and synthesis pages now emit Foam-friendly queries and embeds.

## Known Practical Limits

These are relevant when applying the LLM wiki pattern in this repository:

- `notes/index.md` is still static and does not yet emit `foam-query` blocks.
- Table / figure snippets are not yet materialized as their own block-anchor
  targets.
- Current tags are standardized for note class and status, but not yet rich
  enough for deep topic-level filtering.
- For larger corpora, deterministic retrieval layers beyond a plain markdown
  index may still be needed.

## Related Local Files

- `docs/how-to/llm-wiki.md`
- `docs/reference/foam.md`
- `ARCHITECTURE.md`
- `src/med_paper_assistant/infrastructure/persistence/reference_manager.py`
- `memory-bank/kb-integration-blueprint.md`