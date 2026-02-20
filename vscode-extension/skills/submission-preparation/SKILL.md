# Submission Preparation Skill

## 觸發語

投稿準備、cover letter、highlights、reviewer response、投稿信、回覆審稿、revision、修改回覆、投稿 checklist

## 概述

協助準備期刊投稿所需文件：cover letter、highlights、reviewer response、revision formatting。
此 Skill 不使用 MCP 工具 — Agent 直接按模板生成內容。

---

## 📚 支援期刊及投稿要求

| 代碼             | 期刊名稱                        | 字數限制 (Original) | Abstract         | References | Figures | Tables | Keywords |
| ---------------- | ------------------------------- | ------------------- | ---------------- | ---------- | ------- | ------ | -------- |
| `bja`            | British Journal of Anaesthesia  | 3500                | 250              | 40         | 6       | 5      | 6 MeSH   |
| `anesthesiology` | Anesthesiology                  | 4500                | 300 (structured) | 50         | 6       | 5      | 3-6      |
| `aa`             | Anesthesia & Analgesia          | 3500                | 400              | 35         | 6       | 5      | 3-6      |
| `jama`           | JAMA                            | 3000                | 350 (structured) | 40         | 4       | 4      | 3-10     |
| `nejm`           | New England Journal of Medicine | 2500                | 250              | 40         | 4       | 4      | None     |
| `lancet`         | The Lancet                      | 3500                | 300              | 30         | 5       | 5      | None     |
| `ccm`            | Critical Care Medicine          | 3000                | 250              | 50         | 6       | 5      | 3-5      |
| `generic`        | Generic (fallback)              | 4000                | 300              | 50         | 6       | 5      | 3-6      |

### 各期刊必要文件

| 期刊           | Cover Letter | Highlights | Graphical Abstract | ORCID                  |
| -------------- | ------------ | ---------- | ------------------ | ---------------------- |
| BJA            | ✅           | ❌         | ❌                 | Corresponding required |
| Anesthesiology | ✅           | ❌         | ❌                 | All authors            |
| A&A            | ✅           | ❌         | ❌                 | Optional               |
| JAMA           | ✅           | ❌         | ❌                 | Optional               |
| NEJM           | ✅           | ❌         | ❌                 | Optional               |
| Lancet         | ✅           | ❌         | ❌                 | Optional               |
| CCM            | ✅           | ❌         | ❌                 | Optional               |

> 所有期刊都要求: Author Contributions, COI Statement, Ethics Statement, Data Availability

---

## ✉️ Cover Letter 模板

### 結構

```markdown
Dear Editor,

We are pleased to submit our manuscript entitled **"[TITLE]"** for consideration
for publication in _[JOURNAL NAME]_.

**Key Highlights of This Study:**

1. [Novelty point 1]
2. [Novelty point 2]
3. [Novelty point 3]

This manuscript has not been published elsewhere and is not under consideration
by another journal. All authors have approved the manuscript and agree with its
submission to _[JOURNAL NAME]_.

[Author Contributions statement — if required by journal]

[COI statement — if required by journal]

[Ethics statement — if required by journal]

[Data Availability statement — if required by journal]

**Suggested Reviewers:** (if applicable)

- [Name; Affiliation; Email]

**Reviewers to Exclude:** (if applicable)

- [Name; Reason]

We believe this manuscript is well suited for _[JOURNAL NAME]_ and will be of
interest to your readers. Thank you for considering our submission.

Sincerely,

[Corresponding Author]
(On behalf of all authors)

---

**Corresponding Author:**
[Name]
[Institution]
[Address]
[Email]
[Phone]
[ORCID: https://orcid.org/0000-0000-0000-0000]
```

### 生成規則

1. 從 concept.md 取得 title 和 novelty points
2. 根據目標期刊加入必要的 statements
3. 替換所有 `[PLACEHOLDER]` 並提醒用戶填入實際資訊
4. Ethics approval number 必須由用戶提供

---

## ✨ Highlights 格式

### 規則

- 3-5 個 bullet points
- 每條 ≤ 125 字元
- 第一條放 novelty/innovation
- 最後一條放 clinical impact
- 用 `•` 開頭

### 範例

```
• First study to demonstrate [specific finding] in [population]
• [Key methodology or approach used]
• [Main quantitative finding with effect size]
• [Secondary finding or subgroup analysis]
• [Clinical implication or practice change]
```

---

## 📝 Reviewer Response 格式

### Format 1: Structured (推薦)

```markdown
# Response to Reviewers

_Thank you for the opportunity to revise our manuscript.
Below we provide point-by-point responses to each comment._

---

## Response to Reviewer 1

### Comment 1

> [Original reviewer comment]

**Response:**

[Your detailed response]

**Changes made:**

[Describe changes with page/line numbers, or 'No changes made']

---

### Comment 2

> [Original reviewer comment]

**Response:**

[Your detailed response]

**Changes made:**

[Changes description]

---

## Summary of Changes

| Section      | Change                | Location          |
| ------------ | --------------------- | ----------------- |
| Introduction | Added paragraph on... | Page X, Lines Y-Z |
| Methods      | Clarified...          | Page X, Lines Y-Z |
```

### Format 2: Table

```markdown
# Response to Reviewers

## Reviewer 1

| #   | Comment   | Response   | Changes Made |
| --- | --------- | ---------- | ------------ |
| 1   | [Comment] | [Response] | [Changes]    |
| 2   | [Comment] | [Response] | [Changes]    |
```

### Format 3: Letter

```markdown
# Response to Reviewers

[Date]

Dear Editor,

Thank you for the opportunity to revise our manuscript titled
"[MANUSCRIPT TITLE]" (Manuscript ID: [ID]).

We have carefully considered all reviewer comments and have revised
the manuscript accordingly. Below we provide detailed responses to each point.

**Reviewer 1:**

_Comment 1: "[comment text]"_

Response: [Your response here]

...

Sincerely,

[Corresponding Author]
```

### Reviewer Comment 解析規則

- 尋找 `Reviewer #N:` 或 `Rev. N:` 作為 reviewer 分隔
- 尋找 `1.` / `2.` / `-` / `•` 作為 comment 分隔
- 續行文字（無特殊開頭）append 到前一個 comment

---

## 📐 Revision Change Formatting

標記修改處的標準格式：

```markdown
**Changes made:**

_Location: Page 5, Lines 120-125_

~~Original:~~

> [Original text before revision]

**Revised:**

> [Revised text after changes]
```

---

## 🔄 工作流程

### 投稿準備

1. 確認目標期刊 → 查上方期刊要求表
2. 生成 Cover Letter → 用 concept.md 的 title + novelty
3. 生成 Highlights → 如果期刊要求
4. 執行 `check_formatting(check_submission=True)` → 投稿 checklist

### Revision 回覆

1. 用戶貼上 reviewer comments
2. 選擇格式 (structured/table/letter)
3. 生成 response template
4. 對每個修改處用 revision change formatting
5. 填入 Summary of Changes table
