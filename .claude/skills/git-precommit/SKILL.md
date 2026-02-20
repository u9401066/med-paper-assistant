---
name: git-precommit
description: |
  提交前編排器 + Paper-Aware Pre-Commit Hooks。
  LOAD THIS SKILL WHEN: commit、提交、推送、做完了、收工
  CAPABILITIES: 記憶同步、文檔更新、Paper 品質把關、Git 操作
---

# Git 提交前工作流（編排器 + Pre-Commit Hooks）

## 🔔 雙重 Hook 系統定位

```
┌─── Copilot Hooks (寫作時) ───┐  ┌─── Pre-Commit Hooks (提交時) ──┐
│ Agent 在 auto-paper Pipeline │  │ Agent 在 git commit 前檢查      │
│ 即時品質控制（邊寫邊查）     │  │ 最終品質把關（全局總檢查）      │
│ 定義: auto-paper/SKILL.md    │  │ 定義: 本檔案 ← YOU ARE HERE    │
└──────────────────────────────┘  └─────────────────────────────────┘
```

---

## 觸發條件

| 用戶說法 | 觸發 |
|----------|------|
| 準備 commit、要提交了 | ✅ |
| 推送、做完了、收工 | ✅ |
| 快速 commit (--quick) | ✅ 快速模式 |

---

## 執行流程總覽

```
┌─────────────────────────────────────────────────────────┐
│              Git Pre-Commit Orchestrator                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Step 0: 偵測變更範圍                                    │
│    └── 判斷是否觸發 Paper Hooks                          │
│                                                         │
│  ┌─── 通用 Hooks（每次觸發）──────────────────────────┐  │
│  │ G1: memory-sync     [必要] Memory Bank 同步       │  │
│  │ G2: readme-update   [條件] README 更新            │  │
│  │ G3: changelog-update[條件] CHANGELOG 更新         │  │
│  │ G4: roadmap-update  [條件] ROADMAP 更新           │  │
│  │ G5: arch-check      [條件] 架構文檔檢查           │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌─── Paper Hooks（偵測到論文變更時）────────────────┐   │
│  │ P1: citation-integrity   引用完整性              │   │
│  │ P2: anti-ai-scan         Anti-AI 用詞掃描        │   │
│  │ P3: concept-alignment    概念一致性              │   │
│  │ P4: word-count           字數合規                │   │
│  │ P5: protected-content    🔒 保護內容完整          │   │
│  │ P6: memory-sync          專案 .memory/ 已更新     │   │
│  │ P7: reference-integrity  文獻引用完整             │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  Step Final: commit-prepare  [最終] 準備提交             │
└─────────────────────────────────────────────────────────┘
```

---

## Step 0: 偵測變更範圍

```python
# 取得變更檔案
changed_files = get_changed_files()
# 或
run_in_terminal("git diff --cached --name-only")

# 判斷是否包含論文檔案
paper_patterns = [
    "projects/*/drafts/*",
    "projects/*/concept.md",
    "projects/*/references/*",
    "projects/*/.memory/*"
]

trigger_paper_hooks = any(
    file matches pattern
    for file in changed_files
    for pattern in paper_patterns
)
```

---

## 🔧 通用 Hooks（每次觸發）

### G1: memory-sync [必要]

**MCP Tools**：`memory_bank_update_progress`, `memory_bank_update_context`

```python
# 更新全域 Memory Bank
memory_bank_update_progress(
    done=["完成 XXX"],
    doing=[],
    next=["下一步..."]
)

# 如有研究專案變更 → 更新專案 .memory/
mcp_mdpaper_sync_workspace_state(
    doing="Committing changes",
    next_action="..."
)
```

---

### G2: readme-update [條件]

**觸發條件**：新增功能、API 變更
**工具**：`read_file` → `replace_string_in_file`

---

### G3: changelog-update [條件]

**觸發條件**：版本變更、重要修改
**工具**：`read_file` → `replace_string_in_file`

---

### G4: roadmap-update [條件]

**觸發條件**：里程碑完成
**工具**：`read_file` → `replace_string_in_file`

---

### G5: arch-check [條件]

**觸發條件**：結構性程式碼變更
**工具**：`grep_search`, `list_dir`

---

## 📄 Paper Hooks（論文變更時觸發）

> **⚠️ 僅當 Step 0 偵測到論文檔案變更時才觸發**

### P1: citation-integrity（引用完整性）

**目的**：確保所有 `[[wikilinks]]` 能解析到已儲存的文獻

**MCP Tools**：
```python
# 掃描草稿中的所有引用
result = mcp_mdpaper_scan_draft_citations(filename="drafts/manuscript.md")

# 檢查未解析的引用
if result.unresolved_citations:
    # 報告未解析的 wikilinks
    print(f"⚠️ {len(result.unresolved_citations)} unresolved citations")

    # 嘗試自動修復：驗證 wikilink 格式
    mcp_mdpaper_validate_wikilinks()

    # 若仍無法解析 → 警告用戶
```

**判定**：
- ✅ PASS: 0 個未解析引用
- ⚠️ WARN: 有未解析但已知原因
- ❌ FAIL: 有 unknown wikilinks → 阻止提交

---

### P2: anti-ai-scan（Anti-AI 用詞掃描）

**目的**：掃描草稿中的 AI 痕跡用詞

**MCP Tools**：
```python
# 讀取所有已變更的草稿
for draft_file in changed_draft_files:
    content = mcp_mdpaper_read_draft(filename=draft_file)

    # Agent 掃描 Anti-AI 禁止詞清單
    anti_ai_patterns = [
        "In recent years",
        "It is worth noting",
        "plays a crucial role",
        "has garnered significant attention",
        "a comprehensive understanding",
        "This groundbreaking",
        "It is important to note",
        "delve into",
        "shed light on",
        "pave the way",
        "a myriad of",
    ]

    # 檢查並報告
    for pattern in anti_ai_patterns:
        if pattern.lower() in content.lower():
            report(f"⚠️ Anti-AI: Found '{pattern}' in {draft_file}")
```

**判定**：
- ✅ PASS: 0 個 AI 用詞
- ⚠️ WARN: 1-2 個（報告但不阻止）
- ❌ FAIL: ≥3 個 → 建議修正後再提交

---

### P3: concept-alignment（概念一致性）

**目的**：草稿與 concept.md 的核心概念保持一致

**MCP Tools**：
```python
# 讀取 concept
concept = mcp_mdpaper_read_draft(filename="concept.md")

# 提取 🔒 NOVELTY 和 🔒 SELLING POINTS
novelty_keywords = extract_novelty_keywords(concept)
selling_points = extract_selling_points(concept)

# 讀取已變更的草稿
for draft_file in changed_draft_files:
    content = mcp_mdpaper_read_draft(filename=draft_file)

    # Agent 檢查核心概念是否體現
    if "introduction" in draft_file.lower():
        check_novelty_present(content, novelty_keywords)
    if "discussion" in draft_file.lower():
        check_selling_points_present(content, selling_points)
```

**判定**：
- ✅ PASS: 核心概念完整體現
- ⚠️ WARN: 部分概念缺失
- ❌ FAIL: NOVELTY 完全缺失 → 阻止提交

---

### P4: word-count（字數合規）

**目的**：各 section 字數在合理範圍

**MCP Tools**：
```python
for draft_file in changed_draft_files:
    result = mcp_mdpaper_count_words(filename=draft_file)

    # 對照預設字數限制
    limits = {
        "abstract": 350,
        "introduction": 800,
        "methods": 1500,
        "results": 1500,
        "discussion": 1500,
    }

    section_name = extract_section_name(draft_file)
    if section_name in limits and result.words > limits[section_name] * 1.2:
        report(f"⚠️ {section_name}: {result.words} words (limit: {limits[section_name]})")
```

**判定**：
- ✅ PASS: 所有 section 在限制 ±20% 內
- ⚠️ WARN: 超標 20-50%
- ❌ FAIL: 超標 >50%

---

### P5: protected-content（🔒 保護內容完整）

**目的**：確保 `concept.md` 的 🔒 區塊未被刪除或弱化

**MCP Tools**：
```python
# 讀取 concept.md
concept = mcp_mdpaper_read_draft(filename="concept.md")

# 檢查 🔒 區塊存在且非空
checks = [
    ("🔒 NOVELTY STATEMENT", "NOVELTY"),
    ("🔒 KEY SELLING POINTS", "SELLING_POINTS"),
]

for marker, name in checks:
    if marker not in concept:
        report(f"❌ Missing {name} in concept.md!")
    elif is_empty_section(concept, marker):
        report(f"❌ {name} is empty!")
```

**判定**：
- ✅ PASS: 兩個 🔒 區塊都存在且有內容
- ❌ FAIL: 任一缺失 → 阻止提交

---

### P6: project-memory-sync（專案 .memory/ 同步）

**目的**：確保專案的 `.memory/activeContext.md` 已更新

**MCP Tools**：
```python
# 檢查 .memory/ 是否在變更清單中
project_memory_updated = any(
    ".memory/" in f for f in changed_files
)

if not project_memory_updated:
    # 自動更新
    mcp_mdpaper_sync_workspace_state(
        doing="Pre-commit sync",
        next_action="Ready to commit"
    )

    # 確認 activeContext.md 最後更新時間
    report("⚠️ Project .memory/ was not updated. Auto-syncing...")
```

**判定**：
- ✅ PASS: .memory/ 已在變更清單中
- ⚠️ AUTO-FIX: 自動同步後加入暫存

---

### P7: reference-integrity（文獻引用完整）

**目的**：已儲存的文獻都有必要的 metadata

**MCP Tools**：
```python
# 列出所有已儲存的文獻
refs = mcp_mdpaper_list_saved_references()

# 對每個被引用的文獻檢查完整性
for ref in refs.referenced_in_drafts:
    details = mcp_mdpaper_get_reference_details(pmid=ref.pmid)

    if not details.title or not details.authors:
        report(f"⚠️ Reference {ref.pmid} missing metadata")

    if details.trust_level != "VERIFIED":
        report(f"⚠️ Reference {ref.pmid} not verified (was saved via fallback)")
```

**判定**：
- ✅ PASS: 所有引用的文獻都是 🔒 VERIFIED
- ⚠️ WARN: 有 fallback 儲存的文獻（建議重新用 `save_reference_mcp` 驗證）

---

## 🚀 執行模式

### 標準模式（完整檢查）

```
用戶：「準備 commit」

Agent：
  Step 0 → 偵測變更範圍
  G1-G5 → 通用 Hooks
  P1-P7 → Paper Hooks（如適用）
  Final → 準備提交
```

### 快速模式（--quick）

```
用戶：「快速 commit」

Agent：
  G1 → memory-sync（必要）
  P1 → citation-integrity（如有論文變更）
  P5 → protected-content（如有 concept 變更）
  Final → 準備提交
```

### 開發模式（--dev）

```
用戶：「commit code changes」

Agent：
  G1-G5 → 通用 Hooks
  跳過 Paper Hooks
  Final → 準備提交
```

---

## 📋 輸出範例

```
🚀 Git Pre-Commit 工作流

═══ 通用 Hooks ═══
[G1] Memory Bank 同步 ✅
  └─ progress.md: 更新 2 項
[G2] README 更新 ⏭️ (無變更)
[G3] CHANGELOG 更新 ✅
  └─ 添加條目
[G4] ROADMAP 更新 ⏭️
[G5] 架構文檔 ⏭️

═══ Paper Hooks ═══ (偵測到 3 個草稿變更)
[P1] 引用完整性 ✅ (12 citations, 0 unresolved)
[P2] Anti-AI 掃描 ⚠️ (1 warning)
  └─ introduction.md: "It is worth noting" → 建議改寫
[P3] 概念一致性 ✅ (NOVELTY + SELLING POINTS 完整)
[P4] 字數合規 ✅
  └─ Introduction: 520/800 | Methods: 980/1500
[P5] 🔒 保護內容 ✅
[P6] .memory/ 同步 ✅ (auto-synced)
[P7] 文獻完整 ✅ (15 refs, all VERIFIED)

═══ 結果 ═══
✅ 12/12 checks passed (1 warning)

📋 Staged files: 8 files

建議 commit message：
  feat(paper): complete Introduction and Methods sections

準備好了！確認提交？
```

---

## Git 操作工具

| 工具 | 用途 |
|------|------|
| `get_changed_files()` | 取得變更檔案清單 |
| `run_in_terminal("git status")` | 檢查 Git 狀態 |
| `run_in_terminal("git add .")` | 暫存變更 |
| `run_in_terminal("git commit -m '...'")` | 提交 |

**Commit Message 格式**：
```
type(scope): description

Types: feat, fix, docs, refactor, style, test, chore
Scope: paper, concept, refs, export, core
```

---

## Skill 依賴

| 編排的 Skill | 工具 | 在哪個 Hook |
|-------------|------|-------------|
| memory-updater | `memory_bank_update_progress` | G1 |
| readme-updater | `read_file`, `replace_string_in_file` | G2 |
| changelog-updater | `read_file`, `replace_string_in_file` | G3 |
| roadmap-updater | `read_file`, `replace_string_in_file` | G4 |
| ddd-architect | `grep_search`, `list_dir` | G5 |
| draft-writing | `read_draft`, `count_words`, `validate_wikilinks` | P1-P4 |
| reference-management | `list_saved_references`, `get_reference_details` | P7 |
| concept-development | `read_draft("concept.md")` | P3, P5 |

---

## 與 Copilot Hooks 的關係

| 面向 | Copilot Hooks | Pre-Commit Hooks |
|------|---------------|------------------|
| **誰定義** | `auto-paper/SKILL.md` | 本 SKILL（`git-precommit`） |
| **何時觸發** | 寫作過程中（每次 write/patch） | `git commit` 前 |
| **檢查粒度** | 單個 section | 所有已變更檔案 |
| **自動修復** | ✅ 自動 `patch_draft` | ⚠️ 只報告，不自動修改 |
| **目的** | 即時品質控制 | 最終品質把關 |
| **互補性** | 處理寫作細節 | 處理全局一致性 |

**💡 理想情況**：如果 Copilot Hooks 在 auto-paper pipeline 中都正確執行，
Pre-Commit Hooks 應該全部 PASS（因為問題已在寫作時修正）。
Pre-Commit Hooks 是 **safety net**，捕捉 Copilot Hooks 可能遺漏的問題。
