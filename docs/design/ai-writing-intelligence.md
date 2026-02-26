# AI Writing Intelligence - MCP 層面的寫作問題解決方案

> **Status**: Draft  
> **Created**: 2025-01-12  
> **Author**: Eric + Copilot

---

## 🎯 問題陳述

目前 med-paper-assistant 的架構主要是：

- **Prompt/Skill 層面**：靠精心設計的 prompt 和 workflow 編排
- **MCP Tools 層面**：主要是 CRUD 操作（存取檔案、搜尋文獻）

這導致 AI 寫作的三大根本問題沒有在 **代碼層面** 被解決：

| 問題         | 症狀                               | 目前「解法」                 | 為什麼不夠                    |
| ------------ | ---------------------------------- | ---------------------------- | ----------------------------- |
| **連貫性**   | 段落間跳躍、重複、邏輯斷裂         | Prompt 說「要連貫」          | 沒有強制機制，AI 下次還是忘記 |
| **引用**     | 不知道哪裡該引用、引用不支持 claim | `suggest_citations` 事後建議 | 寫作時已經定型，補引用很彆扭  |
| **思考脈絡** | 寫到哪算哪、缺乏全局架構           | `validate_concept` 檢查結構  | 只是檢查，不是引導寫作        |

---

## 🏗️ 解決方案架構

### 總體設計原則

```
❌ 目前：Agent 靠 prompt 「請求」AI 好好寫
✅ 目標：MCP tools 在代碼層面「強制」結構化寫作流程
```

### 三大模組

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AI Writing Intelligence                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │   Coherence     │  │    Citation     │  │   Argument      │     │
│  │   Engine        │  │  Intelligence   │  │   Tracker       │     │
│  │                 │  │                 │  │                 │     │
│  │  • 段落大綱     │  │  • 引用需求分析 │  │  • 論點地圖     │     │
│  │  • 上下文寫作   │  │  • 即時引用插入 │  │  • 結構化生成   │     │
│  │  • 連貫性檢查   │  │  • 引用驗證     │  │  • 邏輯鏈追蹤   │     │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘     │
│           │                    │                    │               │
│           └────────────────────┼────────────────────┘               │
│                                │                                    │
│                                ▼                                    │
│                    ┌───────────────────────┐                        │
│                    │   Shared Foundation   │                        │
│                    │  • Sentence Analyzer  │                        │
│                    │  • Reference Matcher  │                        │
│                    │  • Logic Validator    │                        │
│                    └───────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📚 Phase 1: Citation Intelligence（MVP）

### 為什麼先做這個？

1. **最具體可驗證** — 引用對/錯很明確
2. **可以 rule-based** — 不一定需要額外 LLM 調用
3. **整合現有資源** — `references/` + `pubmed-search` 已經有了
4. **用戶痛點明確** — 「這句話該引用什麼？」是常見問題

### 核心工具設計

#### 1. `analyze_citation_needs` — 分析哪些句子需要引用

```python
@mcp.tool()
def analyze_citation_needs(
    text: str,
    section: str = "",  # Introduction/Methods/Results/Discussion
) -> str:
    """
    分析文本中每個句子的引用需求。

    分類標準（Rule-based + NLP）：

    🔴 MUST_CITE (必須引用):
       - 統計數據: "15% of patients...", "mortality rate is..."
       - 比較結論: "A is better than B", "showed superior outcomes"
       - 他人研究結果: "Previous studies demonstrated..."
       - 指南/共識: "Guidelines recommend..."

    🟡 SHOULD_CITE (建議引用):
       - 背景事實: "Diabetes affects millions..."
       - 定義: "Sepsis is defined as..."
       - 一般性陳述: "It is well established that..."

    🟢 NO_CITE (不需引用):
       - 自己的研究方法: "We enrolled 100 patients"
       - 自己的結果: "Our results showed..."
       - 邏輯推論: "Therefore, we hypothesized..."
       - 研究目的: "The aim of this study was..."

    Args:
        text: 要分析的文本（可以是段落或整個 section）
        section: 文章章節，影響分析策略
                 - Introduction: 背景需要更多引用
                 - Methods: 只有參考方法需要引用
                 - Results: 只有比較他人結果需要引用
                 - Discussion: 與他人研究比較需要引用

    Returns:
        JSON report:
        {
            "sentences": [
                {
                    "text": "Mortality rate is 15%",
                    "need": "MUST_CITE",
                    "reason": "統計數據",
                    "suggested_search": "mortality rate [topic]",
                    "local_matches": ["[[smith2020_xxx]]"]  # 如果本地有
                },
                ...
            ],
            "summary": {
                "must_cite": 5,
                "should_cite": 3,
                "no_cite": 8,
                "coverage": "60% of claims have citations"
            }
        }
    """
```

**實作策略**：

```python
# 偵測模式（Rule-based）
MUST_CITE_PATTERNS = [
    r'\d+\.?\d*\s*%',                    # 百分比
    r'\d+\.?\d*\s*(mg|ml|kg|mmHg)',      # 數值+單位
    r'(mortality|survival|incidence)\s+rate',
    r'(studies|trials|research)\s+(showed|demonstrated|found)',
    r'(better|worse|superior|inferior)\s+than',
    r'(guidelines?|consensus)\s+(recommend|suggest)',
    r'(OR|HR|RR)\s*[=:]\s*\d',           # 統計指標
    r'p\s*[<>=]\s*0\.\d+',               # p-value
]

SHOULD_CITE_PATTERNS = [
    r'(is|are)\s+defined\s+as',
    r'it\s+is\s+(well\s+)?(known|established|recognized)',
    r'(common|rare|frequent)\s+(cause|complication)',
]

NO_CITE_PATTERNS = [
    r'^we\s+(enrolled|included|excluded|collected|analyzed)',
    r'^(the|this)\s+(aim|purpose|objective)\s+(of|was)',
    r'^our\s+(results|findings|data)\s+(showed|demonstrated)',
    r'^(therefore|thus|hence|consequently)',
]
```

#### 2. `find_supporting_references` — 為 claim 找引用

```python
@mcp.tool()
def find_supporting_references(
    claim: str,
    claim_type: str = "auto",  # statistical/comparison/background/guideline
    search_local: bool = True,
    search_pubmed: bool = False,
    max_results: int = 5,
) -> str:
    """
    為特定 claim 尋找支持的引用。

    搜尋策略：
    1. 先搜尋本地 references/（使用 semantic search）
    2. 如果本地沒有，生成 PubMed 搜尋建議
    3. 根據 claim_type 調整搜尋策略

    Args:
        claim: 需要支持的陳述
        claim_type:
            - "statistical": 找原始數據來源
            - "comparison": 找比較性研究（RCT、meta-analysis）
            - "background": 找 review 或權威來源
            - "guideline": 找指南文件
            - "auto": 自動判斷
        search_local: 是否搜尋本地 references/
        search_pubmed: 是否生成 PubMed 搜尋（需要 pubmed-search MCP）
        max_results: 最大結果數

    Returns:
        {
            "claim": "Remimazolam has faster onset than midazolam",
            "claim_type": "comparison",
            "local_matches": [
                {
                    "citation_key": "doi2020_12345678",
                    "title": "Comparison of onset times...",
                    "relevance_score": 0.85,
                    "supporting_text": "Onset time was 2.3 min vs 4.1 min",
                    "recommendation": "STRONG_MATCH"
                }
            ],
            "pubmed_suggestions": [
                {
                    "query": "remimazolam onset time comparison midazolam",
                    "filters": ["RCT", "recent 5 years"]
                }
            ],
            "recommendation": "Use [[doi2020_12345678]] - directly supports claim"
        }
    """
```

**Semantic Search 實作**：

```python
# 使用 sentence-transformers 做 embedding
from sentence_transformers import SentenceTransformer

class ReferenceSearcher:
    def __init__(self, references_dir: str):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = self._build_index(references_dir)

    def _build_index(self, references_dir):
        """建立 reference abstracts 的 embedding index"""
        embeddings = []
        metadata = []
        for ref in self._load_references(references_dir):
            # Embed: title + abstract
            text = f"{ref['title']}. {ref.get('abstract', '')}"
            emb = self.model.encode(text)
            embeddings.append(emb)
            metadata.append(ref)
        return {'embeddings': np.array(embeddings), 'metadata': metadata}

    def search(self, query: str, top_k: int = 5):
        """Semantic search for relevant references"""
        query_emb = self.model.encode(query)
        scores = cosine_similarity([query_emb], self.index['embeddings'])[0]
        top_indices = np.argsort(scores)[-top_k:][::-1]
        return [(self.index['metadata'][i], scores[i]) for i in top_indices]
```

#### 3. `verify_citation_support` — 驗證引用是否支持 claim

```python
@mcp.tool()
def verify_citation_support(
    claim: str,
    citation_key: str,
    strictness: str = "moderate",  # strict/moderate/lenient
) -> str:
    """
    驗證引用是否真的支持所述 claim。

    這是解決「引用存在但不支持 claim」問題的關鍵工具。

    驗證邏輯：
    1. 讀取 citation 的 abstract/fulltext
    2. 檢查 claim 的核心論點是否在 citation 中有對應
    3. 分析支持程度

    Args:
        claim: 文中的陳述
        citation_key: 引用的 citation key（如 "smith2020_12345678"）
        strictness:
            - "strict": 需要直接、明確的支持
            - "moderate": 允許合理推論的支持
            - "lenient": 主題相關即可

    Returns:
        {
            "claim": "Remimazolam causes less hypotension",
            "citation": {
                "key": "smith2020_12345678",
                "title": "...",
                "relevant_excerpt": "Blood pressure decrease was 12% vs 25%..."
            },
            "verification": {
                "supports": true,
                "confidence": 0.9,
                "support_type": "DIRECT",  # DIRECT/INDIRECT/PARTIAL/NONE
                "explanation": "Abstract directly states BP decrease comparison"
            },
            "warnings": [],
            "recommendation": "✅ Citation supports claim"
        }

        # 如果不支持：
        {
            "verification": {
                "supports": false,
                "confidence": 0.85,
                "support_type": "NONE",
                "explanation": "Citation discusses onset time, not hypotension"
            },
            "warnings": ["Citation topic mismatch"],
            "recommendation": "❌ Find different citation for hypotension claim",
            "suggested_search": "remimazolam hypotension"
        }
    """
```

#### 4. `write_paragraph_with_citations` — 寫作時即時引用

```python
@mcp.tool()
def write_paragraph_with_citations(
    topic: str,
    key_points: list[str],
    available_references: list[str],  # citation keys
    style: str = "academic",
) -> str:
    """
    根據要點撰寫段落，同時即時插入引用。

    這是解決「事後補引用」問題的關鍵工具。

    流程：
    1. 分析每個 key_point 的引用需求
    2. 從 available_references 找匹配
    3. 生成時直接帶 [[citation_key]]
    4. 標記找不到引用的 claims

    Args:
        topic: 段落主題
        key_points: 要表達的要點列表
        available_references: 可用的引用 keys
        style: 寫作風格

    Returns:
        {
            "paragraph": "Remimazolam, a novel benzodiazepine...",
            "citations_used": [
                {"key": "doi2020_xxx", "for_claim": "faster onset"}
            ],
            "missing_citations": [
                {
                    "claim": "lower cost",
                    "reason": "No matching reference found",
                    "suggested_search": "remimazolam cost effectiveness"
                }
            ],
            "citation_coverage": "4/5 claims cited (80%)"
        }
    """
```

---

## 🔧 技術實作考量

### 依賴

```toml
# pyproject.toml additions
[project.optional-dependencies]
citation-intelligence = [
    "sentence-transformers>=2.2.0",  # Semantic search
    "numpy>=1.24.0",
    "scikit-learn>=1.3.0",           # cosine_similarity
    "spacy>=3.7.0",                  # NLP for sentence analysis
]
```

### 檔案結構

```
src/med_paper_assistant/
├── domain/
│   └── services/
│       └── citation_intelligence/
│           ├── __init__.py
│           ├── analyzer.py          # analyze_citation_needs
│           ├── searcher.py          # find_supporting_references
│           ├── verifier.py          # verify_citation_support
│           └── patterns.py          # MUST_CITE_PATTERNS etc.
│
├── infrastructure/
│   └── services/
│       └── reference_embedder.py    # Semantic search index
│
└── interfaces/
    └── mcp/
        └── tools/
            └── citation/
                ├── __init__.py
                └── intelligence.py   # MCP tool registrations
```

### 與現有系統整合

```
┌─────────────────────────────────────────────────────────────────┐
│                    Citation Intelligence                         │
│                                                                  │
│  analyze_citation_needs() ──┬── Rule-based patterns             │
│                             └── spaCy NLP (optional)            │
│                                                                  │
│  find_supporting_references() ──┬── Local: semantic search      │
│                                 │   (sentence-transformers)     │
│                                 │                               │
│                                 └── Remote: pubmed-search MCP   │
│                                     GET /api/search             │
│                                                                  │
│  verify_citation_support() ──── Read reference abstract/fulltext │
│                                 from references/{pmid}/          │
│                                                                  │
│  write_paragraph_with_citations() ── Orchestrates above tools   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 實作計畫

### Phase 1.1: Foundation（Week 1）

- [ ] 建立 `citation_intelligence/` 模組結構
- [ ] 實作 `patterns.py` — 引用需求偵測規則
- [ ] 實作 `analyzer.py` — `analyze_citation_needs`
- [ ] 單元測試：各種句子類型的分類

### Phase 1.2: Search（Week 2）

- [ ] 實作 `reference_embedder.py` — 建立 embedding index
- [ ] 實作 `searcher.py` — `find_supporting_references`
- [ ] 整合 pubmed-search MCP 的 HTTP API
- [ ] 測試：本地搜尋 + PubMed 搜尋

### Phase 1.3: Verification（Week 3）

- [ ] 實作 `verifier.py` — `verify_citation_support`
- [ ] 設計 support_type 判斷邏輯
- [ ] 測試：各種支持/不支持情境

### Phase 1.4: Integration（Week 4）

- [ ] 實作 `write_paragraph_with_citations`
- [ ] 註冊 MCP tools
- [ ] 整合測試
- [ ] 更新文檔

---

## 🔮 未來擴展

### Phase 2: Coherence Engine

基於 Citation Intelligence 的經驗，擴展到連貫性：

- `generate_section_outline` — 段落級大綱
- `write_paragraph_with_context` — 帶上下文寫作
- `check_coherence` — 連貫性檢查

### Phase 3: Argument Tracker

- `create_argument_map` — 論點地圖（整合 CGU deep_think）
- `generate_structured_draft` — 結構化生成
- `track_logic_chain` — 邏輯鏈追蹤

---

## 📝 開放問題

1. **Embedding 模型選擇**

   - `all-MiniLM-L6-v2`：快速、輕量
   - `all-mpnet-base-v2`：更準確但較慢
   - 是否需要 fine-tune 醫學領域？

2. **引用驗證的深度**

   - 只看 abstract 夠嗎？
   - 如果有 fulltext PDF，如何處理？

3. **與 Agent 的互動模式**

   - 主動模式：寫作時自動呼叫
   - 被動模式：用戶/Agent 明確請求
   - 混合模式：關鍵步驟強制檢查

4. **效能考量**
   - Embedding index 要多久重建？
   - 是否需要增量更新？

---

## 📚 參考資源

- [Sentence-Transformers](https://www.sbert.net/)
- [spaCy](https://spacy.io/)
- [SciBERT](https://github.com/allenai/scibert) — 科學領域預訓練模型
- [PubMedBERT](https://huggingface.co/microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract) — 生醫領域模型
