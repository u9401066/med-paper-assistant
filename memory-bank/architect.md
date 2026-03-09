# Architect

## 系統架構

### 整體架構

```
med-paper-assistant/
├── src/med_paper_assistant/       # 核心程式碼
│   ├── domain/                    # 領域層 (DDD)
│   ├── application/               # 應用層
│   ├── infrastructure/            # 基礎設施層
│   ├── interfaces/mcp/            # MCP 介面
│   └── shared/                    # 共用模組
├── integrations/                  # 外部整合
│   ├── pubmed-search-mcp/         # PubMed 搜尋子模組
│   └── next-ai-draw-io/           # Draw.io forked submodule（主要共同開發線）
├── _workspace/                    # 🆕 成品暫存區 (Artifact-Centric)
│   ├── .registry.json             # 成品註冊表
│   ├── references/                # 暫存參考文獻
│   ├── pdfs/                      # 匯入 PDF
│   ├── notes/                     # 獨立筆記
│   ├── data/                      # 資料檔案
│   └── figures/                   # 圖表
├── projects/                      # 正式研究專案
├── memory-bank/                   # 專案記憶 (版控)
├── .github/bylaws/                # 子法規範
├── .claude/skills/                # Claude Skills
└── scripts/                       # 跨平台腳本
```

### MCP Server 架構 (81 tools, 2026-02-27)

```
.vscode/mcp.json
├── mdpaper        # 主要 MCP (81 tools) - 專案/草稿/參考/匯出/Workspace State/Self-Evolution
├── pubmed-search  # PubMed 搜尋 (submodule)
├── cgu            # Creativity Generation (submodule)
├── zotero-keeper  # 書目管理 (uvx)
└── drawio         # Draw.io 圖表 (npx @drawio/mcp)
```

### MCP Tool 模組分布 (2026-02-27)

```
tools/
├── project/       16 tools  CRUD + exploration + workspace state
├── reference/     10 tools  save_reference_mcp 優先
├── draft/         13 tools  writing + citation + editing (patch_draft)
├── validation/     3 tools  validate_concept + wikilinks
├── analysis/       9 tools  table_one + stats + figures
├── review/        20 tools  formatting + pipeline + audit + meta-learning + flexibility + tool_health
├── export/        10 tools  word + pandoc (docx/pdf/bib)
├── _shared/       — (非 MCP tool) guidance + tool_logging + project_context
└── discussion/    — (DEPRECATED — 已遷移至 Skills)
```

### Self-Evolution 架構 (2026-02-27)

> **核心價值：逐步多輪演進（CONSTITUTION §25-26）**
> 寫論文 = 人類多年累積的螺旋式進步。本系統用三層架構重現此過程。

```
三層演進架構（2026-02-27 深度審查結果）
═══════════════════════════════════════════════════

L1: Event-Driven Hooks（即時品質）⚠️ 23/65 Code-Enforced
    Code-Enforced (run_writing_hooks):
      A5 語言一致、A6 段落重複、B8 統計對齊、B9 時態、B10 段落品質
      B11 Results客觀性、B12 Intro結構、B13 Discussion結構
      B14 倫理聲明、B15 Hedging密度、B16 效果量報告
      C6 ICMJE字數(body-only)、C9 補充材料
      F1-F4 數據產出物（DataArtifactTracker）
    Code-Enforced (run_meta_learning):
      D1-D9 全部（MetaLearningEngine）
    Agent-Driven (42 hooks):
      A1-A4, B1-B7, C1-C8, E1-E5, P1-P8, G1-G8
      僅靠 Agent 閱讀 SKILL.md 自行執行

L2: Code-Level Enforcement（結構約束）✅ 完整
    DomainConstraintEngine → .constraints/*.json per project
    ToolInvocationStore → .audit/tool-telemetry.yaml
    PendingEvolutionStore → .audit/pending-evolutions.yaml
    guidance.py → build_startup_guidance (新對話提示)
    tool_health.py → diagnose_tool_health + flush to PE store

L3: Autonomous Self-Evolution（長期演進）⚠️ 部分
    ✅ MetaLearningEngine D1-D9 + flush to PendingEvolutionStore
    ✅ GitHub Actions weekly health check (evolution-health.yml)
    ✅ PendingEvolution 跨對話機制 (Phase C 完成)
    ❌ Git post-commit hook (Phase A 未開始)
    ❌ EvolutionVerifier 類別 (被引用但未實作)
    ❌ L3 建議自動產生 PR (Phase B 未完成)

整合流程：
    tool call → tool_logging → ToolInvocationStore
    → MetaLearningEngine D9 → PendingEvolutionStore
    → build_startup_guidance → 下次對話提示
    → apply_pending_evolutions → 套用/駁回
```

元件：QualityScorecard(8 dims), HookEffectivenessTracker(56 hooks),
MetaLearningEngine(D1-D9), WritingHooksEngine(A5/A6/B8/C9/F),
DomainConstraintEngine(3 paper types, 26 constraints),
ToolInvocationStore, PendingEvolutionStore, tool_health

### 狀態管理架構 (2025-01-22 新增)

**三階段狀態機**：

```
┌─────────────┐     save_reference     ┌─────────────┐
│             │    search_literature   │             │
│    EMPTY    │ ─────────────────────► │ EXPLORATION │
│             │    import_pdf          │             │
└─────────────┘                        └──────┬──────┘
                                              │
                                              │ create_project
                                              │ (user decision)
                                              ▼
                                       ┌─────────────┐
                                       │   PROJECT   │
                                       └─────────────┘
```

**狀態持久化**：

- `.mdpaper-state.json` - 全域 Workspace 狀態
- `projects/{slug}/project.json` - 專案狀態

**MCP 間通訊原則：**

- MCP 對 MCP 只要 API！
- 不直接 import 其他 MCP 的模組
- Agent (Copilot) 負責協調 MCP 間資料傳遞

**範例工作流程：**

```
用戶：「幫我儲存這篇 PMID:12345678」
1. Agent → pubmed-search: fetch_article_details(pmids="12345678")
2. Agent 取得 metadata dict
3. Agent → mdpaper: save_reference(article=<metadata>)
```

### 跨平台支援

- Windows: `.venv/Scripts/python.exe`
- Linux/macOS: `.venv/bin/python`
- 透過 mcp.json 的 `platforms` 配置自動切換

## 技術決策

### 2025-01-22: Artifact-Centric Architecture

- 新增 `_workspace/` 成品暫存區
- 三階段狀態機支援非線性工作流程
- 設計文件：[docs/design/artifact-centric-architecture.md](../docs/design/artifact-centric-architecture.md)

### 2025-01-22: Workspace State 跨 Session 持久化

- `WorkspaceStateManager` singleton
- `.mdpaper-state.json` 狀態檔案
- 三個新工具支援 context 恢復

### 2025-12-17: 跨平台架構

- 採用 VS Code MCP 的 platforms 配置
- setup.sh (Linux/macOS) + setup.ps1 (Windows) 並行維護

### 2025-12-03: Foam 整合

- 參考文獻使用 `[[author_year_pmid]]` 格式
- 自動建立 Foam alias 檔案

### 2025-12-02: 子模組獨立化

- pubmed-search-mcp 獨立為 Git 子模組
- 可單獨使用或整合
