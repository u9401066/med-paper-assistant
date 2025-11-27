# Active Context

## Current Work
整理專案目錄結構，確保測試資料只在 tests/ 內。

## Recently Completed
- **目錄結構整理** (2025-11-27):
  - 確認所有 test_* 目錄都在 `tests/` 內
  - 更新 `.gitignore` 明確指定規則
  - 根目錄已清理乾淨

## Directory Structure
```
med-paper-assistant/
├── .memory/              # System memory (dev only)
├── projects/             # Research projects (gitignored)
│   └── {slug}/
│       ├── concept.md
│       ├── drafts/
│       ├── references/
│       ├── data/
│       └── results/
├── src/                  # Source code
├── tests/                # Test suite
│   ├── test_*.py         # Test files
│   ├── test_data/        # Test fixtures (gitignored)
│   ├── test_drafts/
│   ├── test_references/
│   └── test_results/
├── templates/            # Word templates
└── scripts/              # Setup scripts
```

## .gitignore Rules
- `projects/` - 使用者資料不進 git
- `tests/test_*/` - 測試 fixtures 不進 git
- `/drafts/`, `/references/` 等 - 禁止根目錄有這些資料夾
