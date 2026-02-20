# Capability Index

> 觸發規則：精確（`/mdpaper.xxx`）→ 意圖匹配 → 情境匹配。匹配時載入對應 Prompt File。

## 研究 Capabilities

| Capability          | Prompt File                             | 觸發語                                        |
| ------------------- | --------------------------------------- | --------------------------------------------- |
| write-paper         | `mdpaper.write-paper.prompt.md`         | 寫論文、完整流程、從頭開始、全自動、autopilot |
| literature-survey   | `mdpaper.literature-survey.prompt.md`   | 系統性搜尋、找所有相關、全面調查              |
| manuscript-revision | `mdpaper.manuscript-revision.prompt.md` | revision、reviewer comment、被退稿            |
| quick-search        | `mdpaper.search.prompt.md`              | 找論文、search、PubMed                        |

## 研究單步 Prompts

| Prompt   | Prompt File                  | 觸發語                    |
| -------- | ---------------------------- | ------------------------- |
| concept  | `mdpaper.concept.prompt.md`  | 發展概念、文獻缺口        |
| draft    | `mdpaper.draft.prompt.md`    | 撰寫草稿、寫 Introduction |
| project  | `mdpaper.project.prompt.md`  | 設置專案、paper type      |
| format   | `mdpaper.format.prompt.md`   | 匯出 Word、export         |
| strategy | `mdpaper.strategy.prompt.md` | 搜尋策略、配置關鍵字      |
| analysis | `mdpaper.analysis.prompt.md` | 資料分析、統計、Table 1   |
| clarify  | `mdpaper.clarify.prompt.md`  | 改進內容、refine          |
| help     | `mdpaper.help.prompt.md`     | 顯示所有指令              |

## 開發 Capabilities

| Capability   | Prompt File              | 觸發語                |
| ------------ | ------------------------ | --------------------- |
| code-quality | `code-quality.prompt.md` | code review、品質檢查 |
| release-prep | `release-prep.prompt.md` | 準備發布、release     |

## Hook 系統

Copilot Hooks（A-D，寫作時）→ `auto-paper/SKILL.md`
Pre-Commit Hooks（P1-P8 + G1-G7）→ `git-precommit/SKILL.md`
詳見 AGENTS.md Hook 架構表。
