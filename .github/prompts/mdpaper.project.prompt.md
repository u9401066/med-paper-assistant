---
description: "📁 mdpaper.project - 設置和配置研究專案"
---

# 設置研究專案
📖 **技能參考**: `.claude/skills/project-management/SKILL.md`
請依序執行以下步驟：

## Step 1: 確認專案狀態

使用 `mcp_mdpaper_list_projects()` 列出所有專案。

**決策點：**
- 如果用戶指定了專案名稱 → 檢查是否存在
- 如果未指定 → 詢問用戶要建立新專案還是切換現有專案

---

## Step 2: 建立或切換專案

**新專案：**
```
mcp_mdpaper_create_project(name="專案名稱")
```

**切換現有專案：**
```
mcp_mdpaper_switch_project(slug="專案代碼")
```

---

## Step 3: 互動式設定

使用 `mcp_mdpaper_setup_project_interactive()` 進行：

1. **Paper Type** (required) - 選擇論文類型：
   - `original-research` - 原創研究
   - `systematic-review` - 系統性回顧
   - `meta-analysis` - 統合分析
   - `case-report` - 病例報告
   - `letter` - 讀者來函

2. **Interaction Preferences** (optional) - 互動偏好

3. **Project Memo** (optional) - 備註

---

## 📋 完成檢查

- [ ] 專案已建立或切換
- [ ] Paper type 已設定
- [ ] 可以開始進行 `/mdpaper.concept` 或 `/mdpaper.search`
