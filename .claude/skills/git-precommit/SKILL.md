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
│  │ G6: project-integrity[條件] 專案自我一致性審計    │  │
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
│  │ P8: methodology-validation  方法學可再現性 [NEW]  │   │
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

### G6: project-integrity [條件] — 專案閉環進化

> **CONSTITUTION §22 延伸**：專案本身也應該可審計、可拆解、可重組。
> Hook D 改進論文 + Hook 自身，G6 則確保專案文檔的自我一致性。

**觸發條件**：`SKILL.md`、`AGENTS.md`、`_capability-index.md`、`ARCHITECTURE.md`、`README.md`、`src/` 工具定義有變更

**檢查項目**：

| # | 檢查項 | 方法 | 失敗行為 |
|---|--------|------|----------|
| G6.1 | Tool 數量一致 | `grep -c "mcp.tool"` vs README/ARCHITECTURE 宣稱的數字 | ⚠️ 報告差異，建議更新 |
| G6.2 | Skill 數量一致 | `ls -d .claude/skills/*/` vs AGENTS.md 表格行數 | ⚠️ 報告缺漏的 Skill |
| G6.3 | Prompt 數量一致 | `ls .github/prompts/*.prompt.md` vs 文檔宣稱的數字 | ⚠️ 報告差異 |
| G6.4 | Hook 引用工具存在 | 掃描 SKILL.md 中的 `mcp_mdpaper_*` → 確認 tool 已註冊 | ❌ FAIL：引用了已廢棄工具 |
| G6.5 | 跨文件數字一致 | README vs ARCHITECTURE vs AGENTS vs _capability-index | ⚠️ 報告不一致 |

**執行邏輯**：

```bash
# G6.1: 計算實際 tool 數量
actual_tools=$(grep -r "mcp.tool" src/med_paper_assistant/interfaces/mcp/tools/ --include="*.py" -l | \
  xargs grep -c "@mcp.tool" | grep -v ":0" | awk -F: '{s+=$2} END {print s}')

# G6.2: 計算實際 skill 數量
actual_skills=$(ls -d .claude/skills/*/ | wc -l)

# G6.3: 計算實際 prompt 數量
actual_prompts=$(ls .github/prompts/*.prompt.md | wc -l)

# G6.4: 檢查 Hook 中引用的 tool 是否存在
grep -oP 'mcp_mdpaper_\w+' .claude/skills/auto-paper/SKILL.md | sort -u | while read tool; do
  tool_name=$(echo "$tool" | sed 's/mcp_mdpaper_//')
  if ! grep -rq "@mcp.tool.*$tool_name\|def $tool_name" src/; then
    echo "❌ Hook 引用了不存在的工具: $tool"
  fi
done

# G6.5: 比對各文件數字
readme_tools=$(grep -oP '\d+ tools' README.md | head -1)
arch_tools=$(grep -oP '\d+ 個 tools' ARCHITECTURE.md | head -1)
# 比對並報告差異
```

**報告格式**：

```
[G6] 專案一致性審計
  G6.1 Tool 數量: 實際 53 | README 53 | ARCHITECTURE 53 ✅
  G6.2 Skill 數量: 實際 26 | AGENTS 26 ✅
  G6.3 Prompt 數量: 實際 15 | README 15 ✅
  G6.4 Hook 工具引用: 全部存在 ✅
  G6.5 跨文件一致性: 全部一致 ✅

  → 專案健康度: ✅ 一致
```

**失敗時行為**：
- G6.1-G6.3, G6.5: ⚠️ WARN — 報告差異，列出需更新的文件和正確數字，不阻止提交
- G6.4: ❌ FAIL — Hook 引用了不存在的工具會導致 Pipeline 執行時崩潰，阻止提交

**自我改進閉環**：
```
G6 發現不一致 → 報告問題 → Agent 或用戶修正 → 下次 G6 驗證修正
                    ↑                               │
                    └───────────────────────────────┘
                          專案本身的閉環進化
```

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

### P8: methodology-validation（方法學驗證）

> **CONSTITUTION §21**：Methods 必須可被第三方重現。

**目的**：確保 Methods section 的方法學描述具備可再現性

**觸發條件**：Methods 或 Discussion 草稿有變更

**MCP Tools**：
```python
# 讀取 concept → 確認 paper_type
concept = mcp_mdpaper_read_draft(filename="concept.md")
paper_type = extract_paper_type(concept)  # original-research, case-report, etc.

# 讀取 Methods 草稿
methods = mcp_mdpaper_read_draft(filename="drafts/methods.md")

# 讀取 Discussion（檢查限制段落）
discussion = mcp_mdpaper_read_draft(filename="drafts/discussion.md")

# Agent 依 paper_type 執行方法學 checklist
checklist = {
    "original-research": [
        ("研究設計明確描述", methods),
        ("主要結局定義", methods),
        ("統計方法匹配設計", methods),
        ("倫理審查聲明", methods),
        ("Discussion 有限制段落", discussion),
    ],
    "case-report": [
        ("病例描述完整", methods),
        ("倫理/知情同意", methods),
        ("Discussion 有限制段落", discussion),
    ],
    "systematic-review": [
        ("搜尋策略描述", methods),
        ("納入排除標準", methods),
        ("PRISMA 流程", methods),
        ("Discussion 有限制段落", discussion),
    ],
}

# 逐項評估
for item, source in checklist.get(paper_type, []):
    score = agent_evaluate(item, source)  # 0-10
    report(f"  {item}: {score}/10")
```

**判定**：
- ✅ PASS: 所有項目 ≥ 5 分
- ⚠️ WARN: 有項目 3-5 分（報告但不阻止）
- ❌ FAIL: 有項目 < 3 分（建議修正後再提交）

**與 Copilot Hook B5 的關係**：
- B5 在寫作時即時檢查並自動修正
- P8 在提交時做最終確認（safety net）
- P8 只報告不修改，由用戶決定是否要回去修正

---

## 📊 Hook 效能追蹤（Self-Improving Hooks）

> **CONSTITUTION §23**：Hook 必須追蹤自身效能並自我改進。

每次 Pre-Commit 執行後，在 `projects/{slug}/.audit/precommit-stats.md` 記錄：

```markdown
# Pre-Commit Hook Statistics

## 歷史統計（最近 N 次提交）
| Hook | 執行次數 | 通過率 | 警告率 | 阻止率 | 趨勢 |
|------|---------|--------|--------|--------|------|
| P1 citation | 5 | 80% | 20% | 0% | → |
| P2 anti_ai | 5 | 60% | 40% | 0% | ↓ 需注意 |
| P3 concept | 5 | 100% | 0% | 0% | → |
| P8 methodology | 2 | 50% | 50% | 0% | 新 Hook |

## 自動調整紀錄
| 日期 | Hook | 調整 | 原因 |
|------|------|------|------|
| 2026-02-20 | P2 | 移除 'comprehensive' | 連續 3 次誤報 |
| 2026-02-21 | P4 | Discussion 限制 1500→1650 | 觀察性研究需更長 |
```

**效能判斷規則**：
- Hook 通過率 >95%（5 次以上）→ 考慮是否太鬆
- Hook 阻止率 >50%（5 次以上）→ 考慮是否太嚴
- 記錄到 `.audit/` 供 auto-paper Hook D 分析

---

## 🚀 執行模式

### 標準模式（完整檢查）

```
用戶：「準備 commit」

Agent：
  Step 0 → 偵測變更範圍
  G1-G6 → 通用 Hooks
  P1-P8 → Paper Hooks（如適用）
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
  G1-G6 → 通用 Hooks
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
[G6] 專案一致性 ✅
  └─ Tools: 53 | Skills: 26 | Prompts: 15 | 全部一致

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
[P8] 方法學驗證 ✅
  └─ 研究設計: 8/10 | 統計方法: 7/10 | 限制段落: 9/10

═══ 結果 ═══
✅ 13/13 checks passed (1 warning)

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
| concept-development | `read_draft("concept.md")` | P3, P5, P8 |

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
