# Progress (Updated: 2025-12-17)

## Done

- MCP 解耦：完全移除 mdpaper 對 pubmed_search 的依賴
- ReferenceManager 重構：新 API save_reference(article)
- Skill tools 移除：已內建於 VS Code Copilot
- Deprecated API 移除：save_reference_by_pmid_legacy
- copilot-instructions.md 更新：新增 MCP 架構原則
- README 更新：Python 3.11+、工具數量 46、新架構說明
- save_reference JSON 解析修復：處理 MCP 傳遞 JSON 字串的情況
- **MCP Tool Logging 系統建立**：
  - `tool_logging.py`：log_tool_call, log_tool_result, log_agent_misuse
  - 日誌存放在專案目錄 `{project}/logs/YYYYMMDD.log`（跨平台）
  - 已為 draft/writing.py, project/crud.py, validation/concept.py, reference/manager.py 添加日誌

## Doing

- 為其餘 MCP tools 添加日誌記錄

## Next

- 測試新 reference 工作流程
- 重啟 MCP Server 測試日誌功能
- 分析 Agent 錯誤使用工具的日誌模式
