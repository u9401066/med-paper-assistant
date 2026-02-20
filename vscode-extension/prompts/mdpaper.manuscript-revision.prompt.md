---
description: "📝 manuscript-revision - 稿件修改與回覆審稿意見"
---

# 稿件修改與回覆審稿意見

📖 **Capability 類型**: 高層編排
📖 **編排 Skills**: draft-writing → concept-validation → word-export

---

## 🎯 此 Capability 的目標

處理期刊審稿意見，系統性地：

1. 分析 reviewer comments
2. 逐項回應並修改稿件
3. 撰寫 response letter
4. 匯出修改後文件

---

## Phase 1: 分析審稿意見 `analyze`

### Step 1.1: 收集審稿意見

```
詢問用戶：
1. 請提供 reviewer comments（貼上或上傳）
2. 是 major revision 還是 minor revision？
3. 有幾位 reviewer？
```

### Step 1.2: 結構化分析

```
將每個 comment 分類：

| Comment | 類型 | 難度 | 需要 |
|---------|------|------|------|
| #1 | 方法質疑 | 高 | 補充分析 |
| #2 | 文獻補充 | 中 | 新增引用 |
| #3 | 語言潤飾 | 低 | 文字修改 |
```

### Step 1.3: 優先級排序

```
建議處理順序：
1. 高難度/核心問題 → 先確認能否解決
2. 中難度 → 逐項處理
3. 低難度 → 最後統一處理
```

---

## Phase 2: 逐項回應 `respond`

📖 Skill: `.claude/skills/draft-writing/SKILL.md`

### Step 2.1: 建立 response template

```markdown
# Response to Reviewers

## Reviewer 1

### Comment 1.1

> [原始 comment]

**Response:**
[回應內容]

**Changes made:**

- Page X, Line Y: [具體修改]

---
```

### Step 2.2: 處理每個 comment

```
對於每個 comment：

1. 確認理解
   「Reviewer 說 X，您理解是 Y 嗎？」

2. 討論回應策略
   「建議回應方式：A / B / C」

3. 執行修改
   mcp_mdpaper_read_draft(filename="...")
   mcp_mdpaper_write_draft(filename="...", content="修改後內容")

4. 記錄修改位置
   「Page X, Line Y-Z: 已修改為...」
```

---

## Phase 3: 補充分析（如需要）`supplement`

### 如果需要補充文獻

```
mcp_pubmed-search_search_literature(query="reviewer 提到的主題")
mcp_mdpaper_save_reference_mcp(pmid="...", agent_notes="補充給 reviewer")
```

### 如果需要補充分析

```
討論：
- 是否有現有數據可以回答？
- 需要重新分析嗎？
- 如何呈現補充結果？
```

---

## Phase 4: 驗證修改 `validate`

📖 Skill: `.claude/skills/concept-validation/SKILL.md`

### Step 4.1: 確保 🔒 受保護內容完整

```
mcp_mdpaper_validate_concept(filename="concept.md")

檢查：
- 🔒 NOVELTY STATEMENT 是否被弱化？
- 🔒 KEY SELLING POINTS 是否全部保留？
```

### Step 4.2: 確認一致性

```
確認所有修改不互相矛盾：
- Introduction 的聲明 vs Methods 的描述
- Results 的數據 vs Discussion 的解釋
```

---

## Phase 5: 匯出文件 `export`

📖 Skill: `.claude/skills/word-export/SKILL.md`

### Step 5.1: 匯出修改後稿件

```
# 使用 track changes 或 highlight 標記修改處

mcp_mdpaper_start_document_session(template_name="...", session_id="revision")
# ... 插入各章節 ...
mcp_mdpaper_save_document(session_id="revision", output_filename="manuscript_R1.docx")
```

### Step 5.2: 匯出 Response Letter

```
Response letter 包含：
1. Cover letter（感謝 reviewer）
2. Point-by-point response
3. 修改摘要

儲存為：response_to_reviewers.docx
```

---

## 📋 完成檢查

- [ ] 所有 reviewer comments 已分類
- [ ] 每個 comment 有對應回應
- [ ] 修改位置已標記（Page/Line）
- [ ] 🔒 受保護內容未被弱化
- [ ] 修改後稿件已匯出
- [ ] Response letter 已完成

---

## 💡 常見回應策略

### 同意並修改

```
Thank you for this valuable suggestion. We have revised
the manuscript accordingly. [具體說明修改內容]
```

### 部分同意

```
We appreciate this comment. While we agree that [X],
we believe [Y] because [原因]. However, we have added
[補充說明] to address this concern.
```

### 不同意但尊重

```
We thank the reviewer for raising this point. We
respectfully disagree because [有力證據]. However,
we have added a discussion of this limitation in
the Discussion section (Page X, Lines Y-Z).
```

---

## ⚠️ 注意事項

1. **不要刪除關鍵內容** - 即使 reviewer 質疑
2. **保持禮貌** - 即使 reviewer 誤解
3. **具體回應** - 避免「已修改」這種模糊回覆
4. **標記所有修改** - 讓 reviewer 容易找到
