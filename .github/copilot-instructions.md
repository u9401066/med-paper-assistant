# Copilot 自定義指令

> **📋 完整指引請參見 [AGENTS.md](../AGENTS.md)**

此文件為簡化版，完整的 Agent 指引位於專案根目錄。

## 🎛️ 運行模式

**在開始操作前，先檢查 `.copilot-mode.json` 的 `mode` 值！**

| 模式 | 說明 | 檔案保護 |
|------|------|----------|
| `development` | 開發模式 - 啟用所有技能和靜態分析 | ❌ 無 |
| `normal` | 一般模式 - 僅研究技能 | ✅ 受保護 |
| `research` | 研究模式 - 專注論文寫作 | ✅ 受保護 |

**切換方式**：用戶說「開發模式」/「一般模式」/「研究模式」時，修改 `.copilot-mode.json`

### 🔒 檔案保護（Normal/Research 模式）

**受保護路徑（唯讀）**：
- `.claude/` - Skills 定義
- `.github/` - Copilot 指令
- `src/` - 原始碼
- `tests/` - 測試
- `integrations/` - MCP 整合
- `AGENTS.md`, `CONSTITUTION.md`, `pyproject.toml`

**可修改路徑**：
- `projects/` - 研究專案
- `docs/` - 文件

**用戶要修改受保護檔案時**：
```
⚠️ 目前是 [normal/research] 模式，這個檔案受保護。
請說「開發模式」切換後再修改。
```

## 快速參考

### 法規層級
1. **憲法**：`CONSTITUTION.md`
2. **子法**：`.github/bylaws/*.md`
3. **技能**：`.claude/skills/*/SKILL.md`

### 核心原則
- **DDD 架構**：Domain-Driven Design
- **MCP-to-MCP 通訊**：儲存文獻用 `save_reference_mcp(pmid)`，不是傳 metadata
- **Memory Bank**：`memory-bank/` 強制同步
- **Python 環境**：uv 優先、禁止全域安裝

### ⚠️ 儲存文獻規則

```
✅ 正確：save_reference_mcp(pmid="12345678", agent_notes="...")
   → mdpaper 直接從 pubmed-search API 取得驗證資料

❌ 錯誤：save_reference(article={從 search 拿到的完整 metadata})
   → Agent 可能修改/幻覺書目資料（僅當 API 不可用時 fallback）
```

### ⚠️ Novelty Check 規則（犀利回饋模式！）

```
📌 核心：像頂尖 Reviewer 一樣犀利，但給選項！

✅ 正確做法：
   1. 直指問題：「您聲稱『首次』，但沒有搜尋證據」
   2. 提出 Reviewer 會問的問題
   3. 給具體修復方案（不是「可以考慮」）
   4. 主動問：「直接寫？修正問題？用 CGU？」
   5. 用戶決定後立即執行

❌ 錯誤做法：
   1. 討好式回饋「您的 concept 很好喔～」
   2. 自動開始修改 NOVELTY STATEMENT
   3. 反覆修改追分數
   4. 越改越糟還繼續改
```

**CGU 創意工具**：主動問用戶要不要用 CGU 幫忙
- `deep_think` - 從 reviewer 角度找弱點
- `spark_collision` - 碰撞現有限制與我的優勢
- `generate_ideas` - 發想無可辯駁的 novelty

### 回應風格
- 繁體中文
- 清晰步驟
- 引用法規
