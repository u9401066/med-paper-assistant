# Progress (Updated: 2025-12-17)

## Done

- MCP 解耦：完全移除 mdpaper 對 pubmed_search 的依賴
- ReferenceManager 重構：新 API save_reference(article)
- Skill tools 移除：已內建於 VS Code Copilot
- Deprecated API 移除：save_reference_by_pmid_legacy
- copilot-instructions.md 更新：新增 MCP 架構原則
- README 更新：Python 3.11+、工具數量 46、新架構說明
- save_reference JSON 解析修復：處理 MCP 傳遞 JSON 字串的情況
- **MCP Tool Logging 系統建立**
- **Foam 專案隔離功能**：
  - `FoamSettingsManager` 服務：動態更新 `foam.files.ignore`
  - `switch_project()` 整合：切換專案時自動更新 Foam 設定
  - Whitelist 邏輯：只顯示當前專案的 `references/`
- **Reference 格式優化**：
  - 加入 `title` frontmatter 供 Foam 顯示文章標題
  - `foam.completion.label: "title"` 設定
- **sync_references 工具**：
  - 掃描 `[[wikilinks]]` 自動生成 References 區塊
  - 可逆設計：`[1]<!-- [[citation_key]] -->` 格式
  - 支援重複同步、重新排序

## Doing

- **MCP-to-MCP 直接通訊架構設計**：
  - pubmed-search 新增 `/api/cached_article/{pmid}` HTTP endpoint
  - mdpaper `save_reference` 改為只接收 `pmid + agent_notes`
  - 分層信任：VERIFIED / AGENT / USER 區塊
- **Reference 新格式設計**：
  - BibTeX 相容的結構化 author 欄位
  - 更美觀的人類可讀格式
  - Agent 短評區塊（標記來源）

## Next

- 實作 pubmed-search HTTP API endpoint
- 實作 mdpaper MCP-to-MCP 呼叫邏輯
- 更新 reference_manager.py 生成新格式
- Migration script 更新現有參考文獻
