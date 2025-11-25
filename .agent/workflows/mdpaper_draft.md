---
description: Generate a medical paper draft from a concept file.
---

1. Read the user's concept file to understand the research content.
   `view_file(AbsolutePath="/home/eric/workspace251125/concept.md")`

2. Read the target journal template to understand the required structure.
   `view_file(AbsolutePath="/home/eric/workspace251125/src/med_paper_assistant/templates/general_medical_journal.md")`

3. (Optional) If there are PMIDs in `concept.md` that are not yet saved, use `save_reference` to fetch them.

4. Generate the draft content.
   - Map the "Key Results" and "Methodology" from `concept.md` to the "Results" and "Methods" sections of the template.
   - Check `results/figures/` for any generated plots. If found, embed them in the "Results" section using markdown image syntax `![Caption](results/figures/filename.png)`.
   - Expand the "Hypothesis" into the "Introduction".
   - Ensure citations are inserted using `(PMID:xxxx)` format where appropriate.

5. Write the draft to a file using the `write_draft` tool.
   `write_draft(filename="draft_v1.md", content="...generated content...")`
