# Citation Tools Architecture Design

## 目標

建立完整的引用管理系統，支援：

1. 儲存參考文獻（Foam 整合）
2. 在草稿中插入/管理引用
3. 智慧引用建議（為某句話找文獻）
4. 整篇文章自動引用

---

## 1. 檔案結構設計

### 單一 Markdown 檔案方案

```
references/
└── {pmid}/
    └── {citation_key}.md   ← 唯一檔案，包含所有資訊
```

### Markdown 檔案格式

```yaml
---
# ========== Foam 連結 ==========
aliases:
  - greer2017_27345583 # 主要引用 key
  - "PMID:27345583" # PMID 格式
  - "27345583" # 純數字
type: reference

# ========== 書目資訊 ==========
pmid: "27345583"
doi: "10.1002/lary.26134"
pmc: null # PMC ID (如果有)
year: 2017
title: "Review of videolaryngoscopy pharyngeal wall injuries"

# ========== 作者 ==========
authors: ["Greer D", "Marshall KE", "Bevans S"]
first_author: "Greer"
authors_full:
  - { last: "Greer", first: "Devon", initials: "D" }
  - { last: "Marshall", first: "Kathryn E", initials: "KE" }

# ========== 期刊 ==========
journal: "The Laryngoscope"
journal_abbrev: "Laryngoscope"
volume: "127"
issue: "2"
pages: "349-353"

# ========== 預格式化引用 (重要！) ==========
cite:
  vancouver: "Greer D, Marshall KE, et al. Review... Laryngoscope. 2017;127(2):349-353."
  apa: "Greer, D., Marshall, K. E., et al. (2017). Review... *The Laryngoscope*, *127*(2), 349-353."
  nature: "Greer D, et al. *Laryngoscope* **127**, 349-353 (2017)."
  inline: "(Greer et al., 2017)"
  number: null # 待分配的數字編號

# ========== 語意搜尋索引 ==========
keywords: ["GlideScope", "Laryngoscopy", "injury"]
mesh_terms: ["Intubation, Intratracheal", "Laryngoscopy"]
abstract_embedding: null # 未來：向量嵌入

# ========== 元資料 ==========
saved_at: "2025-12-17T18:40:00"
source: pubmed # pubmed | zotero | doi | manual
has_pdf: false
pdf_path: null
---
```

### 為什麼用 YAML 而不是 JSON？

| 特性      | YAML in Frontmatter | 獨立 JSON       |
| --------- | ------------------- | --------------- |
| Foam 相容 | ✅ 原生支援         | ❌ 需要額外處理 |
| 人類可讀  | ✅ 易讀易改         | ⚠️ 較難閱讀     |
| 程式解析  | ✅ 標準格式         | ✅ 標準格式     |
| 版本控制  | ✅ 差異易讀         | ⚠️ 差異較亂     |
| IDE 支援  | ✅ 語法高亮         | ✅ 語法高亮     |

---

## 2. 引用工具設計

### 2.1 基礎工具

#### `insert_citation` - 插入引用

```python
@mcp.tool()
def insert_citation(
    filename: str,           # 草稿檔案
    target_text: str,        # 要加引用的文字（定位用）
    pmid: str,               # 或 citation_key
    position: str = "after"  # before | after | replace
) -> str:
    """
    在指定文字後插入引用標記。

    Example:
        insert_citation(
            filename="introduction.md",
            target_text="Video laryngoscopy has higher injury rates",
            pmid="27345583"
        )

    Result:
        "Video laryngoscopy has higher injury rates [PMID:27345583]."
        或
        "Video laryngoscopy has higher injury rates [[greer2017_27345583]]."
    """
```

#### `update_citation_numbers` - 重新編號

```python
@mcp.tool()
def update_citation_numbers(
    filename: str,
    style: str = "numbered"  # numbered | author-year | superscript
) -> str:
    """
    重新編號草稿中的所有引用。

    [PMID:27345583] → [1]
    [PMID:26391674] → [2]

    同時更新 references 的 cite.number 欄位。
    """
```

#### `list_citations_in_draft` - 列出引用

```python
@mcp.tool()
def list_citations_in_draft(filename: str) -> str:
    """
    列出草稿中所有引用及其位置。

    Returns:
        | # | Citation Key | Position | Context |
        |---|--------------|----------|---------|
        | 1 | greer2017_27345583 | L23 | "...higher injury rates [1]..." |
        | 2 | mourao2015_26391674 | L45 | "...soft tissue trauma [2]..." |
    """
```

### 2.2 智慧工具

#### `find_citation_for_claim` - 為聲明找引用 🔥

```python
@mcp.tool()
def find_citation_for_claim(
    claim: str,              # 要支持的聲明
    search_scope: str = "local",  # local | pubmed | both
    max_results: int = 5
) -> str:
    """
    為給定的聲明找到支持的文獻。

    Example:
        find_citation_for_claim(
            claim="Video laryngoscopy causes more pharyngeal injuries than direct laryngoscopy"
        )

    Process:
        1. 從 claim 提取關鍵概念
        2. 搜尋本地 references (語意匹配 abstract/title)
        3. 如果本地不夠，搜尋 PubMed
        4. 排序並返回最相關的

    Returns:
        📖 Found 3 supporting references:

        1. [[greer2017_27345583]] (Relevance: 95%)
           "Our data suggests video-assisted laryngoscopy puts patients
            at significantly greater risk for injury..."

        2. [[mourao2015_26391674]] (Relevance: 72%)
           "Soft tissue trauma was observed in 52.1% of patients..."
    """
```

#### `auto_cite_draft` - 自動引用整篇草稿 🔥🔥

```python
@mcp.tool()
def auto_cite_draft(
    filename: str,
    citation_density: str = "moderate",  # minimal | moderate | thorough
    require_confirmation: bool = True
) -> str:
    """
    自動為整篇草稿建議引用位置。

    Process:
        1. 解析草稿，識別 claims/statements
        2. 對每個 claim 執行 find_citation_for_claim
        3. 產生建議報告
        4. (可選) 自動插入或等待確認

    Returns:
        📝 Auto-Citation Report for introduction.md

        Found 8 statements that may need citations:

        ✅ Already cited (3):
        - L12: "Dental injuries occur in 0.02-0.07%..." [mourao2015]

        ⚠️ Needs citation (5):
        - L23: "Video laryngoscopy has become increasingly popular"
          → Suggested: [[greer2017_27345583]] (95% match)
          → Alternative: [[pacheco2014_24891204]] (78% match)

        - L34: "The GlideScope is the most commonly used device"
          → No local match. Search PubMed? [Y/n]

        Apply all suggestions? [Y/n/selective]
    """
```

#### `verify_citations` - 驗證引用 🔥

```python
@mcp.tool()
def verify_citations(filename: str) -> str:
    """
    驗證草稿中的引用是否真的支持相關聲明。

    Returns:
        🔍 Citation Verification Report

        ✅ Verified (4):
        - L23: "higher injury rates" ← [[greer2017]] supports this

        ⚠️ Weak support (1):
        - L45: "50% of patients experience trauma"
          ← [[mourao2015]] says 52.1%, consider updating text

        ❌ Potentially unsupported (1):
        - L67: "LMA causes fewer injuries than ETT"
          ← [[greer2017]] doesn't discuss LMA, find better citation?
    """
```

### 2.3 格式化工具

#### `format_reference_list` - 格式化參考文獻列表

```python
@mcp.tool()
def format_reference_list(
    filename: str,           # 草稿檔案
    style: str = "vancouver",
    output: str = "append"   # append | separate | clipboard
) -> str:
    """
    根據草稿中的引用，產生格式化的參考文獻列表。

    Returns:
        ## References

        1. Greer D, Marshall KE, Bevans S, et al. Review of videolaryngoscopy
           pharyngeal wall injuries. Laryngoscope. 2017;127(2):349-353.
           doi:10.1002/lary.26134

        2. Mourão J, Moreira J, Barbosa J, et al. Soft tissue injuries after
           direct laryngoscopy. J Clin Anesth. 2015;27(8):668-71.
           doi:10.1016/j.jclinane.2015.07.009
    """
```

---

## 3. 實作優先順序

### Phase 1: 基礎設施 (現在)

- [x] save_reference - 儲存參考文獻
- [ ] **重構檔案結構** - 單一 .md 檔案 + 豐富 frontmatter
- [ ] insert_citation - 基本插入

### Phase 2: 引用管理 (近期)

- [ ] list_citations_in_draft
- [ ] update_citation_numbers
- [ ] format_reference_list

### Phase 3: 智慧引用 (未來)

- [ ] find_citation_for_claim (需要語意搜尋)
- [ ] auto_cite_draft
- [ ] verify_citations

### Phase 4: 進階功能 (遠期)

- [ ] 向量嵌入 (abstract embedding)
- [ ] 跨文獻知識圖譜
- [ ] AI 輔助引用建議

---

## 4. 引用標記格式

### 草稿中的引用標記

支援多種格式，自動轉換：

| 格式          | 範例                     | 說明              |
| ------------- | ------------------------ | ----------------- |
| Foam wikilink | `[[greer2017_27345583]]` | 最推薦，Foam 原生 |
| PMID 標記     | `[PMID:27345583]`        | 匯出時轉換        |
| 數字編號      | `[1]`                    | 最終輸出格式      |
| 行內引用      | `(Greer et al., 2017)`   | Author-year style |

### 轉換流程

```
Writing Phase:
  [[greer2017_27345583]] ← Foam hover preview

Export Phase:
  → [1] (Vancouver)
  → (Greer et al., 2017) (APA)
  → ¹ (Nature superscript)
```

---

## 5. 與 Foam 的整合

### Foam 功能利用

| Foam 功能       | 用途                     |
| --------------- | ------------------------ |
| `[[wikilinks]]` | 引用連結                 |
| Hover preview   | 快速查看文獻             |
| Backlinks       | 查看哪些草稿引用了某文獻 |
| Graph view      | 視覺化引用網絡           |
| Daily notes     | 研究日誌                 |

### 設定建議 (.vscode/settings.json)

```json
{
  "foam.files.ignore": ["**/node_modules/**", "**/.git/**"],
  "foam.graph.style": {
    "reference": {
      "color": "#4CAF50",
      "shape": "circle"
    }
  },
  "foam.links.hover.enable": true,
  "foam.preview.embedNoteStyle": "full"
}
```

---

## 6. 範例工作流程

### 寫作時引用

```markdown
# Introduction

Video laryngoscopy has become increasingly popular in clinical practice.
However, recent studies suggest that it may cause more pharyngeal injuries
than traditional direct laryngoscopy [[greer2017_27345583]].

In a prospective study of 534 patients, soft tissue trauma was observed
in over half of cases using direct laryngoscopy [[mourao2015_26391674]].
```

### 匯出時

```markdown
# Introduction

Video laryngoscopy has become increasingly popular in clinical practice.
However, recent studies suggest that it may cause more pharyngeal injuries
than traditional direct laryngoscopy [1].

In a prospective study of 534 patients, soft tissue trauma was observed
in over half of cases using direct laryngoscopy [2].

---

## References

1. Greer D, Marshall KE, Bevans S, et al. Review of videolaryngoscopy
   pharyngeal wall injuries. Laryngoscope. 2017;127(2):349-353.

2. Mourão J, Moreira J, Barbosa J, et al. Soft tissue injuries after
   direct laryngoscopy. J Clin Anesth. 2015;27(8):668-71.
```
