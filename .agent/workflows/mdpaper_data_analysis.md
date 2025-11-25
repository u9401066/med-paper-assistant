---
description: Perform statistical analysis on uploaded data.
---

1. List available data files in the `data/` directory.
   `list_dir(DirectoryPath="/home/eric/workspace251125/data")`

2. Ask the user which file to analyze and to define the columns (e.g., "Which column is the Group? Which is the Outcome?").
   `notify_user(Message="Found the following files... Please specify which file to analyze and define the columns...")`

3. Based on user input, use the `analyze_dataset`, `run_statistical_test`, or `create_plot` tools.
   - If the user asks for a specific test (e.g., "2 group test"), map it to the appropriate tool (e.g., `run_statistical_test(..., test_type='t-test')`).
   - Always generate a visualization if appropriate (e.g., Boxplot for T-test).

4. Save the results (figures/tables) to `results/`.
   - The tools automatically save to `results/`.
   - Confirm the location to the user.
