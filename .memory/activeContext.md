# Active Context

## Current Work
清理根目錄結構，移除與 projects/ 重複的目錄。

## Recently Completed
- **目錄清理** (2025-11-27):
  - 刪除根目錄的 `drafts/`, `references/`, `results/`
  - 刪除空的 `data/` 和 `logs/`
  - 這些目錄應該存在於 `projects/{project-slug}/` 內

## Current Directory Structure
```
med-paper-assistant/
├── .memory/              # System memory (development only)
├── projects/             # All research projects
│   └── {project-slug}/
│       ├── concept.md
│       ├── drafts/
│       ├── references/
│       ├── data/
│       └── results/
├── src/                  # Source code
├── tests/                # Test suite
├── test_*/               # Test fixtures (pytest)
├── templates/            # Word templates
└── scripts/              # Setup scripts
```

## Notes
- 每個專案的檔案都應該在 `projects/{slug}/` 內
- 根目錄不應有 drafts, references, results, data 等目錄
- `test_*` 目錄是 pytest fixtures，保留供測試使用
