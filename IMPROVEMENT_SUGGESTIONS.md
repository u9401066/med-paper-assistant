# Med-Paper-Assistant 專案改進建議

## 📊 專案現況評估

### ✅ 優點
1. **架構清晰** - MCP server + Core modules 分離良好
2. **功能完整** - 涵蓋文獻搜尋、分析、草稿、匯出全流程
3. **引用自動化** - PMID → [數字] 轉換運作正常
4. **PubMed 整合** - 使用 Biopython 的 Entrez API 穩定可靠
5. **測試覆蓋** - 有 12 個測試檔案

### ⚠️ 待改進項目
1. `formatter.py` 尚未實作
2. 缺少錯誤處理和日誌系統
3. 引用格式只有一種（Vancouver style）
4. 缺少非同步處理能力
5. Word 匯出功能較基礎

---

## 🚀 功能增強建議

### 1. 引用格式擴充 (高優先)

**問題**: 目前只支援 Vancouver 風格 `[1]`

**建議**: 新增多種引用格式支援

```python
# 建議新增到 drafter.py
class CitationStyle:
    VANCOUVER = "vancouver"      # [1]
    APA = "apa"                  # (Author, Year)
    HARVARD = "harvard"          # (Author Year)
    NATURE = "nature"            # Superscript¹
    AMA = "ama"                  # ¹
    
class Drafter:
    def __init__(self, reference_manager, drafts_dir="drafts", 
                 citation_style=CitationStyle.VANCOUVER):
        self.citation_style = citation_style
        # ...
        
    def _format_citation(self, number: int, metadata: dict) -> str:
        """根據期刊風格格式化引用"""
        if self.citation_style == CitationStyle.VANCOUVER:
            return f"[{number}]"
        elif self.citation_style == CitationStyle.APA:
            author = metadata['authors'][0].split()[0] if metadata['authors'] else "Unknown"
            return f"({author}, {metadata['year']})"
        # ...
```

**新增 MCP 工具**:
```python
@mcp.tool()
def set_citation_style(style: str) -> str:
    """
    Set the citation style for the current session.
    
    Args:
        style: Citation style ("vancouver", "apa", "nature", "ama")
    """
```

---

### 2. 完善 Reference Manager (高優先)

**建議新增功能**:

```python
# reference_manager.py 擴充

class ReferenceManager:
    # 新增方法
    
    def search_local(self, query: str) -> List[Dict]:
        """搜尋本地文獻庫"""
        results = []
        for pmid in self.list_references():
            meta = self.get_metadata(pmid)
            if query.lower() in meta.get('title', '').lower() or \
               query.lower() in meta.get('abstract', '').lower():
                results.append(meta)
        return results
    
    def export_bibliography(self, pmids: List[str], style: str = "vancouver") -> str:
        """匯出指定文獻的參考文獻列表"""
        pass
    
    def get_citation_count(self, pmid: str) -> int:
        """查詢文獻被引用次數 (需整合 Semantic Scholar API)"""
        pass
    
    def find_related_papers(self, pmid: str, limit: int = 5) -> List[Dict]:
        """查找相關文獻 (使用 PubMed Related Articles)"""
        pass
    
    def import_from_ris(self, filepath: str) -> List[str]:
        """從 RIS 檔案匯入文獻"""
        pass
    
    def export_to_ris(self, pmids: List[str], filepath: str) -> str:
        """匯出為 RIS 格式 (可匯入 EndNote/Zotero)"""
        pass
```

**新增 MCP 工具**:
```python
@mcp.tool()
def search_local_references(query: str) -> str:
    """Search within saved local references by keyword."""

@mcp.tool()
def find_related_papers(pmid: str, limit: int = 5) -> str:
    """Find related papers based on a PMID."""

@mcp.tool()
def export_references_ris(pmids: str) -> str:
    """Export references to RIS format for EndNote/Zotero."""
```

---

### 3. 增強 Analyzer 統計功能 (中優先)

**建議新增**:

```python
# analyzer.py 擴充

class Analyzer:
    def run_statistical_test(self, filename, test_type, col1, col2=None, **kwargs):
        # 現有的 t-test, correlation
        
        # 新增統計方法
        if test_type == "anova":
            return self._run_anova(df, col1, col2)
        elif test_type == "chi-square":
            return self._run_chi_square(df, col1, col2)
        elif test_type == "mann-whitney":
            return self._run_mann_whitney(df, col1, col2)
        elif test_type == "wilcoxon":
            return self._run_wilcoxon(df, col1, col2)
        elif test_type == "paired-t":
            return self._run_paired_ttest(df, col1, col2)
        elif test_type == "logistic-regression":
            return self._run_logistic_regression(df, col1, col2, **kwargs)
        elif test_type == "survival":
            return self._run_survival_analysis(df, time_col=col1, event_col=col2)
    
    def create_table_one(self, filename: str, group_col: str, 
                         continuous_cols: List[str], 
                         categorical_cols: List[str]) -> str:
        """Generate Table 1 (baseline characteristics) for medical papers"""
        # 使用 tableone 套件
        pass
    
    def create_forest_plot(self, data: Dict) -> str:
        """Generate forest plot for meta-analysis visualization"""
        pass
    
    def power_analysis(self, effect_size: float, alpha: float = 0.05, 
                       power: float = 0.8) -> str:
        """Calculate required sample size"""
        pass
```

**新增依賴** (`pyproject.toml`):
```toml
dependencies = [
    # 現有...
    "tableone",        # Table 1 生成
    "lifelines",       # 生存分析
    "statsmodels",     # 進階統計
    "pingouin",        # 更多統計方法
]
```

---

### 4. 增強 Word Exporter (中優先)

**建議改進**:

```python
# exporter.py 擴充

class WordExporter:
    def export_to_word(self, draft_path, template_path, output_path, 
                       journal_style=None):
        """
        改進版匯出功能
        
        新增:
        - 表格支援 (從 Markdown 表格轉換)
        - 自動頁碼
        - 行號 (可選)
        - 字數統計
        - 圖片自動編號
        - 交叉引用
        """
        pass
    
    def _parse_markdown_table(self, table_text: str) -> List[List[str]]:
        """解析 Markdown 表格"""
        pass
    
    def _add_table(self, doc, data: List[List[str]], style: str = "Table Grid"):
        """新增表格到文件"""
        pass
    
    def _add_figure_caption(self, doc, caption: str, figure_num: int):
        """新增圖片標題與編號"""
        pass
    
    def add_journal_specific_formatting(self, doc, journal: str):
        """套用期刊特定格式"""
        journal_configs = {
            "nature": {"font": "Arial", "size": 11, "line_spacing": 2},
            "lancet": {"font": "Times New Roman", "size": 12, "line_spacing": 2},
            "nejm": {"font": "Arial", "size": 11, "line_spacing": 2},
            "jama": {"font": "Times New Roman", "size": 11, "line_spacing": 2},
        }
        # 套用設定...
```

---

### 5. 新增 Prompt Templates (高優先)

**建議**: 新增專門的論文寫作提示模板

```python
# 新增檔案: src/med_paper_assistant/core/prompts.py

SECTION_PROMPTS = {
    "introduction": """
Write an Introduction section for a medical research paper with the following structure:
1. Opening statement about the clinical problem/significance
2. Current state of knowledge (cite provided references)
3. Knowledge gap or controversy
4. Study rationale and hypothesis
5. Study objectives

Guidelines:
- Use formal academic tone
- Each claim should have a citation
- Avoid first person (use "this study" instead of "we")
- Target length: 400-600 words
""",
    
    "methods": """
Write a Methods section following CONSORT/STROBE guidelines:
1. Study design
2. Setting and participants
3. Inclusion/exclusion criteria
4. Intervention or exposure
5. Outcomes (primary and secondary)
6. Sample size calculation
7. Statistical analysis

Guidelines:
- Use past tense
- Be specific and reproducible
- Include ethical approval statement
""",
    
    "results": """
Write a Results section based on the provided statistical outputs:
1. Participant flow and baseline characteristics
2. Primary outcome results
3. Secondary outcome results
4. Subgroup analyses (if applicable)

Guidelines:
- Report exact p-values (except p<0.001)
- Include confidence intervals
- Reference tables and figures
- Do not interpret results (save for Discussion)
""",
    
    "discussion": """
Write a Discussion section with the following structure:
1. Summary of main findings
2. Comparison with existing literature
3. Possible mechanisms
4. Clinical implications
5. Strengths and limitations
6. Future directions
7. Conclusion

Guidelines:
- Start with interpretation, not repetition of results
- Acknowledge limitations honestly
- Avoid overstatement of findings
""",
    
    "abstract": """
Write a structured abstract (250-300 words) with:
- Background: 2-3 sentences
- Methods: 3-4 sentences
- Results: 4-5 sentences with key statistics
- Conclusions: 2-3 sentences

Guidelines:
- No citations in abstract
- Include specific numbers
- State clinical significance
"""
}
```

**新增 MCP 工具**:
```python
@mcp.tool()
def get_section_template(section: str) -> str:
    """
    Get writing guidelines for a specific paper section.
    
    Args:
        section: "introduction", "methods", "results", "discussion", "abstract"
    """
    return SECTION_PROMPTS.get(section, "Section not found")
```

---

### 6. 增強錯誤處理與日誌 (中優先)

**建議新增**:

```python
# 新增檔案: src/med_paper_assistant/core/logger.py

import logging
from datetime import datetime

def setup_logger(name: str = "med_paper_assistant"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # 檔案處理器
    fh = logging.FileHandler(f"logs/{datetime.now().strftime('%Y%m%d')}.log")
    fh.setLevel(logging.DEBUG)
    
    # 控制台處理器
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger

# 在其他模組中使用
# from med_paper_assistant.core.logger import setup_logger
# logger = setup_logger()
# logger.info("搜尋文獻...")
# logger.error(f"無法取得 PMID {pmid}: {error}")
```

---

### 7. 新增自動摘要功能 (低優先)

**建議**: 整合 LLM 進行文獻摘要

```python
# 新增到 reference_manager.py

def summarize_paper(self, pmid: str, max_length: int = 200) -> str:
    """
    Generate a brief summary of a paper.
    
    Note: This could use:
    1. Built-in abstractive summarization
    2. Integration with local LLM
    3. External API (OpenAI, etc.)
    """
    metadata = self.get_metadata(pmid)
    if not metadata:
        return "Paper not found"
    
    # 簡單版本：返回摘要前 N 個字
    abstract = metadata.get('abstract', '')
    if len(abstract) > max_length:
        return abstract[:max_length] + "..."
    return abstract

def compare_papers(self, pmids: List[str]) -> str:
    """
    Generate a comparison table of multiple papers.
    
    Returns a markdown table comparing:
    - Study design
    - Sample size
    - Main findings
    - Limitations
    """
    pass
```

---

## 🛠️ 技術改進建議

### 1. 非同步支援

```python
# server.py 改進

import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=3)

@mcp.tool()
async def search_literature_async(query: str, limit: int = 5) -> str:
    """非同步文獻搜尋（避免阻塞）"""
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(
        executor, 
        lambda: searcher.search(query, limit)
    )
    return format_results(results)
```

### 2. 快取機制

```python
# 新增檔案: src/med_paper_assistant/core/cache.py

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

class SearchCache:
    def __init__(self, cache_dir=".cache", ttl_hours=24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
    
    def _get_key(self, query: str, **kwargs) -> str:
        data = f"{query}_{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def get(self, query: str, **kwargs):
        key = self._get_key(query, **kwargs)
        cache_file = self.cache_dir / f"{key}.json"
        
        if cache_file.exists():
            with open(cache_file) as f:
                cached = json.load(f)
            if datetime.fromisoformat(cached['timestamp']) + self.ttl > datetime.now():
                return cached['data']
        return None
    
    def set(self, query: str, data, **kwargs):
        key = self._get_key(query, **kwargs)
        cache_file = self.cache_dir / f"{key}.json"
        
        with open(cache_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'data': data
            }, f)
```

### 3. 設定檔支援

```python
# 新增檔案: src/med_paper_assistant/config.py

from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # PubMed API
    pubmed_email: str = "your.email@example.com"
    pubmed_api_key: Optional[str] = None  # 可選，提高速率限制
    
    # 目錄設定
    data_dir: str = "data"
    drafts_dir: str = "drafts"
    references_dir: str = "references"
    results_dir: str = "results"
    
    # 預設值
    default_citation_style: str = "vancouver"
    default_search_limit: int = 10
    
    # 快取
    enable_cache: bool = True
    cache_ttl_hours: int = 24
    
    class Config:
        env_file = ".env"
        env_prefix = "MEDPAPER_"

settings = Settings()
```

---

## 📦 新增依賴建議

```toml
# pyproject.toml 更新

[project]
dependencies = [
    # 現有依賴
    "mcp",
    "pydantic",
    "biopython",
    "pandas",
    "matplotlib",
    "scipy",
    "seaborn",
    "tabulate",
    "python-docx",
    
    # 建議新增
    "tableone",          # Table 1 生成
    "lifelines",         # 生存分析 (Kaplan-Meier)
    "statsmodels",       # 進階統計
    "pingouin",          # 更多統計方法
    "pydantic-settings", # 設定管理
    "aiohttp",           # 非同步 HTTP
    "rispy",             # RIS 檔案處理
    "pyyaml",            # YAML 設定檔
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
    "pytest-cov",
    "black",
    "ruff",
    "mypy",
]
```

---

## 📋 新增 MCP 工具建議總結

### 高優先
| 工具名稱 | 功能 |
|---------|------|
| `set_citation_style` | 設定引用格式 |
| `search_local_references` | 搜尋本地文獻庫 |
| `find_related_papers` | 查找相關文獻 |
| `get_section_template` | 取得章節寫作模板 |
| `generate_table_one` | 生成 Table 1 |

### 中優先
| 工具名稱 | 功能 |
|---------|------|
| `export_references_ris` | 匯出 RIS 格式 |
| `import_references_ris` | 匯入 RIS 檔案 |
| `run_survival_analysis` | 生存分析 |
| `calculate_sample_size` | 樣本數計算 |
| `summarize_paper` | 摘要文獻 |

### 低優先
| 工具名稱 | 功能 |
|---------|------|
| `compare_papers` | 比較多篇文獻 |
| `get_citation_count` | 取得引用次數 |
| `check_journal_requirements` | 檢查期刊投稿要求 |

---

## 🎯 實作優先順序建議

### Phase 1 (1-2 週)
1. ✅ 多引用格式支援
2. ✅ 本地文獻搜尋
3. ✅ 錯誤處理與日誌
4. ✅ 完善 `formatter.py`

### Phase 2 (2-4 週)
1. ✅ Table 1 生成
2. ✅ 更多統計方法
3. ✅ RIS 匯入匯出
4. ✅ 章節寫作模板

### Phase 3 (4-6 週)
1. ✅ Word 匯出增強
2. ✅ 相關文獻推薦
3. ✅ 快取機制
4. ✅ 非同步處理

---

## 📝 立即可執行的小改進

### 1. 修復 `formatter.py`

```python
# src/med_paper_assistant/core/formatter.py

import re
from typing import Dict, Any

class Formatter:
    """Format text according to journal guidelines."""
    
    JOURNAL_CONFIGS = {
        "nature": {
            "max_abstract_words": 150,
            "max_references": 50,
            "citation_style": "superscript",
        },
        "lancet": {
            "max_abstract_words": 300,
            "max_references": 40,
            "citation_style": "vancouver",
        },
        "nejm": {
            "max_abstract_words": 250,
            "max_references": 50,
            "citation_style": "vancouver",
        },
    }
    
    def __init__(self):
        self.current_config = None
    
    def set_journal(self, journal: str):
        """Set target journal for formatting."""
        journal = journal.lower()
        if journal in self.JOURNAL_CONFIGS:
            self.current_config = self.JOURNAL_CONFIGS[journal]
        else:
            raise ValueError(f"Unknown journal: {journal}")
    
    def check_word_count(self, text: str, section: str = "abstract") -> Dict[str, Any]:
        """Check if word count meets journal requirements."""
        words = len(text.split())
        limit = self.current_config.get(f"max_{section}_words", float('inf'))
        
        return {
            "word_count": words,
            "limit": limit,
            "within_limit": words <= limit,
            "excess": max(0, words - limit)
        }
    
    def format_numbers(self, text: str) -> str:
        """Format numbers according to medical writing standards."""
        # 小於 10 的數字用文字
        def replace_small_numbers(match):
            num = int(match.group(0))
            words = ["zero", "one", "two", "three", "four", 
                    "five", "six", "seven", "eight", "nine"]
            if num < 10 and not match.group(0).startswith('0'):
                return words[num]
            return match.group(0)
        
        # 只替換獨立數字（不在統計數據中）
        # 這是簡化版本
        return text
    
    def apply_template(self, content: str, template_name: str) -> str:
        """Apply a template to content."""
        # TODO: 實作模板套用邏輯
        return content
```

### 2. 新增 search_local_references 工具

```python
# 在 server.py 新增

@mcp.tool()
def search_local_references(query: str) -> str:
    """
    Search within saved local references by keyword.
    
    Args:
        query: Keyword to search in titles and abstracts.
    """
    results = []
    for pmid in ref_manager.list_references():
        meta = ref_manager.get_metadata(pmid)
        if meta:
            title = meta.get('title', '').lower()
            abstract = meta.get('abstract', '').lower()
            if query.lower() in title or query.lower() in abstract:
                results.append(f"PMID:{pmid} - {meta.get('title', 'Unknown')[:80]}...")
    
    if not results:
        return f"No local references found matching '{query}'"
    
    return f"Found {len(results)} matching references:\n" + "\n".join(results)
```

---

## 🎉 總結

Med-Paper-Assistant 是一個**很有潛力的專案**！基本架構穩固，核心功能運作正常。

**最重要的三項改進**:
1. 🔥 **多引用格式** - 不同期刊有不同要求
2. 🔥 **Table 1 生成** - 這是醫學論文的標配
3. 🔥 **本地文獻搜尋** - 已保存 30 篇，需要能快速找到

如需我協助實作任何建議，請告訴我！
