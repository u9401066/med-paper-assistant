---
description: Interactively refine specific sections of concept or draft files.
---

1. Ask the user which file they want to refine (`concept.md` or a specific draft in `drafts/`) and which section (e.g., "Hypothesis", "Introduction").
   `notify_user(Message="Which file and section would you like to clarify?")`

2. Read the content of the specified file.
   `view_file(AbsolutePath="...")`

3. Discuss the specific changes with the user. Ask for the new text or the desired improvement.
   `notify_user(Message="Current content is... How would you like to change it?")`

4. Apply the changes to the file.
   - Use `replace_file_content` for single blocks.
   - Use `multi_replace_file_content` if multiple non-contiguous edits are needed.
   - If editing a draft, ensure you don't break existing citation placeholders `[PMID:xxxx]` or `[x]`.

5. Confirm the update with the user.
   `notify_user(Message="Updated the section. Is this correct?")`
