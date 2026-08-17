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
│   ├── asset-aware-mcp/           # PDF/DOCX 與 reusable assets（SDK2）
│   ├── pubmed-search-mcp/         # PubMed 搜尋（SDK2）
│   ├── cgu/                       # 創意與論證壓力測試（SDK2）
│   └── next-ai-draw-io/           # Draw.io Python/TypeScript servers（SDK2）
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
├── .agents/skills/                # Codex + OpenClaw 共用 Skills
├── .claude/skills/                # Claude Code / workflow Skills
└── scripts/                       # 跨平台腳本
```

### Cross-Agent Harness 架構 (2026-07-14)

- `AGENTS.md`：Codex 與 repo-level 治理權威；OpenClaw workspace 亦可使用。
- `CLAUDE.md`：Claude Code 精簡 always-loaded 入口，不複製完整治理內容。
- `.agents/skills/academic-writing-harness/`：Codex 與 OpenClaw 共用 discovery root。
- `.claude/skills/academic-writing-harness/`：Claude Code discovery adapter。
- `docs/harness/academic-writing-workflow.md`：平台中立寫作、exemplar、phase 與 completion contract。
- `tests/test_agent_harness_contract.py`：frontmatter、路徑、支援類型與可攜性 gate。

原則：平台 adapter 只負責 discovery/tool mapping；科學方法、證據角色與 hard-gate 語義維持單一權威。

### MCP Server 架構 (118 full / 12 compact default, 2026-08-17)

```
.vscode/mcp.json
├── mdpaper        # 主要 MCP（118 full / 12 compact default）
├── pubmed-search  # PubMed 搜尋（immutable submodule/archive）
├── cgu            # Creativity Generation（immutable submodule/archive）
├── asset-aware    # PDF/DOCX evidence intake（immutable submodule/archive）
├── zotero-keeper  # 書目管理（immutable commit archive）
└── drawio         # Draw.io Python server（immutable submodule/archive）
```

### MCP Tool 模組分布 (2026-05-19)

```
tools/
├── project/       CRUD + settings + exploration + diagrams + workspace state
├── reference/     save_reference_mcp 優先 + wiki materialization + identity helpers
├── draft/         writing + citation + editing (patch_draft)
├── validation/    concept / wikilink / literature-comparison validation
├── analysis/      table_one + stats + figures + asset insertion
├── review/        formatting + pipeline + audit + review hooks + tool_health
├── export/        word + pandoc (docx/pdf/bib) facade workflow
├── façade/        project/workspace/review/pipeline/export stable entrypoints
├── _shared/       — (非 MCP tool) guidance + tool_logging + project_context + optional decorators
└── discussion/    — (DEPRECATED — 已遷移至 Skills)
```

### Tool Surface Policy (2026-08-17)

- **full**: 保留所有 118 個 first-party tools，供開發、相容性、進階 orchestration 使用
- **compact**: 預設公開 12 個 workflow tools，以 façade-first surface 為主，降低 agent 選錯 granular verbs 的機率
- **切換方式**: 透過 `MEDPAPER_TOOL_SURFACE=full|compact` 控制；workspace setup、`.vscode/mcp.json` 與 VSX runtime 預設注入 `compact`
- **Authority**: `tool-surface-authority.json` 是 README / VSIX / validate gate 的單一權威來源

### Content Integrity 與 Reference Trust (2026-08-17)

- Domain：`ContentIntegrityReceipt` / status/value objects 定義不可變的 hash、provenance 與 review decision。
- Application：`ContentIntegrityInspector` 編排 MIME、SHA-256、C2PA 與 visible-watermark signals，不依賴 MCP/UI。
- Infrastructure：optional `c2pa-python` adapter 禁止 remote fetch；未知 raster 回 human review，不得默認通過。
- Reference trust：PubMed client 產生 typed attestation，domain invariant 與 persistence 再驗證；agent/user metadata 與 verified provenance 分層保存。
- 原則：永遠保留原始 bytes/hash；預設只檢測與記錄，不自動移除 watermark 或 provenance。

### Phase Artifact 與外部核准信任 (2026-08-17)

- Phase 2/2.1：reference identity、verified PubMed raw payload、fulltext/Asset-Aware bytes/hash/size/source revision 與分析欄位皆為 code-enforced evidence。
- Phase 3/7：正常 ready/quality-met 路徑由 deterministic gate 決定；例外只接受外部 Ed25519 v3 receipt，信任錨來自 host process env，不來自 workspace。
- Phase 7：review config floor、serialized state、R1-R6 artifacts、evolution events、hash chain 與 current manuscript 全部重算；MCP 不能自行簽核。

### Code Quality 與 VSIX Runtime Authority (2026-08-17)

- `code-quality-authority.json` 對 400 行/file、300 行/class、50 行/function 的既有例外建立 shrink-only ratchet；CI 同時要求 vulture 80%+ 零發現。
- VSIX palette 為 9 commands、2 settings；移除沒有 lifecycle ownership 的 start/stop 與未讀設定。
- uv/uvx 固定 0.12.5；官方 release assets 以平台/架構 SHA-256 allowlist、bounded safe extractor、receipt/binary hash、symlink containment 與 install lease 驗證。

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
    ✅ EvolutionVerifier 跨專案品質趨勢與證據彙整（read-only）
    ❌ L3 建議自動產生 PR (Phase B 未完成)

整合流程：
    tool call → tool_logging → ToolInvocationStore
    → MetaLearningEngine D9 → PendingEvolutionStore
    → build_startup_guidance → 下次對話提示
    → apply_pending_evolutions → 套用/駁回
```

元件：QualityScorecard(8 dims), HookEffectivenessTracker(56 hooks),
MetaLearningEngine(D1-D9), WritingHooksEngine(A5/A6/B8/C9/F),
DomainConstraintEngine(13 output profiles, 110 base constraints),
ToolInvocationStore, PendingEvolutionStore, tool_health

### 狀態管理架構 (2025-01-22 新增)

**三階段狀態機**：

```
┌─────────────┐     save_reference     ┌─────────────┐
│             │      unified_search    │             │
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
