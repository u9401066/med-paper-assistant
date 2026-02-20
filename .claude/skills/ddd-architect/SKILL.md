---
name: ddd-architect
description: DDD 架構輔助與檢查。觸發：架構、新功能、新模組、domain、structure。
---

# DDD 架構輔助技能

觸發：新增功能/模組、架構檢查、建立新檔案時自動檢查

工具：`grep_search`（搜尋 import）、`list_dir`、`read_file`、`create_file`

---

## 層級結構

`src/domain/` → entities, value_objects, aggregates, repositories(介面), services
`src/application/` → use_cases, dtos
`src/infrastructure/` → persistence, services(外部服務實作)
`src/interfaces/` → api, mcp

## 依賴規則

✅ Presentation → Application → Domain ← Infrastructure（實作介面）
❌ Domain → Infrastructure, Domain → Application, Application → Presentation

## 違規檢查

| 違規                    | 修復                 |
| ----------------------- | -------------------- |
| Domain → Infrastructure | 使用 Repository 介面 |
| 直接 SQL 在 Domain      | 抽出到 Repository    |
| Application → DB        | 透過 Repository      |

檢查方法：`grep_search(query="from.*infrastructure.*import", isRegexp=True, includePattern="**/domain/**/*.py")`

## 工作流

A: **新功能腳手架** — 依序建立 Domain(entity+repo介面) → Application(use_case+dto) → Infrastructure(repo實作)
B: **架構違規檢查** — grep Domain 層的 Infrastructure import → 有結果即違規
