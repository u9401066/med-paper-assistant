# 🗺️ MedPaper Assistant Roadmap

## Vision
成為醫學研究人員從文獻探索到論文發表的完整 AI 輔助平台。

---

## ✅ 已完成 (Completed)

### Phase 1: Core Features
| Feature | Description | Date |
|---------|-------------|------|
| PubMed Integration | 搜尋、下載、參考文獻管理 | 2025-10 |
| Draft Generation | 智慧草稿生成、引用插入 | 2025-10 |
| Word Export | 匯出符合期刊格式的 .docx | 2025-10 |
| Data Analysis | 統計分析、Table 1 生成 | 2025-11 |

### Phase 2: Advanced Features
| Feature | Description | Date |
|---------|-------------|------|
| Multi-Project | 多專案管理、Exploration 模式 | 2025-11 |
| Novelty Validation | 研究概念原創性驗證 | 2025-11 |
| Draw.io Integration | CONSORT/PRISMA 流程圖 | 2025-11 |
| Skills System | AI 工作流程引導 (.skills/) | 2025-12-01 |
| Parallel Search | 並行搜尋、策略整合 | 2025-12-01 |
| WebSocket Sync | 即時雙向通訊 | 2025-12-01 |
| Dashboard | 專案管理 UI | 2025-12-02 |
| pubmed-search-mcp | 獨立 PubMed MCP 伺服器 | 2025-12-02 |

### Phase 3: Knowledge Management
| Feature | Description | Date |
|---------|-------------|------|
| Foam Integration | Wikilinks、Hover Preview、Backlinks | 2025-12-03 |
| Citation Keys | `author_year_pmid` 格式 | 2025-12-03 |
| Project File Mgmt | Dashboard 專案切換增強 | 2025-12-03 |

---

## 🔜 進行中 (In Progress)

| Feature | Description | Priority |
|---------|-------------|----------|
| Journal Style Library | 主要期刊的預設格式 | High |
| Multi-language UI | 完整本地化 | Medium |

---

## 📋 規劃中 (Planned)

### Phase 4: API & Deployment
**參考 medical-calc-mcp 的部署架構**

| Feature | Description | Use Case |
|---------|-------------|----------|
| **REST API Mode** | 將 MCP 工具以 API 公開 | 外部系統整合 |
| SSE Mode | Server-Sent Events 支援 | 輕量即時通訊 |
| Docker Support | 容器化部署 | 一鍵啟動 |
| HTTPS + Nginx | 生產環境安全部署 | 團隊使用 |

**架構:**
```
┌─────────────────────────────────────────────────────────────┐
│                    Deployment Modes                          │
├─────────────────┬─────────────────┬─────────────────────────┤
│   MCP (stdio)   │   SSE (:8000)   │   REST API (:8080)      │
│   VS Code       │   Claude        │   External Apps         │
└─────────────────┴─────────────────┴─────────────────────────┘
```

### Phase 5: Collaboration & Review

| Feature | Description |
|---------|-------------|
| **Multi-Author Mode** | 多人協作、版本控制 |
| **AI Review** | LLM 審稿、改進建議 |
| **Dashboard File Browser** | Chonky 檔案瀏覽器 |
| **Reference Graph** | 文獻引用關係視覺化 |

---

## 💡 構想中 (Ideas)

參考 medical-calc-mcp 的優秀設計:

| Idea | Description | Inspired By |
|------|-------------|-------------|
| **Tool Discovery** | 兩層級工具索引 (Low/High Level) | medical-calc-mcp 的工具分類 |
| **Validation Layer** | 3 層驗證 (MCP/Application/Domain) | 確保資料品質 |
| **Resources API** | `paper://list`, `reference://{pmid}` | 結構化資源訪問 |
| **Prompts Library** | 預定義的研究流程 Prompts | 引導新手研究人員 |

---

## 🔗 Related Projects

| Project | Description | Status |
|---------|-------------|--------|
| [pubmed-search-mcp](https://github.com/u9401066/pubmed-search-mcp) | PubMed 文獻搜尋 MCP | ✅ Integrated |
| [next-ai-draw-io](https://github.com/u9401066/next-ai-draw-io) | Draw.io 流程圖 MCP | ✅ Integrated |
| [medical-calc-mcp](https://github.com/u9401066/medical-calc-mcp) | 醫學計算器 MCP | 📋 Planned |

---

## Contributing

有興趣參與開發？歡迎：
- 🐛 回報問題
- 💡 提出功能建議
- 🔧 提交 Pull Request

詳見 [CONTRIBUTING.md](CONTRIBUTING.md)
