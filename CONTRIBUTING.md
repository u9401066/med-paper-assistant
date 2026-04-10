# Contributing Guidelines 貢獻指南

[English](#english) | [繁體中文](#繁體中文)

---

<a name="english"></a>

## 🇬🇧 English

Thank you for your interest in contributing to Medical Paper Assistant! This document explains how you can participate in the development of this project.

### What is this document?

This is a **Contributing Guide** - a standard document in open source projects that explains:

- How to report bugs or suggest features
- How to set up your development environment
- How to submit code changes
- The coding standards we follow

### Ways to Contribute

| Type                         | Description                          | Skill Level  |
| ---------------------------- | ------------------------------------ | ------------ |
| 🐛 **Report Bugs**           | Found something broken? Let us know! | Beginner     |
| �� **Suggest Features**      | Have an idea? Open an issue!         | Beginner     |
| 📝 **Improve Documentation** | Fix typos, add examples              | Beginner     |
| 🧪 **Write Tests**           | Help improve test coverage           | Intermediate |
| 🔧 **Fix Bugs**              | Pick an issue and submit a fix       | Intermediate |
| ✨ **Add Features**          | Implement new functionality          | Advanced     |

### Getting Started

#### 1. Fork & Clone

```bash
# Fork this repository on GitHub (click the "Fork" button)

# Clone your fork
git clone https://github.com/YOUR_USERNAME/med-paper-assistant.git
cd med-paper-assistant

# Add upstream remote (original repository)
git remote add upstream https://github.com/u9401066/med-paper-assistant.git
```

> 💡 **What is forking?**  
> Forking creates your own copy of the repository on GitHub. You make changes to your copy, then request to merge them back into the original.

#### 2. Set Up Development Environment

```bash
# Create virtual environment and install all dependencies
uv sync --all-extras
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
```

#### 3. Create a Branch

```bash
# Sync with upstream first
git fetch upstream
git checkout master
git merge upstream/master

# Create your feature branch
git checkout -b feature/your-feature-name
```

> 💡 **Branch naming convention:**
>
> - `feature/xxx` - New features
> - `fix/xxx` - Bug fixes
> - `docs/xxx` - Documentation changes
> - `refactor/xxx` - Code refactoring

### Making Changes

#### Project Structure (DDD Architecture)

```
src/med_paper_assistant/
├── domain/                  # Domain layer (entities, value objects, services)
├── application/            # Application layer (use cases)
├── infrastructure/         # Infrastructure layer (persistence, external services)
├── interfaces/             # Interface layer (MCP protocol entrypoints)
│   └── mcp/                # MCP server, prompts, resources, and tools
├── shared/                 # Shared utilities
└── __init__.py
```

#### Code Style

- **Python**: Follow [PEP 8](https://pep8.org/)
- **Docstrings**: Use Google style docstrings
- **Type hints**: Encouraged but not required
- **Language**: Code and comments in English; documentation can be bilingual

Example:

```python
def save_reference(pmid: str, download_pdf: bool = True) -> str:
    """
    Save a reference to the local library.

    Args:
        pmid: PubMed ID of the article.
        download_pdf: Whether to attempt PDF download from PMC.

    Returns:
        Success message with reference details.
    """
    pass
```

### Testing

```bash
# Run all tests
uv run pytest tests/

# Run specific test
uv run pytest tests/test_project_manager.py

# Run with coverage
uv run pytest tests/ --cov=src/med_paper_assistant
```

Please ensure:

- All existing tests pass
- New features have corresponding tests
- Test files are named `test_*.py`

### Submitting Changes

#### 1. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a descriptive message
git commit -m "feat: Add PDF download from PMC Open Access"
```

> 💡 **Commit message format:**
>
> - `feat:` - New feature
> - `fix:` - Bug fix
> - `docs:` - Documentation
> - `refactor:` - Code refactoring
> - `test:` - Adding tests
> - `chore:` - Maintenance tasks

#### 2. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

#### 3. Open a Pull Request

1. Go to your fork on GitHub
2. Click "Compare & pull request"
3. Fill in the PR template:
   - What does this PR do?
   - How was it tested?
   - Any breaking changes?

### Reporting Issues

When opening an issue, please include:

- **Bug reports:**

  - Steps to reproduce
  - Expected behavior
  - Actual behavior
  - Python version and OS
  - Error messages (if any)

- **Feature requests:**
  - Use case / problem to solve
  - Proposed solution
  - Alternatives considered

### Questions?

- Open a GitHub Issue with the `question` label
- Check existing issues first

---

<a name="繁體中文"></a>

## 🇹🇼 繁體中文

感謝您有興趣為 Medical Paper Assistant 做出貢獻！本文件說明如何參與此專案的開發。

### 這份文件是什麼？

這是一份**貢獻指南**（Contributing Guide）——開源專案中的標準文件，說明：

- 如何回報錯誤或建議功能
- 如何設置開發環境
- 如何提交程式碼變更
- 我們遵循的程式碼規範

### 貢獻方式

| 類型            | 說明                      | 技能等級 |
| --------------- | ------------------------- | -------- |
| 🐛 **回報錯誤** | 發現問題？讓我們知道！    | 初學者   |
| 💡 **建議功能** | 有想法？開一個 Issue！    | 初學者   |
| 📝 **改善文件** | 修正錯字、增加範例        | 初學者   |
| 🧪 **撰寫測試** | 幫助提高測試覆蓋率        | 中級     |
| 🔧 **修復錯誤** | 選擇一個 Issue 並提交修復 | 中級     |
| ✨ **新增功能** | 實作新功能                | 進階     |

### 開始貢獻

#### 1. Fork 與 Clone

```bash
# 在 GitHub 上 Fork 此專案（點擊「Fork」按鈕）

# Clone 您的 Fork
git clone https://github.com/您的帳號/med-paper-assistant.git
cd med-paper-assistant

# 新增 upstream remote（原始專案）
git remote add upstream https://github.com/u9401066/med-paper-assistant.git
```

> 💡 **什麼是 Fork？**  
> Fork 會在 GitHub 上建立專案的副本。您在副本上進行修改，然後請求將變更合併回原始專案。

#### 2. 設置開發環境

```bash
# 建立虛擬環境並安裝所有相依套件
uv sync --all-extras
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
```

#### 3. 建立分支

```bash
# 先與 upstream 同步
git fetch upstream
git checkout master
git merge upstream/master

# 建立您的功能分支
git checkout -b feature/您的功能名稱
```

> 💡 **分支命名慣例：**
>
> - `feature/xxx` - 新功能
> - `fix/xxx` - 錯誤修復
> - `docs/xxx` - 文件變更
> - `refactor/xxx` - 程式碼重構

### 進行修改

#### 專案結構（DDD 架構）

```
src/med_paper_assistant/
├── domain/                  # 領域層（實體、值物件、領域服務）
├── application/            # 應用層（用例）
├── infrastructure/         # 基礎設施層（持久化、外部服務）
├── interfaces/             # 介面層（MCP 協定入口）
│   └── mcp/                # MCP server、prompts、resources、tools
├── shared/                 # 共用工具
└── __init__.py
```

#### 程式碼風格

- **Python**：遵循 [PEP 8](https://pep8.org/)
- **文件字串**：使用 Google 風格的 docstring
- **型別提示**：鼓勵但非必要
- **語言**：程式碼與註解使用英文；文件可使用雙語

範例：

```python
def save_reference(pmid: str, download_pdf: bool = True) -> str:
    """
    儲存參考文獻到本地文獻庫。

    Args:
        pmid: 文章的 PubMed ID。
        download_pdf: 是否嘗試從 PMC 下載 PDF。

    Returns:
        包含參考文獻詳情的成功訊息。
    """
    pass
```

### 測試

```bash
# 執行所有測試
uv run pytest tests/

# 執行特定測試
uv run pytest tests/test_project_manager.py

# 執行並顯示覆蓋率
uv run pytest tests/ --cov=src/med_paper_assistant
```

請確保：

- 所有現有測試通過
- 新功能有對應的測試
- 測試檔案命名為 `test_*.py`

### 提交變更

#### 1. 提交您的變更

```bash
# 暫存您的變更
git add .

# 使用描述性訊息提交
git commit -m "feat: 新增從 PMC Open Access 下載 PDF 功能"
```

> 💡 **提交訊息格式：**
>
> - `feat:` - 新功能
> - `fix:` - 錯誤修復
> - `docs:` - 文件更新
> - `refactor:` - 程式碼重構
> - `test:` - 新增測試
> - `chore:` - 維護工作

#### 2. 推送到您的 Fork

```bash
git push origin feature/您的功能名稱
```

#### 3. 開啟 Pull Request

1. 前往您在 GitHub 上的 Fork
2. 點擊「Compare & pull request」
3. 填寫 PR 說明：
   - 這個 PR 做了什麼？
   - 如何測試？
   - 有任何破壞性變更嗎？

### 回報問題

開啟 Issue 時，請包含：

- **錯誤回報：**

  - 重現步驟
  - 預期行為
  - 實際行為
  - Python 版本與作業系統
  - 錯誤訊息（如有）

- **功能請求：**
  - 使用情境 / 要解決的問題
  - 建議的解決方案
  - 考慮過的替代方案

### 有問題？

- 開一個帶有 `question` 標籤的 GitHub Issue
- 先查看現有的 Issues

---

## 📜 License 授權

By contributing, you agree that your contributions will be licensed under the Apache-2.0 License.

貢獻即表示您同意您的貢獻將以 Apache-2.0 授權發布。
