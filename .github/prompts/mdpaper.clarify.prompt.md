---
description: "✨ mdpaper.clarify - 改進與潤飾內容"
---

# 改進與潤飾內容

## Step 1: 列出可用草稿

```
mcp_mdpaper_list_drafts()
```

詢問用戶要改進哪個 draft。

---

## Step 2: 讀取草稿

```
mcp_mdpaper_read_draft(filename="drafts/introduction.md")
```

---

## Step 3: 確認改進方向

詢問用戶需要哪種改進：

| 類型 | 說明 |
|------|------|
| 文法潤飾 | 修正文法、改善流暢度 |
| 邏輯強化 | 加強論述邏輯連貫性 |
| 學術語調 | 調整為更正式的學術寫作風格 |
| 精簡內容 | 縮減字數、去除冗贅 |
| 擴充內容 | 增加細節、補充說明 |
| 引用整合 | 更好地整合文獻引用 |

---

## Step 4: 執行改進

**⚠️ 尊重 🔒 受保護區塊！**

修改前確認：
- 🔒 NOVELTY STATEMENT 是否需要保留？
- 🔒 KEY SELLING POINTS 是否需要保留？

如需修改 🔒 區塊，必須先詢問用戶。

---

## Step 5: 儲存改進版本

```
mcp_mdpaper_write_draft(filename="drafts/introduction_v2.md", content="...")
```

或覆蓋原檔：
```
mcp_mdpaper_write_draft(filename="drafts/introduction.md", content="...")
```

---

## 📋 完成檢查

- [ ] 草稿已讀取
- [ ] 改進方向已確認
- [ ] 🔒 區塊已尊重
- [ ] 改進版本已儲存
