# Copilot 自定義指令

> **📋 完整指引請參見 [AGENTS.md](../AGENTS.md)**

此文件為簡化版，完整的 Agent 指引位於專案根目錄。

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

### 回應風格
- 繁體中文
- 清晰步驟
- 引用法規
