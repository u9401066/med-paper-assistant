# Active Context

## Current Work
新增 Windows 安裝腳本，更新 README 文件。

## Recently Completed
- **Windows Setup Scripts** (2025-11-27):
  - 新增 `scripts/setup.ps1` (PowerShell)
  - 新增 `scripts/setup.bat` (Command Prompt)
  - 更新 `scripts/setup.sh` (Linux/macOS)
  - 更新 README 雙語安裝說明
  - 更新專案結構說明（projects/ 結構）
  - 更新工具數量（33→42）

## Setup Scripts
| Script | Platform | Usage |
|--------|----------|-------|
| `setup.sh` | Linux/macOS | `./scripts/setup.sh` |
| `setup.ps1` | Windows PowerShell | `.\scripts\setup.ps1` |
| `setup.bat` | Windows CMD | `scripts\setup.bat` |

## Directory Structure
```
med-paper-assistant/
├── projects/             # Research projects
│   └── {slug}/
│       ├── concept.md
│       ├── drafts/
│       ├── references/
│       ├── data/
│       └── results/
├── src/                  # Source code
├── tests/                # Test suite
├── scripts/              # Setup scripts (sh, ps1, bat)
└── templates/            # Word templates
```
