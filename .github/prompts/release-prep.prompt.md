---
description: "🚢 release-prep - 發布準備流程"
---

# 發布準備流程

📖 **Capability 類型**: 高層編排
📖 **編排 Skills**: code-quality → changelog-updater → readme-updater → git-precommit

---

## 🎯 此 Capability 的目標

完成發布前的所有準備工作：
1. 品質檢查
2. 更新文件
3. 版本號更新
4. 建立發布標籤

---

## Phase 1: 品質確認 `quality`

📖 Capability: `.github/prompts/code-quality.prompt.md`

### Step 1.1: 執行完整檢查

```bash
# 靜態分析
uv run ruff check src/ tests/
uv run mypy src/

# 測試
uv run pytest tests/ -v --cov=src
```

### Step 1.2: 確認無阻擋問題

```
✅ 必須通過：
- 所有 linting 錯誤已修復
- 所有測試通過
- 覆蓋率 ≥ 80%

⚠️ 可以暫緩：
- Warning（非 error）
- 建議性改善
```

---

## Phase 2: 更新文件 `docs`

### Step 2.1: 更新 CHANGELOG

📖 Skill: `.claude/skills/changelog-updater/SKILL.md`

```
讀取 git log 自上次發布以來的 commits
分類為：
- Added
- Changed
- Fixed
- Deprecated
- Removed
- Security

更新 CHANGELOG.md
```

### Step 2.2: 更新 README

📖 Skill: `.claude/skills/readme-updater/SKILL.md`

```
確認：
- 安裝指令正確
- 功能說明最新
- 範例可執行
- 版本號正確
```

### Step 2.3: 更新 ROADMAP

📖 Skill: `.claude/skills/roadmap-updater/SKILL.md`

```
標記已完成的里程碑
更新進行中的項目
```

---

## Phase 3: 版本更新 `version`

### Step 3.1: 確定版本號

遵循 Semantic Versioning：

| 變更類型 | 版本更新 | 範例 |
|----------|----------|------|
| Breaking changes | Major | 1.0.0 → 2.0.0 |
| New features | Minor | 1.0.0 → 1.1.0 |
| Bug fixes | Patch | 1.0.0 → 1.0.1 |

### Step 3.2: 更新版本號

```python
# pyproject.toml
[project]
version = "X.Y.Z"

# src/__init__.py（如果有）
__version__ = "X.Y.Z"
```

### Step 3.3: 同步版本號

確保以下位置版本一致：
- `pyproject.toml`
- `CHANGELOG.md` 標題
- 任何 `__version__` 變數

---

## Phase 4: 提交與標籤 `release`

📖 Skill: `.claude/skills/git-precommit/SKILL.md`

### Step 4.1: 建立發布 commit

```bash
git add -A
git commit -m "chore: release vX.Y.Z"
```

### Step 4.2: 建立標籤

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
```

### Step 4.3: 推送

```bash
git push origin master
git push origin vX.Y.Z
```

---

## Phase 5: 發布後 `post-release`

### Step 5.1: 發布到 PyPI（如適用）

```bash
uv build
uv publish
```

### Step 5.2: 建立 GitHub Release

```
標題: vX.Y.Z
內容: 從 CHANGELOG 複製
附件: dist/*.whl, dist/*.tar.gz
```

### Step 5.3: 更新進度

```
更新 Memory Bank:
- progress.md: 標記發布完成
- ROADMAP: 標記里程碑
```

---

## 📋 發布檢查清單

```markdown
# 發布 vX.Y.Z 檢查清單

## 品質
- [ ] ruff 無錯誤
- [ ] mypy 無錯誤
- [ ] 所有測試通過
- [ ] 覆蓋率 ≥ 80%

## 文件
- [ ] CHANGELOG.md 已更新
- [ ] README.md 已檢查
- [ ] ROADMAP.md 已更新

## 版本
- [ ] pyproject.toml 版本已更新
- [ ] 版本號一致

## Git
- [ ] 所有變更已提交
- [ ] 標籤已建立
- [ ] 已推送到 remote

## 發布
- [ ] PyPI 已發布（如適用）
- [ ] GitHub Release 已建立
```

---

## ⚠️ 回滾方案

如果發布後發現問題：

```bash
# 刪除本地標籤
git tag -d vX.Y.Z

# 刪除遠端標籤
git push origin :refs/tags/vX.Y.Z

# 回滾 commit
git revert HEAD
git push
```
