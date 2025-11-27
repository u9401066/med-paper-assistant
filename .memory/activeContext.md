# Active Context

## Current Work
修正模組初始化時不建立根目錄資料夾的問題。

## Recently Completed
- **目錄初始化修正** (2025-11-27):
  - 移除 `analyzer.py` 初始化時建立 data/, results/ 的程式碼
  - 移除 `reference_manager.py` 初始化時建立 references/ 的程式碼
  - 移除 `drafter.py` 初始化時建立 drafts/ 的程式碼
  - 修改 `logger.py` 使用系統臨時目錄而非 logs/
  - 目錄現在只在專案建立時 (`create_project`) 才會建立

## Directory Creation Rules
- **專案建立時** (`project_manager.create_project`): 建立完整專案結構
- **儲存檔案時**: 各模組在實際儲存時建立必要的子目錄
- **初始化時**: 不建立任何目錄（避免污染根目錄）

## Clean Root Directory
```
med-paper-assistant/
├── .memory/          # System memory
├── projects/         # All research projects
├── src/              # Source code
├── tests/            # Test suite
├── scripts/          # Setup scripts
├── templates/        # Word templates
└── (no data/drafts/references/results/logs)
```
