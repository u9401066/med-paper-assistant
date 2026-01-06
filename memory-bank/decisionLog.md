# Decision Log

## [2025-01-22] Artifact-Centric Architecture 設計

### 背景
發現現有「專案優先」架構無法支援非線性工作流程。研究者可能從搜尋、PDF、資料等多種入口開始，不一定先建立專案。

### 選項
1. 維持專案優先，提供快速建立專案
2. 新增 Exploration 暫存區，讓成品可以先存再連結

### 決定
選擇方案 2：Artifact-Centric Architecture

### 設計決策

| 問題 | 選項 | 決策 | 理由 |
|------|------|------|------|
| 成品歸屬 | A.Copy / B.Symlink / C.Reference | **C. Reference** | 多對多關係最彈性 |
| 強制專案時機 | A.Never / B.Export / C.Validate | **B. Export** | 探索階段零阻力 |
| 向後相容 | A.Keep Both / B.Migrate / C.Gradual | **A. Keep Both** | 最小影響 |

### 影響
- 新增 `_workspace/` 成品暫存區
- 三階段狀態機：EMPTY → EXPLORATION → PROJECT
- 新增 6 個 Exploration 工具
- 設計文件：[docs/design/artifact-centric-architecture.md](../docs/design/artifact-centric-architecture.md)

---

## [2025-01-22] Workspace State 跨 Session 持久化

### 背景
Agent 被 summarize 後遺失專案 context，每次新對話都要重新問用戶「你在做哪個專案？」

### 決定
實作 `WorkspaceStateManager` singleton，狀態存於 `.mdpaper-state.json`

### 影響
- 三個新工具：`get_workspace_state`, `sync_workspace_state`, `clear_recovery_state`
- 新對話開始時自動恢復上次工作 context
- 工具總數：69 → 72

---

## [2025-12-17] 跨平台架構重構

### 背景
原專案在 Linux 環境開發，需要支援 Windows 開發環境。

### 選項
1. 維持 Linux only，使用 WSL
2. 重構為跨平台支援 (Windows/Linux/macOS)

### 決定
選擇方案 2：跨平台架構

### 理由
- 提高開發彈性
- 減少環境依賴
- VS Code MCP 支援 platforms 配置

### 影響
- `.vscode/mcp.json` 使用 platforms 配置
- `scripts/setup.sh` 和 `setup.ps1` 並行維護
- 路徑使用正斜線 `/` 以相容兩平台

---

## [2025-12-17] Memory Bank 統一化

### 背景
原本使用 `.memory/` 目錄，與 template 的 `memory-bank/` 不一致。

### 決定
統一使用 `memory-bank/` 目錄，並納入版本控制。

### 理由
- 與 template-is-all-you-need 一致
- 透過 bylaws 和 skills 強制寫入
- 便於協作和追蹤

### 影響
- 刪除 `.memory/` 目錄
- 更新所有引用路徑
- 更新 .gitignore 確保追蹤 memory-bank
| 2025-12-17 | 將 .agent_constitution.md 整合進正式 CONSTITUTION.md，版本升級至 v1.1.0 | Agent 行為規範和研究操作規則應納入專案憲法正式管理，避免分散在多個檔案造成維護困難。新增第四至六章涵蓋：Agent 行為規範、研究操作規則（含 Concept/Draft 流程）、互動指南。 |
| 2025-12-17 | 重構 integrations 為選擇性 submodule 架構 | 採用選擇性 submodule 策略：pubmed-search-mcp 和 CGU 作為 submodule（常改代碼），drawio 和 zotero-keeper 改用獨立 uvx 安裝（較少改動）。Python 版本升級至 >=3.11 以支援 CGU。 |
| 2025-12-17 | mdpaper MCP 完全解耦 pubmed_search 依賴 | **MCP 對 MCP 只要 API！** 移除 mdpaper 對 pubmed_search 的所有 import，改為透過 Agent 協調 MCP 間通訊。刪除：infrastructure/external/{entrez,pubmed}、services/strategy_manager.py、tools/search/、use_cases/search_literature.py。重構 ReferenceManager 接受 metadata dict 而非 PMID。 |
| 2025-12-17 | DDD 重構：建立 ReferenceConverter Domain Service 支援多來源 (PubMed, Zotero, DOI) | 1. Foam 需要唯一識別符支援 [[wikilink]] 功能
2. 不同來源有不同格式，需要統一轉換
3. 遵循 DDD 架構：Domain Service 處理格式轉換
4. Agent 協調 MCP 通訊，不需要 mdpaper 直接呼叫其他 MCP |

---

## [2025-01-XX] 分層驗證系統 (Tiered Validation)

### 背景
用戶想寫 Introduction，但 concept 驗證要求完整 Methods 區塊。
> "concept 雖然要求寫 method 但是其實有可能 draft 只想寫 introduction"
> "meta 跟 systematic review 或 research letter 要的又不一樣"

### 問題
1. **流程阻塞**：Methods 未填會阻擋所有 section 撰寫
2. **類型差異**：不同 paper type 需要不同區塊（case report 不需要 Methods）
3. **驗證粒度**：全有或全無，不支援漸進式撰寫

### 決定
實施 **分層驗證系統**：
1. 按 paper type 定義不同需求 (`ConceptRequirements`)
2. 按 target section 動態調整驗證範圍
3. 區分 `required`（blocking）vs `recommended`（warning only）

### 架構變更

**paper_types.py** 新增：
```python
@dataclass
class ConceptRequirements:
    core_required: List[str]      # 永遠必須
    intro_required: List[str]     # Introduction 需要
    methods_required: List[str]   # Methods 建議（不阻塞）
    special_sections: List[str]   # 類型特定

# 每種 paper type 有對應的 requirements
get_concept_requirements(paper_type) -> ConceptRequirements
get_section_requirements(paper_type, section) -> Dict
```

**concept_validator.py** 新增：
- `validate(target_section="Introduction")` - 針對特定 section
- `validate_for_section()` - 便捷方法
- `_can_write_section()` - 判斷是否可寫
- `missing_required` / `missing_recommended` 區分

**MCP tools** 新增：
- `validate_for_section(section, project)` - 推薦的驗證入口

### 驗證矩陣

| Paper Type | Core | Intro | Methods | Special |
|------------|------|-------|---------|---------|
| original-research | NOVELTY, SELLING_POINTS | background, gap, question | study_design, participants | pre_analysis |
| systematic-review | same | same | search_strategy | prisma_checklist |
| case-report | same | same | - | case_timeline |
| letter | NOVELTY only | minimal | - | - |

### 影響
- ✅ 用戶可以先寫 Introduction，Methods 稍後補
- ✅ 不同 paper type 有適當的驗證要求
- ✅ 漸進式撰寫流程
- ⚠️ SKILL.md 和文檔需更新
