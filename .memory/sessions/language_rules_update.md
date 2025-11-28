# Language Rules Update - 2025-11-28

## Change
Added language rules to `instructions.py` to prevent AI from translating academic English content.

## Rules Added
```
### 🌐 LANGUAGE RULES
**NEVER translate academic English content:**
- Paper titles → Keep original English
- Journal names → Keep original
- Author names → Keep original
- Medical terms → Keep original
- Abstract content → Keep original

**Only translate when explicitly asked by user.**
```

## Reason
User requested that MCP tool results (especially paper titles) remain in original English without automatic translation.

## File Modified
- `src/med_paper_assistant/interfaces/mcp/instructions.py`

## Impact
- AI agents following MCP instructions will preserve academic English
- Better for researchers who need exact titles for citation/search
