---
description: Update the research concept and start an interactive refinement session.
---

1. Update `concept.md` with the user's provided hypothesis or research question.
   `write_to_file(TargetFile="/home/eric/workspace251125/concept.md", ...)`

2. Analyze the concept for missing information (Title, Methodology, Specifics).

3. Ask the user clarifying questions to refine the concept.
   `notify_user(Message="Please clarify...")`
