---
description: Export draft and figures to a Word document using a template.
---

1. Ask the user for the draft file they want to format and the template file they want to use.
   `notify_user(Message="Which draft file and template would you like to use?")`

2. If the user provides a template name (e.g., "sensors"), check if it exists in `src/med_paper_assistant/templates/`. If not, ask for the full path.

3. Call the `export_word` tool.
   `export_word(draft_filename="...", template_path="...", output_filename="...")`

4. Confirm the location of the exported file.
   `notify_user(Message="Exported to ...")`
