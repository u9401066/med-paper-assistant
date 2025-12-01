# Skill System Integration

## 問題

Skills 是靜態的 Markdown 文件，Agent 不會自動知道它們的存在。
需要一個機制讓 Agent：
1. 知道有哪些 Skills 可用
2. 在適當時機載入並遵循 Skill
3. 跨 MCP 呼叫時正確協調

## 解決方案

### 方案 1: Copilot Instructions 整合（最簡單）

在 `.github/copilot-instructions.md` 中加入 Skill 索引：

```markdown
## Skills (工作流程指南)

當用戶要求執行以下任務時，先讀取對應的 Skill 文件：

| 觸發語句 | Skill 文件 |
|----------|------------|
| 文獻回顧、找論文、搜尋文獻 | `.skills/research/literature_review.md` |
| 發展概念、concept | `.skills/research/concept_development.md` |
| 寫 Introduction | `.skills/writing/draft_introduction.md` |
| 製作圖表、畫圖 | `.skills/analysis/figure_generation.md` |

**執行流程**：
1. 識別用戶意圖 → 對應的 Skill
2. `read_file` 讀取 Skill 內容
3. 按照 Skill 定義的工作流程執行
```

**優點**：不需要寫程式碼
**缺點**：依賴 Agent 遵循指示

---

### 方案 2: MCP Tool 整合（更可靠）

新增一個 `skill` 工具，讓 Agent 可以主動載入 Skill：

```python
@mcp.tool()
async def load_skill(skill_name: str) -> str:
    """
    載入指定的工作流程技能。
    
    Args:
        skill_name: 技能名稱，如 "literature_review", "concept_development"
    
    Returns:
        Skill 的完整內容，包含工作流程和決策點
    """
    skill_path = SKILLS_DIR / f"{skill_name}.md"
    if not skill_path.exists():
        # 搜尋子目錄
        for subdir in SKILLS_DIR.iterdir():
            if subdir.is_dir():
                candidate = subdir / f"{skill_name}.md"
                if candidate.exists():
                    skill_path = candidate
                    break
    
    if not skill_path.exists():
        return f"Skill '{skill_name}' not found. Available skills: {list_skills()}"
    
    return skill_path.read_text()

@mcp.tool()
async def list_skills() -> str:
    """列出所有可用的工作流程技能"""
    skills = []
    for path in SKILLS_DIR.rglob("*.md"):
        if path.name.startswith("_"):
            continue
        skills.append({
            "name": path.stem,
            "category": path.parent.name,
            "path": str(path.relative_to(SKILLS_DIR))
        })
    return json.dumps(skills, indent=2)

@mcp.tool()
async def suggest_skill(task_description: str) -> str:
    """根據任務描述建議適合的 Skill"""
    # 簡單的關鍵字匹配或用 LLM 判斷
    ...
```

**優點**：更可靠，Agent 可以主動查詢
**缺點**：需要實作

---

### 方案 3: MCP Prompt 整合（最優雅）

使用 MCP 的 Prompt 功能，讓用戶可以直接觸發：

```python
@mcp.prompt()
def skill_literature_review() -> str:
    """執行系統性文獻回顧的完整工作流程"""
    return read_skill("research/literature_review.md")

@mcp.prompt()
def skill_concept_development() -> str:
    """發展並驗證研究概念"""
    return read_skill("research/concept_development.md")
```

用戶可以輸入 `/skill_literature_review` 來觸發。

**優點**：標準 MCP 機制
**缺點**：每個 Skill 需要一個 Prompt

---

## 跨 MCP 協調問題

### 問題

一個 Skill 可能需要呼叫多個 MCP 的工具：

```
literature_review.md:
  → mdpaper: search_literature, save_reference
  → drawio: create_diagram (PRISMA flowchart)
```

### 解決方案

#### A. Agent 層級協調（現有方式）

Agent（Copilot）本身可以呼叫多個 MCP 的工具，這是原生支援的。

```
Agent 讀取 Skill
  ↓
呼叫 mdpaper.search_literature()
  ↓
呼叫 mdpaper.save_reference()
  ↓
呼叫 drawio.create_diagram()  ← 不同 MCP，但 Agent 可以處理
  ↓
呼叫 mdpaper.save_diagram()
```

**這已經可以運作**，只要 Skill 寫清楚要呼叫哪個 MCP 的工具。

#### B. 資料傳遞問題

跨 MCP 時，資料如何傳遞？

**問題**：`drawio.create_diagram()` 產生的內容要傳給 `mdpaper.save_diagram()`

**解決**：
1. `drawio.get_diagram_content()` 返回 XML
2. Agent 將 XML 傳給 `mdpaper.save_diagram(content=xml)`

這需要在 Skill 中明確寫出資料流。

#### C. 統一介面（進階）

建立一個「協調層」MCP，包裝跨 MCP 操作：

```python
# coordinator_mcp.py
@mcp.tool()
async def create_and_save_diagram(
    description: str,
    project: str,
    diagram_type: str = "flowchart"
) -> str:
    """
    建立圖表並儲存到專案（協調 drawio + mdpaper）
    """
    # 1. 呼叫 drawio MCP
    diagram_xml = await call_mcp("drawio", "create_diagram", {...})
    
    # 2. 呼叫 mdpaper MCP
    result = await call_mcp("mdpaper", "save_diagram", {
        "project": project,
        "content": diagram_xml
    })
    
    return result
```

**優點**：用戶只需呼叫一個工具
**缺點**：需要 MCP-to-MCP 通訊機制

---

## 建議的實作順序

### Phase 1: 立即可用（今天）

1. 更新 `copilot-instructions.md` 加入 Skill 索引
2. 讓 Agent 知道要讀取 Skill 文件

### Phase 2: 更可靠（短期）

1. 實作 `list_skills()` 和 `load_skill()` 工具
2. Agent 可以主動查詢和載入 Skill

### Phase 3: 最佳體驗（中期）

1. 實作 MCP Prompts 對應每個 Skill
2. 用戶可以 `/skill:xxx` 直接觸發
3. 考慮統一協調層

---

## 測試驗證

確認系統運作的測試：

```
1. 用戶說「幫我做文獻回顧」
2. Agent 應該：
   - 識別需要 literature_review skill
   - 讀取 .skills/research/literature_review.md
   - 按照 Phase 1-6 執行
   - 在決策點詢問用戶
   - 正確呼叫 mdpaper 和 drawio 的工具
   - 產出預期的文件
```
