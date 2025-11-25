import json
import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class SearchCriteria(BaseModel):
    keywords: List[str]
    exclusions: List[str] = []
    article_types: List[str] = []  # e.g., "Clinical Trial", "Review", "Meta-Analysis"
    min_sample_size: Optional[int] = None
    date_range: Optional[str] = None # e.g., "2020:2025"

class StrategyManager:
    def __init__(self, strategy_file: str = "search_strategy.json"):
        self.strategy_file = strategy_file

    def save_strategy(self, criteria: Dict[str, Any]) -> str:
        """
        Save the search strategy to a JSON file.
        """
        try:
            # Validate with Pydantic
            model = SearchCriteria(**criteria)
            with open(self.strategy_file, "w", encoding="utf-8") as f:
                json.dump(model.dict(), f, indent=2)
            return f"Strategy saved to {self.strategy_file}"
        except Exception as e:
            return f"Error saving strategy: {str(e)}"

    def load_strategy(self) -> Optional[SearchCriteria]:
        """
        Load the search strategy from the JSON file.
        """
        if not os.path.exists(self.strategy_file):
            return None
        try:
            with open(self.strategy_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SearchCriteria(**data)
        except Exception:
            return None

    def build_pubmed_query(self, criteria: SearchCriteria) -> str:
        """
        Construct a PubMed query string from the criteria.
        """
        # 1. Keywords (OR within list if synonyms, but here we assume AND for distinct concepts)
        # For simplicity, let's assume the user provides distinct concepts to AND together.
        # If the user provides "cancer OR tumor", that should be one string in the list.
        query_parts = []
        
        if criteria.keywords:
            # Join keywords with AND
            keywords_str = " AND ".join([f"({k})" for k in criteria.keywords])
            query_parts.append(keywords_str)
            
        # 2. Exclusions
        if criteria.exclusions:
            exclusions_str = " NOT ".join([f"({k})" for k in criteria.exclusions])
            query_parts.append(f"NOT ({exclusions_str})")
            
        # 3. Article Types
        if criteria.article_types:
            types_str = " OR ".join([f"\"{t}\"[pt]" for t in criteria.article_types])
            query_parts.append(f"AND ({types_str})")
            
        # 4. Date Range
        if criteria.date_range:
            # Format: YYYY:YYYY
            query_parts.append(f"AND {criteria.date_range}[dp]")
            
        return " ".join(query_parts)
