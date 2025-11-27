# Active Context

## Current Focus
Novelty Validation System Implementation - COMPLETED

## Recent Changes (2025-11-27)

### Novelty Validation System
- Created `domain/services/novelty_scorer.py` - Scoring criteria and LLM prompts
- Created `infrastructure/services/concept_validator.py` - Comprehensive validation service
- Refactored `draft_tools.py` to use new ConceptValidator
- Added `validate_concept_quick` tool for fast structural checks

### Architecture Updates
- ConceptValidator uses 3-round scoring with 75+ threshold
- 5 evaluation dimensions: Uniqueness, Significance, Gap Alignment, Specificity, Verifiability
- Mandatory validation before any concept file processing
- Results cached for 24 hours

## New Files
```
domain/services/novelty_scorer.py         # Scoring definitions & prompts
infrastructure/services/concept_validator.py  # Validation service
```

## Key Features
1. **Multi-Round Evaluation**: 3 independent scoring rounds
2. **High Threshold**: All rounds must score 75+
3. **5 Dimensions**: Comprehensive novelty assessment
4. **Actionable Feedback**: Specific improvement suggestions
5. **Consistency Check**: Cross-section alignment validation

## Tool Count
- Total: 43 tools (was 42)
- New: `validate_concept_quick`

## Status
✅ ConceptValidator service created
✅ NoveltyScorer domain service created
✅ draft_tools.py refactored
✅ __init__.py exports updated
✅ README updated (EN + ZH)
⏳ Git commit and push pending
