---
description: Generate a medical paper draft from a concept file.
---

1. Read the user's concept file to understand the research content.
   `view_file(AbsolutePath="/home/eric/workspace251125/concept.md")`

1. **Read Context**: Read `concept.md` and any results in `results/`.
2. **Select Template**: Ask the user which journal template to use (default to `general_medical_journal.md` or `Type of the Paper.docx`).
3. **Generate Draft**: Write the paper draft to `drafts/` (e.g., `drafts/paper.md`). Use `(PMID:xxxx)` for citations.
4. **Insert Citations**: Use the `insert_citation` tool to resolve PMIDs and generate the bibliography.

   - Map the "Key Results" and "Methodology" from `concept.md` to the "Results" and "Methods" sections of the template.
   - Check `results/figures/` for any generated plots. If found, embed them in the "Results" section using markdown image syntax `![Caption](results/figures/filename.png)`.
   - Expand the "Hypothesis" into the "Introduction".
   - Ensure citations are inserted using `(PMID:xxxx)` format where appropriate.

5. Write the draft to a file using the `write_draft` tool.
   `write_draft(filename="draft_v1.md", content="...generated content...")`
