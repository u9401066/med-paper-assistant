# Submission Preparation Skill

觸發：投稿準備、cover letter、highlights、reviewer response、revision、投稿 checklist

不使用 MCP 工具 — Agent 直接按模板生成內容。

---

## 支援期刊

| 代碼           | 期刊                   | 字數 | Abstract         | Refs | Figs | Tables |
| -------------- | ---------------------- | ---- | ---------------- | ---- | ---- | ------ |
| bja            | British J Anaesthesia  | 3500 | 250              | 40   | 6    | 5      |
| anesthesiology | Anesthesiology         | 4500 | 300 (structured) | 50   | 6    | 5      |
| aa             | Anesthesia & Analgesia | 3500 | 400              | 35   | 6    | 5      |
| jama           | JAMA                   | 3000 | 350 (structured) | 40   | 4    | 4      |
| nejm           | NEJM                   | 2500 | 250              | 40   | 4    | 4      |
| lancet         | Lancet                 | 3500 | 300              | 30   | 5    | 5      |
| ccm            | Critical Care Medicine | 3000 | 250              | 50   | 6    | 5      |
| generic        | Generic                | 4000 | 300              | 50   | 6    | 5      |

所有期刊都要求：Author Contributions, COI Statement, Ethics Statement, Data Availability

---

## Cover Letter

結構：Dear Editor → Title → 3 Key Highlights (from concept.md novelty) → Not published elsewhere → Statements (per journal) → Suggested Reviewers → Corresponding Author + ORCID

生成規則：從 concept.md 取 title + novelty。不要遺留 `[PLACEHOLDER]`。Ethics number 由用戶提供。

---

## Highlights

- 3-5 bullets, 每條 ≤125 chars
- 第一條 = novelty/innovation, 最後一條 = clinical impact

---

## Reviewer Response

| 格式               | 適用                                            |
| ------------------ | ----------------------------------------------- |
| Structured（推薦） | > Comment → Response → Changes made (page/line) |
| Table              | # / Comment / Response / Changes                |
| Letter             | 正式書信體                                      |

Comment 解析：`Reviewer #N:` 分隔 reviewer，`1.` / `-` / `•` 分隔 comments。

Revision Change Format：Location + ~~Original~~ + **Revised** + Summary of Changes table

---

## 工作流

### 投稿準備

1. 確認目標期刊 → 查上方要求
2. Cover Letter → concept.md title + novelty
3. Highlights → 如期刊要求
4. `check_formatting(check_submission=True)` → checklist

### Revision 回覆

1. 用戶貼 reviewer comments
2. 選格式 → 生成 template
3. 用 revision change format 標記修改
