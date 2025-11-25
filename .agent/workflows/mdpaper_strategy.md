# Medical Paper Search Strategy Workflow

This workflow guides you through defining a complex search strategy and executing it.

## 1. Understand Requirements
Ask the user for their specific search requirements, including:
- **Keywords**: Main topics (e.g., "anesthesia", "postoperative pain").
- **Exclusions**: Topics to avoid (e.g., "children", "pediatric").
- **Study Types**: Preferred article types (e.g., "Clinical Trial", "Meta-Analysis").
- **Sample Size**: Minimum number of participants (e.g., >100).
- **Date Range**: Publication years (e.g., "2020:2025").

## 2. Configure Strategy
Once you have the requirements, format them into a JSON object and call the `configure_search_strategy` tool.

**Example JSON:**
```json
{
  "keywords": ["anesthesia", "postoperative pain"],
  "exclusions": ["children", "pediatric"],
  "article_types": ["Clinical Trial"],
  "min_sample_size": 100,
  "date_range": "2020:2025"
}
```

## 3. Execute Search
After configuring the strategy, run the search using the `search_literature` tool with `use_saved_strategy=True`.

**Example Tool Call:**
```python
search_literature(use_saved_strategy=True, limit=10)
```

## 4. Review Results
Present the results to the user. If the results are not satisfactory, ask the user for adjustments, update the strategy using `configure_search_strategy`, and search again.
