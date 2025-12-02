"""
PubMed Search Tools

search_literature, find_related_articles, find_citing_articles, search strategy
"""

import json
from mcp.server.fastmcp import FastMCP

from pubmed_search import PubMedClient
from med_paper_assistant.infrastructure.services import StrategyManager
from med_paper_assistant.infrastructure.logging import setup_logger

logger = setup_logger()


def format_search_results(results: list, include_doi: bool = True) -> str:
    """Format search results for display."""
    if not results:
        return "No results found."
        
    if "error" in results[0]:
        return f"Error searching PubMed: {results[0]['error']}"
        
    formatted_output = f"Found {len(results)} results:\n\n"
    for i, paper in enumerate(results, 1):
        formatted_output += f"{i}. **{paper['title']}**\n"
        authors = paper.get('authors', [])
        formatted_output += f"   Authors: {', '.join(authors[:3])}{' et al.' if len(authors) > 3 else ''}\n"
        journal = paper.get('journal', 'Unknown Journal')
        year = paper.get('year', '')
        volume = paper.get('volume', '')
        pages = paper.get('pages', '')
        
        journal_info = f"{journal} ({year})"
        if volume:
            journal_info += f"; {volume}"
            if pages:
                journal_info += f": {pages}"
        formatted_output += f"   Journal: {journal_info}\n"
        formatted_output += f"   PMID: {paper.get('pmid', '')}"
        
        if include_doi and paper.get('doi'):
            formatted_output += f" | DOI: {paper['doi']}"
        if paper.get('pmc_id'):
            formatted_output += f" | PMC: {paper['pmc_id']} 📄"
        
        formatted_output += "\n"
        
        abstract = paper.get('abstract', '')
        if abstract:
            formatted_output += f"   Abstract: {abstract[:200]}...\n"
        formatted_output += "\n"
        
    return formatted_output


def register_pubmed_tools(mcp: FastMCP, searcher: PubMedClient, strategy_manager: StrategyManager):
    """Register PubMed search tools."""
    
    @mcp.tool()
    def configure_search_strategy(criteria_json: str) -> str:
        """
        Save a structured search strategy.
        
        Args:
            criteria_json: JSON string with keys: keywords (list), exclusions (list), 
                          article_types (list), min_sample_size (int), date_range (str).
        """
        try:
            criteria = json.loads(criteria_json)
            return strategy_manager.save_strategy(criteria)
        except Exception as e:
            return f"Error configuring strategy: {str(e)}"

    @mcp.tool()
    def get_search_strategy() -> str:
        """Get the currently saved search strategy."""
        strategy = strategy_manager.load_strategy()
        if not strategy:
            return "No strategy saved."
        return json.dumps(strategy.dict(), indent=2)

    @mcp.tool()
    def search_literature(
        query: str = "", 
        limit: int = 5, 
        min_year: int = None, 
        max_year: int = None,
        date_from: str = None,
        date_to: str = None,
        date_type: str = "edat",
        article_type: str = None, 
        strategy: str = "relevance", 
        use_saved_strategy: bool = False
    ) -> str:
        """
        Search for medical literature based on a query using PubMed.
        
        Args:
            query: The search query (e.g., "diabetes treatment guidelines"). 
                   Required if use_saved_strategy is False.
            limit: The maximum number of results to return.
            min_year: Optional minimum publication year (e.g., 2020).
            max_year: Optional maximum publication year.
            date_from: Precise start date in YYYY/MM/DD format (e.g., "2025/10/01").
                       More precise than min_year. If provided, overrides min_year.
            date_to: Precise end date in YYYY/MM/DD format (e.g., "2025/11/28").
                     More precise than max_year. If provided, overrides max_year.
            date_type: Which date field to search. Options:
                       - "edat" (default): Entrez date - when added to PubMed (best for NEW articles)
                       - "pdat": Publication date
                       - "mdat": Modification date
            article_type: Optional article type (e.g., "Review", "Clinical Trial", "Meta-Analysis").
            strategy: Search strategy ("recent", "most_cited", "relevance", "impact", "agent_decided"). 
                     Default is "relevance".
            use_saved_strategy: If True, uses the criteria from configure_search_strategy.
        """
        logger.info(f"Searching literature: query='{query}', limit={limit}, strategy='{strategy}'")
        try:
            min_sample_size = None
            
            if use_saved_strategy:
                saved_criteria = strategy_manager.load_strategy()
                if saved_criteria:
                    query = strategy_manager.build_pubmed_query(saved_criteria)
                    min_sample_size = saved_criteria.min_sample_size
                    logger.info(f"Using saved strategy. Generated query: {query}")
                else:
                    return "Error: No saved strategy found. Please use configure_search_strategy first."
            
            if not query:
                return "Error: Query is required unless use_saved_strategy is True and a strategy is saved."

            results = searcher.search(
                query, limit, min_year, max_year, 
                article_type, strategy,
                date_from=date_from, date_to=date_to, date_type=date_type
            )
            
            if min_sample_size:
                results = searcher.filter_results(results, min_sample_size)
                
            return format_search_results(results[:limit])
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return f"Error: {e}"

    @mcp.tool()
    def find_related_articles(pmid: str, limit: int = 5) -> str:
        """
        Find articles related to a given PubMed article.
        Uses PubMed's "Related Articles" feature to find similar papers.
        
        Args:
            pmid: PubMed ID of the source article.
            limit: Maximum number of related articles to return.
            
        Returns:
            List of related articles with details.
        """
        logger.info(f"Finding related articles for PMID: {pmid}")
        try:
            results = searcher.get_related_articles(pmid, limit)
            
            if not results:
                return f"No related articles found for PMID {pmid}."
            
            if "error" in results[0]:
                return f"Error finding related articles: {results[0]['error']}"
            
            output = f"📚 **Related Articles for PMID {pmid}** ({len(results)} found)\n\n"
            output += format_search_results(results)
            return output
        except Exception as e:
            logger.error(f"Find related articles failed: {e}")
            return f"Error: {e}"

    @mcp.tool()
    def find_citing_articles(pmid: str, limit: int = 10) -> str:
        """
        Find articles that cite a given PubMed article.
        Uses PubMed Central's citation data to find papers that reference this article.
        
        Args:
            pmid: PubMed ID of the source article.
            limit: Maximum number of citing articles to return.
            
        Returns:
            List of citing articles with details.
        """
        logger.info(f"Finding citing articles for PMID: {pmid}")
        try:
            results = searcher.get_citing_articles(pmid, limit)
            
            if not results:
                return f"No citing articles found for PMID {pmid}. (Article may not be indexed in PMC or has no citations yet.)"
            
            if "error" in results[0]:
                return f"Error finding citing articles: {results[0]['error']}"
            
            output = f"📖 **Articles Citing PMID {pmid}** ({len(results)} found)\n\n"
            output += format_search_results(results)
            return output
        except Exception as e:
            logger.error(f"Find citing articles failed: {e}")
            return f"Error: {e}"

    @mcp.tool()
    def generate_search_queries(
        topic: str,
        strategy: str = "comprehensive",
        include_mesh: bool = True,
        include_synonyms: bool = True,
        use_saved_strategy: bool = True
    ) -> str:
        """
        根據主題生成多組搜尋語法，供並行搜尋使用。
        
        這個工具返回多個搜尋 queries，Agent 應該**並行呼叫** search_literature
        對每個 query 執行搜尋，然後使用 merge_search_results 合併結果。
        
        Args:
            topic: 搜尋主題（如 "remimazolam ICU sedation"）
            strategy: 搜尋策略
                - "comprehensive": 全面搜尋，多組不同角度的 queries
                - "focused": 精確搜尋，較少但更精確的 queries  
                - "exploratory": 探索性搜尋，包含更廣泛的相關概念
            include_mesh: 是否包含 MeSH 詞彙的搜尋
            include_synonyms: 是否包含同義詞/別名
            use_saved_strategy: 是否使用已儲存的搜尋策略（date_range, exclusions, article_types）
            
        Returns:
            JSON 格式的搜尋策略，包含多個 queries 供並行執行
        """
        logger.info(f"Generating search queries for topic: {topic}, strategy: {strategy}")
        
        # 載入已儲存的策略設定
        saved_strategy = None
        date_filter = ""
        exclusion_filter = ""
        article_type_filter = ""
        
        if use_saved_strategy:
            saved_strategy = strategy_manager.load_strategy()
            if saved_strategy:
                logger.info(f"Using saved strategy: {saved_strategy}")
                
                # 處理日期範圍
                if saved_strategy.date_range:
                    # 支援格式: "2020-2024" 或 "5 years" 或 "last 10 years"
                    dr = saved_strategy.date_range.lower()
                    if "-" in dr and len(dr.split("-")) == 2:
                        parts = dr.split("-")
                        if parts[0].isdigit() and parts[1].isdigit():
                            date_filter = f" AND ({parts[0]}:{parts[1]}[dp])"
                    elif "year" in dr:
                        import re
                        match = re.search(r'(\d+)\s*year', dr)
                        if match:
                            years = int(match.group(1))
                            from datetime import datetime
                            current_year = datetime.now().year
                            start_year = current_year - years
                            date_filter = f" AND ({start_year}:{current_year}[dp])"
                
                # 處理排除詞
                if saved_strategy.exclusions:
                    exclusions = [f'NOT "{ex}"' for ex in saved_strategy.exclusions]
                    exclusion_filter = " " + " ".join(exclusions)
                
                # 處理文章類型
                if saved_strategy.article_types:
                    types = [f'"{t}"[Publication Type]' for t in saved_strategy.article_types]
                    article_type_filter = f" AND ({' OR '.join(types)})"
        
        # 解析主題詞彙
        words = topic.lower().split()
        
        # 建立過濾器字串（用於追加到每個查詢）
        filters = f"{date_filter}{article_type_filter}{exclusion_filter}".strip()
        
        queries = []
        
        # Query 1: 精確標題搜尋
        base_q1 = f"({topic})[Title]"
        queries.append({
            "id": "q1_title",
            "query": f"{base_q1}{filters}" if filters else base_q1,
            "purpose": "精確標題匹配",
            "expected": "高相關性，較少結果"
        })
        
        # Query 2: 標題/摘要搜尋
        base_q2 = f"({topic})[Title/Abstract]"
        queries.append({
            "id": "q2_tiab",
            "query": f"{base_q2}{filters}" if filters else base_q2,
            "purpose": "標題或摘要包含關鍵字",
            "expected": "中等相關性，適量結果"
        })
        
        # Query 3: 組合詞搜尋（用 AND 連接）
        and_query = " AND ".join(words)
        base_q3 = f"({and_query})"
        queries.append({
            "id": "q3_and",
            "query": f"{base_q3}{filters}" if filters else and_query,
            "purpose": "所有關鍵字都必須出現",
            "expected": "較嚴格的篩選"
        })
        
        if strategy in ["comprehensive", "exploratory"]:
            # Query 4: 部分詞彙搜尋（擴展）
            if len(words) >= 2:
                # 取主要詞彙組合
                main_word = words[0]
                context_words = " OR ".join(words[1:])
                base_q4 = f"({main_word} AND ({context_words}))"
                queries.append({
                    "id": "q4_partial",
                    "query": f"{base_q4}{filters}" if filters else f"{main_word} AND ({context_words})",
                    "purpose": "主要詞彙 + 任一情境詞",
                    "expected": "較寬鬆的匹配"
                })
        
        if include_mesh:
            # Query 5: MeSH 詞彙搜尋
            base_q5 = f"({topic})[MeSH Terms]"
            queries.append({
                "id": "q5_mesh",
                "query": f"{base_q5}{filters}" if filters else base_q5,
                "purpose": "使用 MeSH 標準詞彙",
                "expected": "醫學概念標準化匹配"
            })
        
        if strategy == "exploratory":
            # Query 6: 相關概念擴展
            # 這裡可以加入更多領域知識
            base_q6 = f"({words[0]})[Title] AND review[Publication Type]"
            queries.append({
                "id": "q6_broad",
                "query": f"{base_q6}{date_filter}{exclusion_filter}" if (date_filter or exclusion_filter) else base_q6,
                "purpose": "找相關的 Review 文章",
                "expected": "了解領域全貌"
            })
        
        # 構建結果
        result = {
            "topic": topic,
            "strategy": strategy,
            "queries_count": len(queries),
            "queries": queries,
            "instruction": "請並行呼叫 search_literature 對每個 query 執行搜尋，" +
                          "然後呼叫 merge_search_results 合併結果。",
            "example": {
                "parallel_calls": [
                    f"search_literature(query=\"{q['query']}\", limit=20)" 
                    for q in queries[:2]
                ] + ["..."]
            }
        }
        
        # 加入已應用的策略資訊
        if saved_strategy:
            result["applied_strategy"] = {
                "date_range": saved_strategy.date_range or "not set",
                "exclusions": saved_strategy.exclusions or [],
                "article_types": saved_strategy.article_types or [],
                "note": "已儲存的搜尋策略已自動整合到查詢中"
            }
        else:
            result["applied_strategy"] = None
            result["tip"] = "可使用 configure_search_strategy 設定日期範圍、排除詞等，下次生成查詢時會自動套用"
        
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool()
    def merge_search_results(results_json: str) -> str:
        """
        合併多個搜尋結果並去重。
        
        在並行執行多個 search_literature 後，使用此工具合併結果。
        
        Args:
            results_json: JSON 格式的搜尋結果陣列，每個元素包含：
                - query_id: 搜尋 ID（對應 generate_search_queries 返回的 id）
                - pmids: PMID 列表
                
                例如：
                [
                    {"query_id": "q1_title", "pmids": ["12345", "67890"]},
                    {"query_id": "q2_tiab", "pmids": ["67890", "11111"]}
                ]
                
        Returns:
            合併後的結果，包含去重後的 PMID 列表和來源分析
        """
        logger.info("Merging search results")
        
        try:
            results = json.loads(results_json)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON format - {e}"
        
        # 收集所有 PMID 和來源
        pmid_sources = {}  # pmid -> [source_ids]
        all_pmids = []
        
        for result in results:
            query_id = result.get("query_id", "unknown")
            pmids = result.get("pmids", [])
            
            for pmid in pmids:
                pmid = str(pmid).strip()
                if pmid not in pmid_sources:
                    pmid_sources[pmid] = []
                    all_pmids.append(pmid)
                pmid_sources[pmid].append(query_id)
        
        # 分析結果
        multi_source = {pmid: sources for pmid, sources in pmid_sources.items() if len(sources) > 1}
        single_source = {pmid: sources[0] for pmid, sources in pmid_sources.items() if len(sources) == 1}
        
        # 按來源分組
        by_query = {}
        for result in results:
            query_id = result.get("query_id", "unknown")
            by_query[query_id] = len(result.get("pmids", []))
        
        output = {
            "total_unique": len(all_pmids),
            "total_with_duplicates": sum(by_query.values()),
            "duplicates_removed": sum(by_query.values()) - len(all_pmids),
            "by_query": by_query,
            "appeared_in_multiple_queries": {
                "count": len(multi_source),
                "pmids": list(multi_source.keys())[:10],  # 只顯示前 10 個
                "note": "這些文獻被多個搜尋策略找到，可能更相關"
            },
            "unique_pmids": all_pmids,
            "next_step": "使用 save_reference(pmid=...) 儲存感興趣的文獻，" +
                        "或使用 get_reference_details(pmid=...) 取得詳細資訊",
            "need_more": "如果結果不夠，使用 expand_search_queries 生成更多搜尋策略"
        }
        
        return json.dumps(output, indent=2, ensure_ascii=False)

    @mcp.tool()
    def expand_search_queries(
        topic: str,
        existing_query_ids: str = "",
        expansion_type: str = "synonyms",
        use_saved_strategy: bool = True
    ) -> str:
        """
        擴展搜尋查詢，當初始搜尋結果不夠時使用。
        
        這個工具生成**額外的**搜尋策略，與初始查詢不重複。
        適合在 generate_search_queries + merge_search_results 後，
        發現結果不夠時使用。
        
        Args:
            topic: 原始搜尋主題
            existing_query_ids: 已執行的查詢 ID（逗號分隔），避免重複
                              例如："q1_title,q2_tiab,q3_and"
            expansion_type: 擴展類型
                - "synonyms": 同義詞擴展（如 sedation → conscious sedation, procedural sedation）
                - "related": 相關概念（如 ICU → critical care, intensive care）
                - "broader": 更廣泛的搜尋（放寬限制）
                - "narrower": 更精確的搜尋（加強限制）
                - "author": 搜尋關鍵作者的其他文獻
                - "citation": 基於已找到文獻的引用網絡
            use_saved_strategy: 是否套用已儲存的搜尋策略
            
        Returns:
            新的搜尋查詢，可並行執行後與之前結果合併
        """
        logger.info(f"Expanding search for topic: {topic}, type: {expansion_type}")
        
        # 解析已執行的查詢
        existing = set(existing_query_ids.split(",")) if existing_query_ids else set()
        
        # 載入策略設定
        filters = ""
        if use_saved_strategy:
            saved_strategy = strategy_manager.load_strategy()
            if saved_strategy:
                date_filter = ""
                exclusion_filter = ""
                article_type_filter = ""
                
                if saved_strategy.date_range:
                    dr = saved_strategy.date_range.lower()
                    if "-" in dr and len(dr.split("-")) == 2:
                        parts = dr.split("-")
                        if parts[0].isdigit() and parts[1].isdigit():
                            date_filter = f" AND ({parts[0]}:{parts[1]}[dp])"
                
                if saved_strategy.exclusions:
                    exclusions = [f'NOT "{ex}"' for ex in saved_strategy.exclusions]
                    exclusion_filter = " " + " ".join(exclusions)
                
                if saved_strategy.article_types:
                    types = [f'"{t}"[Publication Type]' for t in saved_strategy.article_types]
                    article_type_filter = f" AND ({' OR '.join(types)})"
                
                filters = f"{date_filter}{article_type_filter}{exclusion_filter}".strip()
        
        words = topic.lower().split()
        queries = []
        query_counter = len(existing) + 1
        
        if expansion_type == "synonyms":
            # 生成同義詞擴展查詢
            # 常見醫學同義詞對照
            synonym_map = {
                "sedation": ["conscious sedation", "procedural sedation", "moderate sedation", "deep sedation"],
                "icu": ["intensive care unit", "critical care unit", "CCU"],
                "anesthesia": ["anaesthesia", "anesthetic", "anaesthetic"],
                "pain": ["analgesia", "analgesic", "nociception"],
                "surgery": ["surgical", "operative", "perioperative", "intraoperative"],
                "ventilation": ["mechanical ventilation", "respiratory support", "ventilator"],
                "hypotension": ["low blood pressure", "hemodynamic instability"],
                "mortality": ["death", "survival", "fatality"],
                "prediction": ["predictive", "prognostic", "forecasting"],
                "machine learning": ["ML", "artificial intelligence", "AI", "deep learning", "neural network"],
            }
            
            for word in words:
                word_lower = word.lower()
                if word_lower in synonym_map:
                    for synonym in synonym_map[word_lower][:2]:  # 取前 2 個同義詞
                        new_topic = topic.replace(word, synonym)
                        query_id = f"q{query_counter}_syn_{word_lower[:3]}"
                        if query_id not in existing:
                            base_q = f"({new_topic})[Title/Abstract]"
                            queries.append({
                                "id": query_id,
                                "query": f"{base_q}{filters}" if filters else base_q,
                                "purpose": f"同義詞擴展: {word} → {synonym}",
                                "expected": "找到使用不同術語的相關文獻"
                            })
                            query_counter += 1
                            
        elif expansion_type == "related":
            # 相關概念擴展
            related_concepts = {
                "sedation": ["analgesia", "anxiolysis", "hypnotic"],
                "icu": ["emergency department", "operating room", "PACU", "ward"],
                "anesthesia": ["sedation", "regional block", "nerve block"],
                "remimazolam": ["midazolam", "propofol", "dexmedetomidine", "benzodiazepine"],
                "propofol": ["remimazolam", "etomidate", "ketamine"],
                "hypotension": ["bradycardia", "tachycardia", "arrhythmia", "shock"],
            }
            
            for word in words:
                word_lower = word.lower()
                if word_lower in related_concepts:
                    for related in related_concepts[word_lower][:2]:
                        other_words = [w for w in words if w.lower() != word_lower]
                        if other_words:
                            new_topic = f"{related} {' '.join(other_words)}"
                            query_id = f"q{query_counter}_rel_{word_lower[:3]}"
                            if query_id not in existing:
                                base_q = f"({new_topic})[Title/Abstract]"
                                queries.append({
                                    "id": query_id,
                                    "query": f"{base_q}{filters}" if filters else base_q,
                                    "purpose": f"相關概念: {word} → {related}",
                                    "expected": "找到相關但不同主題的文獻"
                                })
                                query_counter += 1
                                
        elif expansion_type == "broader":
            # 更廣泛的搜尋（放寬限制）
            # 使用 OR 而非 AND
            if len(words) >= 2:
                or_query = " OR ".join(words)
                query_id = f"q{query_counter}_broad_or"
                if query_id not in existing:
                    queries.append({
                        "id": query_id,
                        "query": f"({or_query})[Title/Abstract]{filters}",
                        "purpose": "放寬搜尋：任一關鍵字",
                        "expected": "更多結果，相關性可能較低"
                    })
                    query_counter += 1
            
            # 只用主要詞彙
            main_word = words[0]
            query_id = f"q{query_counter}_broad_main"
            if query_id not in existing:
                queries.append({
                    "id": query_id,
                    "query": f"({main_word})[Title]{filters}",
                    "purpose": f"只搜尋主要詞彙: {main_word}",
                    "expected": "更廣泛的結果"
                })
                query_counter += 1
                
            # 移除日期限制（如果有的話）
            if filters and "[dp]" in filters:
                no_date_filters = filters.split(" AND ")[0]  # 移除日期部分
                query_id = f"q{query_counter}_broad_nodate"
                if query_id not in existing:
                    queries.append({
                        "id": query_id,
                        "query": f"({topic})[Title/Abstract]",  # 無日期限制
                        "purpose": "移除日期限制",
                        "expected": "包含較舊的文獻"
                    })
                    query_counter += 1
                    
        elif expansion_type == "narrower":
            # 更精確的搜尋
            # 加入更多限制
            query_id = f"q{query_counter}_narrow_rct"
            if query_id not in existing:
                queries.append({
                    "id": query_id,
                    "query": f"({topic})[Title] AND (randomized controlled trial[pt] OR RCT[tiab]){filters}",
                    "purpose": "限定 RCT 研究",
                    "expected": "高品質證據"
                })
                query_counter += 1
            
            query_id = f"q{query_counter}_narrow_meta"
            if query_id not in existing:
                queries.append({
                    "id": query_id,
                    "query": f"({topic})[Title/Abstract] AND (meta-analysis[pt] OR systematic review[pt]){filters}",
                    "purpose": "限定 Meta-analysis/SR",
                    "expected": "綜合性證據"
                })
                query_counter += 1
                
            query_id = f"q{query_counter}_narrow_recent"
            if query_id not in existing:
                from datetime import datetime
                current_year = datetime.now().year
                queries.append({
                    "id": query_id,
                    "query": f"({topic})[Title] AND ({current_year-2}:{current_year}[dp])",
                    "purpose": "限定最近 2 年",
                    "expected": "最新研究"
                })
                query_counter += 1
        
        # 如果沒有生成任何查詢，提供預設擴展
        if not queries:
            # 使用萬用卡擴展
            query_id = f"q{query_counter}_wildcard"
            queries.append({
                "id": query_id,
                "query": f"({words[0]}*)[Title/Abstract]{filters}",
                "purpose": "萬用卡擴展",
                "expected": "包含詞幹變化"
            })
            query_counter += 1
            
            # 使用 All Fields
            query_id = f"q{query_counter}_allfields"
            queries.append({
                "id": query_id,
                "query": f"({topic})[All Fields]{filters}",
                "purpose": "搜尋所有欄位",
                "expected": "最廣泛的搜尋"
            })
        
        result = {
            "topic": topic,
            "expansion_type": expansion_type,
            "existing_queries": list(existing),
            "new_queries_count": len(queries),
            "queries": queries,
            "instruction": "請並行執行這些新查詢，然後將結果與之前的結果一起傳給 merge_search_results",
            "available_expansion_types": [
                {"type": "synonyms", "description": "同義詞擴展"},
                {"type": "related", "description": "相關概念"},
                {"type": "broader", "description": "放寬限制"},
                {"type": "narrower", "description": "更精確搜尋"},
            ]
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
