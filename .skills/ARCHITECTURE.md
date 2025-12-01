# Skill-Based Tool Architecture

## 設計目標

1. **用戶只看到 Skills**（高層級工作流程）
2. **Tools 被隱藏**（但 Agent 可以呼叫）
3. **一個 Skill 自動展開成多個 Tool 呼叫**

## 方案比較

### 方案 A: Server-Side Orchestration（伺服器端編排）

```python
@mcp.tool()
async def execute_skill(skill_name: str, parameters: dict) -> str:
    """
    執行一個完整的技能工作流程。
    
    這是用戶應該呼叫的主要介面。
    內部會自動呼叫多個底層工具。
    """
    skill = load_skill(skill_name)
    
    results = []
    for step in skill.workflow:
        # 直接呼叫內部函數，不是 MCP tool
        result = await internal_functions[step.tool](**step.params)
        results.append(result)
        
        if step.is_decision_point:
            # 返回中間結果，等待用戶決策
            return {
                "status": "awaiting_decision",
                "question": step.question,
                "progress": results
            }
    
    return {"status": "complete", "results": results}
```

**架構**：
```
MCP Tools (公開):
  - execute_skill(skill_name, params)
  - list_skills()
  
Internal Functions (不公開):
  - _search_literature(...)
  - _save_reference(...)
  - _format_references(...)
```

**優點**：
- 用戶只看到少數幾個 tool
- 完整的工作流程控制
- 可以處理複雜的邏輯

**缺點**：
- 失去 Agent 的靈活性
- 決策點處理複雜
- 需要重構所有工具

---

### 方案 B: Tool Grouping via Naming（命名分組）

使用前綴區分「公開」和「內部」工具：

```python
# 公開工具 - 用戶應該呼叫這些
@mcp.tool()
async def skill_literature_review(topic: str, ...) -> str:
    """執行文獻回顧技能"""
    ...

@mcp.tool()
async def skill_concept_development(...) -> str:
    """執行概念發展技能"""
    ...

# 內部工具 - 加上 _internal 前綴
@mcp.tool()
async def _internal_search_literature(...) -> str:
    """[內部工具] 搜尋文獻"""
    ...
```

然後在 Copilot Instructions 中說明：

```markdown
## Tool Usage Rules

- **ONLY use tools starting with `skill_`** for user requests
- Tools starting with `_internal_` are for advanced operations only
- When user asks for "文獻回顧", use `skill_literature_review`, NOT individual tools
```

**優點**：
- 簡單實作
- 保留靈活性
- 不需要大改架構

**缺點**：
- 依賴 Agent 遵守指示
- 所有工具仍然可見

---

### 方案 C: Dual MCP Servers（雙 MCP 伺服器）

```
┌─────────────────────────────────┐
│ MCP Server 1: Skills (公開)     │
│ - skill_literature_review       │
│ - skill_concept_development     │
│ - skill_draft_introduction      │
└───────────────┬─────────────────┘
                │ 內部呼叫
                ▼
┌─────────────────────────────────┐
│ MCP Server 2: Tools (內部)      │
│ - search_literature             │
│ - save_reference                │
│ - format_references             │
└─────────────────────────────────┘
```

只在 VS Code 中配置 Server 1，Server 2 只被 Server 1 呼叫。

**優點**：
- 真正隱藏底層工具
- 清晰的分層

**缺點**：
- MCP-to-MCP 通訊複雜
- 維護兩個伺服器

---

### 方案 D: Lazy Tool Registration（延遲註冊）⭐ 推薦

只註冊 Skill 工具，底層工具作為內部函數：

```python
# server.py
def create_server():
    mcp = FastMCP("MedPaperSkills")
    
    # 只註冊 Skill 工具
    register_skill_tools(mcp)
    
    # 底層服務作為內部依賴
    services = {
        "searcher": PubMedClient(...),
        "ref_manager": ReferenceManager(...),
        "drafter": Drafter(...),
    }
    
    # Skill 工具可以訪問這些服務
    mcp.state["services"] = services
    
    return mcp

# skills/literature_review.py
@mcp.tool()
async def skill_literature_review(topic: str, ...) -> str:
    """執行完整的文獻回顧工作流程"""
    services = mcp.state["services"]
    
    # 直接呼叫服務，不是 MCP tool
    results = await services["searcher"].search(topic)
    
    for r in results:
        await services["ref_manager"].save(r)
    
    return formatted_output
```

**優點**：
- 用戶只看到 Skill
- 底層邏輯完全隱藏
- 最乾淨的 API

**缺點**：
- 需要重構
- Skill 工具變得更複雜

---

## 推薦策略

### 短期（現在可用）

使用 **方案 B (命名分組)** + **Copilot Instructions**：

1. 保留現有 49 個工具
2. 新增 5-10 個 `skill_*` 高層工具
3. 在 instructions 中強調優先使用 skill

### 中期（1-2 週）

實作 **方案 D (Lazy Registration)**：

1. 將現有工具轉為內部函數
2. 只公開 Skill 工具
3. Skill 工具內部呼叫這些函數

### 長期（如果需要）

考慮 **方案 C (Dual Servers)** 如果需要更嚴格的隔離。

---

## 決策點處理

無論哪個方案，Skill 中的決策點是個挑戰：

```python
@mcp.tool()
async def skill_literature_review(topic: str, phase: str = "start", decision: str = None) -> str:
    """
    執行文獻回顧技能。
    
    這是一個多步驟工作流程，可能需要多次呼叫：
    1. 第一次呼叫: phase="start", 開始搜尋
    2. 如果需要決策: 返回問題，等待下次呼叫帶 decision
    3. 繼續直到完成
    
    Args:
        topic: 搜尋主題
        phase: 當前階段 (start, filtering, saving, formatting)
        decision: 用戶對上一個問題的回答
    """
    if phase == "start":
        results = await search(topic)
        return {
            "phase": "filtering",
            "results_count": len(results),
            "question": f"找到 {len(results)} 篇，要繼續篩選嗎？",
            "preview": results[:5]
        }
    
    if phase == "filtering" and decision == "yes":
        # 繼續...
```

這允許多輪對話式的 Skill 執行。
