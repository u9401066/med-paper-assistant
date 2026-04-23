---
description: "📝 manuscript-revision - 稿件修改與回覆審稿意見"
---

# 稿件修改與回覆審稿意見

編排：draft-writing → concept-validation → word-export

## Phase 1: 分析審稿意見

問用戶：reviewer comments、major/minor revision、幾位 reviewer

分類每個 comment：類型（方法質疑/文獻補充/語言潤飾）、難度（高/中/低）

順序：高難度核心問題 → 中 → 低

## Phase 2: 逐項回應

Response template 格式：> Comment → **Response** → **Changes made** (Page X, Line Y)

每個 comment：確認理解 → 討論策略 → `read_draft` + `write_draft` 修改 → 記錄位置

## Phase 3: 補充（如需）

文獻：`unified_search(query)` → `save_reference_mcp(pmid)`
分析：討論數據是否可回答、如何呈現

## Phase 4: 驗證

`validation_action(action="concept", filename="concept.md")` — 確認 🔒 NOVELTY 未弱化、🔒 SELLING POINTS 保留、各 section 不矛盾

## Phase 5: 匯出

修改稿：`export_document(action="session_start")` → `export_document(action="session_insert")` → `export_document(action="session_save", output_filename="manuscript_R1.docx")`
Response letter：Cover letter + Point-by-point + 修改摘要

## 回應策略

- 同意：Thank you...We have revised accordingly
- 部分同意：We agree X, but believe Y because...However, we added...
- 不同意：We respectfully disagree because [evidence]...added limitation discussion

## 注意

不刪關鍵內容、保持禮貌、具體回應（非「已修改」）、標記所有修改位置
