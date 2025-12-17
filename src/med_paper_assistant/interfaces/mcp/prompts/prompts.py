"""
MCP Prompts Module - Minimal Agent Instructions

DESIGN PRINCIPLE:
- Prompts are instructions FOR THE AGENT, not text for the user to read
- Keep prompts minimal - just tell the agent what to do
- Agent should speak naturally to user, not display the prompt
- Use tools to gather info, then respond conversationally
"""

import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from mcp.types import PromptReference, Completion

from med_paper_assistant.infrastructure.services import TemplateReader
from med_paper_assistant.infrastructure.persistence import get_project_manager


def register_prompts(mcp: FastMCP, template_reader: TemplateReader):
    """Register all prompts with the MCP server."""
    
    # ========================================
    # Completion Handler for prompt arguments
    # ========================================
    @mcp.completion()
    async def handle_completion(ref, argument, context):
        """
        Provide autocomplete suggestions for prompt arguments.
        
        This enables IDE-like completion when users type prompt arguments.
        For example, when using /mdpaper.project, suggest existing project names.
        """
        pm = get_project_manager()
        
        # Handle prompt completions
        if isinstance(ref, PromptReference):
            prompt_name = ref.name
            arg_name = argument.name
            partial_value = argument.value or ""
            
            # /mdpaper.project - suggest existing projects
            if prompt_name == "project" and arg_name == "project_name":
                projects = pm.list_projects().get("projects", [])
                suggestions = []
                for p in projects:
                    slug = p.get("slug", "")
                    name = p.get("name", "")
                    # Filter by partial match
                    if partial_value.lower() in slug.lower() or partial_value.lower() in name.lower():
                        suggestions.append(slug)
                return Completion(
                    values=suggestions[:10],  # Max 10 suggestions
                    total=len(suggestions),
                    hasMore=len(suggestions) > 10
                )
            
            # /mdpaper.draft - suggest sections
            if prompt_name == "draft" and arg_name == "section":
                sections = ["Introduction", "Methods", "Results", "Discussion", "Abstract", "Conclusion", "all"]
                suggestions = [s for s in sections if partial_value.lower() in s.lower()]
                return Completion(values=suggestions)
            
            # /mdpaper.concept - no completion needed for topic (free text)
            # /mdpaper.strategy - no completion needed for keywords (free text)
        
        return None
    
    # ========================================
    # /mdpaper.project - Configure project
    # ========================================
    @mcp.prompt(name="project", description="Setup and configure a research project")
    def mdpaper_project(project_name: str = "") -> str:
        pm = get_project_manager()
        
        if project_name:
            # Check if project exists (completion would suggest existing ones)
            projects = pm.list_projects().get("projects", [])
            existing_slugs = [p.get("slug", "") for p in projects]
            
            if project_name in existing_slugs:
                # Existing project selected via completion
                return f"switch_project(slug=\"{project_name}\") then setup_project_interactive()"
            else:
                # New project name
                return f"create_project(name=\"{project_name}\") then setup_project_interactive()"
        
        return "setup_project_interactive()"

    # ========================================
    # /mdpaper.concept - Develop research concept
    # ========================================
    @mcp.prompt(name="concept", description="Develop research concept with literature-based gap analysis")
    def mdpaper_concept(topic: str) -> str:
        return f"""Topic: {topic}

🔍 文獻搜尋（使用 pubmed-search MCP）：
1. mcp_pubmed-search_search_literature(query=topic) → 搜尋相關文獻
2. mcp_pubmed-search_fetch_article_details(pmids) → 取得文章詳細資料
3. 分析 research gap，向用戶說明發現

📁 專案建立（使用 mdpaper MCP）：
4. mcp_mdpaper_create_project(name="...", paper_type="original") → 建立專案
5. mcp_mdpaper_save_reference(article=metadata) → 儲存關鍵參考文獻

📝 概念撰寫：
6. 使用 concept.md template 撰寫：
   - Research Question（明確的研究問題）
   - 🔒 NOVELTY STATEMENT（本研究的創新點 - 不可弱化）
   - 🔒 KEY SELLING POINTS（賣點清單 - 必須全部保留）
   - Gap Analysis（現有研究的不足）
   - Proposed Approach（預計方法）
7. mcp_mdpaper_write_draft(filename="concept.md", content=...) → 儲存

⚠️ 重要：🔒 標記的內容在後續撰寫中不可刪除或弱化！"""

    # ========================================
    # /mdpaper.strategy - Configure search strategy
    # ========================================
    @mcp.prompt(name="strategy", description="Configure search strategy")
    def mdpaper_strategy(keywords: str) -> str:
        return f"""Keywords: {keywords}
詢問: exclusions, year range, article types, sample size → configure_search_strategy()"""

    # ========================================
    # /mdpaper.search - Literature Exploration
    # ========================================
    @mcp.prompt(name="search", description="Smart literature search with context awareness")
    def mdpaper_search(topic: str = "") -> str:
        return f"""Topic: {topic or "（從 context 推斷或詢問用戶）"}

🔍 搜尋策略決策：

【情境 A】有 active project + concept.md：
1. mcp_mdpaper_get_current_project() → 確認專案
2. mcp_mdpaper_read_draft(filename="concept.md") → 提取關鍵字
3. 從 concept 提取：research question, PICO elements, key terms
4. 向用戶確認搜尋策略

【情境 B】無專案 / 純探索：
1. mcp_mdpaper_start_exploration() → 建立探索工作區
2. 詢問用戶搜尋條件

📚 執行搜尋（使用 pubmed-search MCP）：
- 快速搜尋：mcp_pubmed-search_search_literature(query=...)
- PICO 搜尋：mcp_pubmed-search_parse_pico() → 並行 generate_search_queries() → 組合 Boolean
- 精確搜尋：mcp_pubmed-search_generate_search_queries() → 取得 MeSH → 優化查詢
- 擴展搜尋：mcp_pubmed-search_find_related_articles() / find_citing_articles()

💾 儲存文獻（使用 mdpaper MCP）：
- mcp_pubmed-search_fetch_article_details(pmids) → 取得 metadata
- mcp_mdpaper_save_reference(article=metadata) → 儲存到專案

🎯 快捷選項（詢問用戶）：
- "快速找" → 直接 search_literature
- "精確找" → generate_search_queries + MeSH
- "PICO" → parse_pico workflow
- "相關論文" → 從已存的 reference 延伸

💡 Agent 協調 pubmed-search + mdpaper 是正確設計！"""

    # ========================================
    # /mdpaper.draft - Write paper section
    # ========================================
    @mcp.prompt(name="draft", description="Write paper draft")
    def mdpaper_draft(section: str) -> str:
        return f"""Section: {section}

⚠️ MANDATORY: validate_concept(concept.md) 必須先通過才能撰寫 draft！

Flow:
1. validate_concept(concept.md) → 確認通過（novelty score 75+, 3/3 rounds）
2. 如果驗證失敗 → 停止並要求用戶修正 concept
3. 驗證通過後 → read_draft(concept.md) 取得 🔒protected content
4. get_section_template({section}) → 取得寫作指南
5. draft_section() 或 write_draft() → 撰寫（必須保留 🔒 內容）
6. count_words() → 確認字數

🔒 Protected Content Rules:
- Introduction 必須體現 🔒 NOVELTY STATEMENT
- Discussion 必須強調 🔒 KEY SELLING POINTS  
- 修改 🔒 區塊前必須詢問用戶"""

    # ========================================
    # /mdpaper.analysis - Analyze data
    # ========================================
    @mcp.prompt(name="analysis", description="Analyze data")
    def mdpaper_data_analysis() -> str:
        return """Tools: analyze_dataset(), generate_table_one(), run_statistical_test(), create_plot()
先詢問用戶要分析哪個 CSV 和需要什麼分析"""

    # ========================================
    # /mdpaper.clarify - Refine content
    # ========================================
    @mcp.prompt(name="clarify", description="Refine content")
    def mdpaper_clarify() -> str:
        return """list_drafts() → 詢問要改進哪個 draft → read_draft() → 改進（尊重🔒區塊）→ write_draft()"""

    # ========================================
    # /mdpaper.format - Export to Word
    # ========================================
    @mcp.prompt(name="format", description="Export to Word")
    def mdpaper_format() -> str:
        return """read_template() → read_draft() → start_document_session() → insert_section() per section → verify_document() → save_document()"""
