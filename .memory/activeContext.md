# Active Context

## Current Focus
Draw.io MCP 繪圖指南系統實作完成

## Recent Changes (2025-11-29)

### 1. 繪圖指南工具 (Drawing Guidelines Tools) ✅

新增繪圖指南系統，確保圖表品質一致：

**新增工具:**
| 工具 | 描述 |
|------|------|
| `get_drawing_guidelines` | 取得繪圖最佳實踐（邊線、顏色、形狀、佈局） |
| `get_style_string` | 生成 Draw.io style 字串 |
| `list_available_styles` | 列出所有可用樣式和顏色 |

**新增檔案:**
| 檔案 | 說明 |
|------|------|
| `drawing_guidelines.py` | 繪圖標準定義（350+ 行） |
| `tools/guideline_tools.py` | MCP 工具實作 |

### 2. 繪圖標準規範

**連接線 (Edge Styles):**
- ⭐⭐⭐ `orthogonal` - 正交轉角線（推薦）
- ⭐ `straight` - 直線
- ⭐⭐ `curved` - 曲線
- ER專用 `entityRelation` - ER 圖關係線

**顏色規範:**
| 顏色 | fillColor | strokeColor | 用途 |
|------|-----------|-------------|------|
| 藍色 | #dae8fc | #6c8ebf | 處理步驟 |
| 綠色 | #d5e8d4 | #82b366 | 開始/成功 |
| 黃色 | #fff2cc | #d6b656 | 決策 |
| 橘色 | #ffe6cc | #d79b00 | 輸出/警告 |
| 紫色 | #e1d5e7 | #9673a6 | 外部系統 |
| 紅色 | #f8cecc | #b85450 | 結束/錯誤 |

**佈局規範:**
- 水平間距: 60px
- 垂直間距: 40px
- 畫布邊距: 40px
- 網格大小: 20px

### 3. Previous Session (2025-11-28)

Draw.io MCP 全功能完成：
- ✅ `create_diagram` - Agent 生成 XML 創建圖表
- ✅ `load_file` - 載入現有 .drawio 檔案
- ✅ `save_tab` - 智能存檔
- ✅ 分頁管理 - 多分頁切換
- ✅ 用戶存檔事件 - Ctrl+S 觸發下載

### 4. 測試通過

```bash
# 繪圖指南工具測試
=== Test 1: General Guidelines === ✅
=== Test 2: Edge Style String === ✅
=== Test 3: Shape Style String === ✅
```

## 修改的檔案

| 檔案 | 變更 |
|------|------|
| `drawing_guidelines.py` | 新增繪圖標準模組 |
| `tools/guideline_tools.py` | 新增指南工具 |
| `tools/__init__.py` | 註冊 guideline_tools |
| `README.md` | 新增繪圖指南文檔 |

## Status
✅ 繪圖指南工具實作完成
✅ 測試通過
⏳ Git commit and push
