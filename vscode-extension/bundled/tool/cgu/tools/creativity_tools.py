"""
CGU v3: Agent-Driven Creativity Tools

核心思路轉變：
- 不是「給 Agent 創意方法論的 Prompt」
- 而是「給 Agent 工具，讓它自己探索出創意」

這些工具讓 Agent 可以：
1. 搜尋概念空間
2. 發現意外連結
3. 驗證新穎度
4. 迭代改進

Agent 自己決定怎麼用這些工具，而不是我們規定流程。
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================
# Tool 1: 概念搜尋器 (Concept Explorer)
# ============================================================

@dataclass
class ConceptSearchResult:
    """概念搜尋結果"""
    query: str
    found_concepts: list[str]
    related_domains: list[str]
    unexpected_finds: list[str]  # 意外發現（跨域的）


class ConceptExplorer:
    """
    概念探索工具
    
    Agent 可以用這個工具搜尋概念空間，
    發現相關概念、跨域概念、意外連結。
    """
    
    def __init__(self):
        # 簡單的概念知識庫（實際應連接外部 KB）
        self.knowledge_base: dict[str, dict] = {
            # 科技
            "AI": {"domain": "科技", "related": ["機器學習", "神經網路", "自動化", "數據"], "cross": ["創意", "藝術", "醫療"]},
            "程式設計": {"domain": "科技", "related": ["演算法", "Debug", "重構", "軟體"], "cross": ["音樂", "寫作", "建築"]},
            "自動化": {"domain": "科技", "related": ["機器人", "流程", "效率"], "cross": ["農業", "製造", "服務"]},
            
            # 商業
            "創業": {"domain": "商業", "related": ["商業模式", "融資", "市場"], "cross": ["藝術", "科學", "社會"]},
            "行銷": {"domain": "商業", "related": ["品牌", "廣告", "用戶"], "cross": ["心理學", "社會學", "藝術"]},
            
            # 自然
            "生態": {"domain": "自然", "related": ["環境", "永續", "循環"], "cross": ["城市", "經濟", "社會"]},
            "演化": {"domain": "自然", "related": ["適應", "選擇", "突變"], "cross": ["商業", "技術", "文化"]},
            
            # 人文
            "教育": {"domain": "人文", "related": ["學習", "知識", "成長"], "cross": ["遊戲", "科技", "藝術"]},
            "創意": {"domain": "人文", "related": ["想像", "創新", "藝術"], "cross": ["科技", "商業", "科學"]},
            
            # 社會
            "遠端工作": {"domain": "社會", "related": ["協作", "效率", "孤獨", "彈性"], "cross": ["咖啡廳", "游牧", "儀式"]},
            "社群": {"domain": "社會", "related": ["歸屬", "連結", "文化"], "cross": ["遊戲", "宗教", "部落"]},
        }
    
    def search(self, query: str, include_cross_domain: bool = True) -> ConceptSearchResult:
        """
        搜尋概念
        
        Agent 可以：
        - 搜尋任何概念
        - 選擇是否要跨域結果
        - 發現意外連結
        """
        result = ConceptSearchResult(
            query=query,
            found_concepts=[],
            related_domains=[],
            unexpected_finds=[],
        )
        
        # 直接匹配
        if query in self.knowledge_base:
            kb_entry = self.knowledge_base[query]
            result.found_concepts = kb_entry.get("related", [])
            result.related_domains = [kb_entry.get("domain", "unknown")]
            if include_cross_domain:
                result.unexpected_finds = kb_entry.get("cross", [])
        else:
            # 模糊搜尋
            for concept, data in self.knowledge_base.items():
                if query.lower() in concept.lower() or concept.lower() in query.lower():
                    result.found_concepts.append(concept)
                    result.found_concepts.extend(data.get("related", [])[:2])
                    if include_cross_domain:
                        result.unexpected_finds.extend(data.get("cross", [])[:1])
        
        # 去重
        result.found_concepts = list(set(result.found_concepts))
        result.unexpected_finds = list(set(result.unexpected_finds))
        
        return result
    
    def random_concept(self, exclude: list[str] | None = None) -> str:
        """
        隨機取得一個概念
        
        Agent 可以用這個來「隨機探索」
        """
        exclude = exclude or []
        candidates = [c for c in self.knowledge_base.keys() if c not in exclude]
        return random.choice(candidates) if candidates else "unknown"


# ============================================================
# Tool 2: 連結發現器 (Connection Finder)
# ============================================================

@dataclass
class Connection:
    """一個連結"""
    concept_a: str
    concept_b: str
    connection_type: str  # "direct", "indirect", "unexpected"
    path: list[str]
    explanation: str
    novelty_score: float  # 0-1, 越高越新穎


class ConnectionFinder:
    """
    連結發現工具
    
    Agent 可以用這個工具找兩個概念之間的連結，
    包括直接連結和意外連結。
    """
    
    def __init__(self, concept_explorer: ConceptExplorer | None = None):
        self.explorer = concept_explorer or ConceptExplorer()
        self._connection_cache: dict[str, Connection] = {}
    
    def find_connection(self, concept_a: str, concept_b: str) -> Connection | None:
        """
        尋找兩個概念之間的連結
        
        Agent 可以：
        - 查找任意兩個概念的關係
        - 獲得連結路徑和解釋
        - 獲得新穎度評分
        """
        cache_key = f"{concept_a}|{concept_b}"
        if cache_key in self._connection_cache:
            return self._connection_cache[cache_key]
        
        # 搜尋兩個概念
        result_a = self.explorer.search(concept_a)
        result_b = self.explorer.search(concept_b)
        
        # 檢查直接連結
        if concept_b in result_a.found_concepts or concept_a in result_b.found_concepts:
            connection = Connection(
                concept_a=concept_a,
                concept_b=concept_b,
                connection_type="direct",
                path=[concept_a, concept_b],
                explanation=f"「{concept_a}」和「{concept_b}」直接相關",
                novelty_score=0.2,  # 直接連結不新穎
            )
        # 檢查跨域連結（意外連結）
        elif concept_b in result_a.unexpected_finds or concept_a in result_b.unexpected_finds:
            connection = Connection(
                concept_a=concept_a,
                concept_b=concept_b,
                connection_type="unexpected",
                path=[concept_a, "跨域橋接", concept_b],
                explanation=f"「{concept_a}」和「{concept_b}」來自不同領域，但有潛在連結",
                novelty_score=0.8,  # 跨域連結很新穎
            )
        # 檢查間接連結
        else:
            common = set(result_a.found_concepts) & set(result_b.found_concepts)
            if common:
                bridge = list(common)[0]
                connection = Connection(
                    concept_a=concept_a,
                    concept_b=concept_b,
                    connection_type="indirect",
                    path=[concept_a, bridge, concept_b],
                    explanation=f"「{concept_a}」和「{concept_b}」透過「{bridge}」連結",
                    novelty_score=0.5,
                )
            else:
                # 沒找到連結，這可能是最有創意的機會！
                connection = Connection(
                    concept_a=concept_a,
                    concept_b=concept_b,
                    connection_type="unexplored",
                    path=[concept_a, "?", concept_b],
                    explanation=f"「{concept_a}」和「{concept_b}」之間沒有已知連結，這是創新機會！",
                    novelty_score=0.95,  # 未探索 = 最高新穎度
                )
        
        self._connection_cache[cache_key] = connection
        return connection
    
    def suggest_bridge(self, concept_a: str, concept_b: str) -> list[str]:
        """
        建議可能的橋接概念
        
        Agent 可以用這個來找「中間概念」
        """
        result_a = self.explorer.search(concept_a, include_cross_domain=True)
        result_b = self.explorer.search(concept_b, include_cross_domain=True)
        
        # 找共同相關或跨域概念
        all_a = set(result_a.found_concepts + result_a.unexpected_finds)
        all_b = set(result_b.found_concepts + result_b.unexpected_finds)
        
        bridges = list(all_a & all_b)
        if not bridges:
            # 沒有直接橋接，建議跨域概念
            bridges = result_a.unexpected_finds[:2] + result_b.unexpected_finds[:2]
        
        return bridges[:5]


# ============================================================
# Tool 3: 新穎度驗證器 (Novelty Checker)
# ============================================================

@dataclass
class NoveltyReport:
    """新穎度報告"""
    idea: str
    is_novel: bool
    novelty_score: float  # 0-1
    similar_existing: list[str]  # 類似的已存在想法
    differentiation_suggestions: list[str]  # 差異化建議


class NoveltyChecker:
    """
    新穎度驗證工具
    
    Agent 可以用這個工具檢查想法是否足夠新穎，
    以及如何提高新穎度。
    
    這是關鍵！讓 Agent 可以「驗證」而不是盲目生成。
    """
    
    def __init__(self):
        # 模擬的「已存在想法」庫
        self.existing_ideas: list[dict] = [
            {"idea": "用 AI 寫程式碼", "keywords": ["AI", "程式", "自動化"]},
            {"idea": "遠端工作用視訊開會", "keywords": ["遠端", "視訊", "會議"]},
            {"idea": "線上教育平台", "keywords": ["線上", "教育", "學習"]},
            {"idea": "社群媒體行銷", "keywords": ["社群", "行銷", "廣告"]},
            {"idea": "永續環保產品", "keywords": ["永續", "環保", "綠色"]},
        ]
    
    def check(self, idea: str) -> NoveltyReport:
        """
        檢查想法的新穎度
        
        Agent 可以：
        - 驗證想法是否已存在
        - 獲得新穎度評分
        - 獲得差異化建議
        """
        # 關鍵字提取（簡化版）
        idea_keywords = set(idea.replace("、", " ").replace("，", " ").split())
        
        # 檢查相似度
        similar = []
        max_similarity = 0.0
        
        for existing in self.existing_ideas:
            existing_keywords = set(existing["keywords"])
            overlap = idea_keywords & existing_keywords
            similarity = len(overlap) / max(len(idea_keywords), 1)
            
            if similarity > 0.3:
                similar.append(existing["idea"])
                max_similarity = max(max_similarity, similarity)
        
        # 計算新穎度
        novelty_score = 1.0 - max_similarity
        is_novel = novelty_score > 0.6
        
        # 生成差異化建議
        suggestions = []
        if not is_novel:
            suggestions = [
                "嘗試加入不同領域的元素",
                "考慮反向思考：如果相反會怎樣？",
                "縮小目標群體，找出獨特需求",
                "結合兩個不相關的概念",
            ]
        
        return NoveltyReport(
            idea=idea,
            is_novel=is_novel,
            novelty_score=novelty_score,
            similar_existing=similar,
            differentiation_suggestions=suggestions,
        )
    
    def add_existing_idea(self, idea: str, keywords: list[str]) -> None:
        """
        添加已知想法到資料庫
        
        Agent 可以用這個記錄「這個想法已經被想過了」
        """
        self.existing_ideas.append({"idea": idea, "keywords": keywords})


# ============================================================
# Tool 4: 想法演化器 (Idea Evolver)
# ============================================================

@dataclass 
class Evolution:
    """一次演化"""
    original: str
    evolved: str
    mutation_type: str
    reasoning: str


class IdeaEvolver:
    """
    想法演化工具
    
    Agent 可以用這個工具對想法進行「突變」，
    包括：組合、分裂、反轉、類比、極端化。
    
    Agent 自己決定要用哪種突變。
    """
    
    def __init__(self, concept_explorer: ConceptExplorer | None = None):
        self.explorer = concept_explorer or ConceptExplorer()
    
    def mutate(self, idea: str, mutation_type: str | None = None) -> Evolution:
        """
        對想法進行突變
        
        mutation_type:
        - "combine": 與隨機概念結合
        - "split": 拆分成更具體的子想法
        - "reverse": 反向思考
        - "analogize": 類比到其他領域
        - "extreme": 極端化
        - None: 隨機選擇
        """
        if mutation_type is None:
            mutation_type = random.choice(["combine", "split", "reverse", "analogize", "extreme"])
        
        if mutation_type == "combine":
            return self._combine(idea)
        elif mutation_type == "split":
            return self._split(idea)
        elif mutation_type == "reverse":
            return self._reverse(idea)
        elif mutation_type == "analogize":
            return self._analogize(idea)
        elif mutation_type == "extreme":
            return self._extreme(idea)
        else:
            return self._combine(idea)
    
    def _combine(self, idea: str) -> Evolution:
        """結合突變"""
        random_concept = self.explorer.random_concept()
        evolved = f"{idea} + {random_concept} 的元素"
        return Evolution(
            original=idea,
            evolved=evolved,
            mutation_type="combine",
            reasoning=f"將「{random_concept}」的特性融入原始想法",
        )
    
    def _split(self, idea: str) -> Evolution:
        """分裂突變"""
        aspects = ["對象", "方法", "時機", "場景"]
        aspect = random.choice(aspects)
        evolved = f"{idea}，特別針對特定{aspect}"
        return Evolution(
            original=idea,
            evolved=evolved,
            mutation_type="split",
            reasoning=f"聚焦在「{aspect}」維度，找出更具體的應用",
        )
    
    def _reverse(self, idea: str) -> Evolution:
        """反轉突變"""
        evolved = f"如果「{idea}」的反面會怎樣？"
        return Evolution(
            original=idea,
            evolved=evolved,
            mutation_type="reverse",
            reasoning="反向思考，找出隱藏的假設和可能性",
        )
    
    def _analogize(self, idea: str) -> Evolution:
        """類比突變"""
        domains = ["自然界", "歷史", "藝術", "運動", "烹飪"]
        domain = random.choice(domains)
        evolved = f"如果用「{domain}」的角度看「{idea}」"
        return Evolution(
            original=idea,
            evolved=evolved,
            mutation_type="analogize",
            reasoning=f"借用「{domain}」的概念框架重新審視",
        )
    
    def _extreme(self, idea: str) -> Evolution:
        """極端化突變"""
        direction = random.choice(["放大 10 倍", "縮小到極致", "完全免費", "極度昂貴"])
        evolved = f"如果「{idea}」{direction}"
        return Evolution(
            original=idea,
            evolved=evolved,
            mutation_type="extreme",
            reasoning=f"極端化測試：{direction}",
        )


# ============================================================
# Tool 5: 創意記錄器 (Creativity Logger)
# ============================================================

@dataclass
class CreativitySession:
    """創意探索會話"""
    session_id: str
    topic: str
    explorations: list[dict] = field(default_factory=list)
    ideas_generated: list[str] = field(default_factory=list)
    ideas_validated: list[dict] = field(default_factory=list)
    best_idea: str | None = None
    best_novelty_score: float = 0.0


class CreativityLogger:
    """
    創意記錄工具
    
    讓 Agent 記錄自己的探索過程，
    追蹤哪些嘗試有效、哪些無效。
    
    這是 Agent 學習的基礎。
    """
    
    def __init__(self):
        self.sessions: dict[str, CreativitySession] = {}
        self.current_session: CreativitySession | None = None
    
    def start_session(self, topic: str) -> str:
        """開始新的創意探索會話"""
        session_id = hashlib.md5(f"{topic}{random.random()}".encode()).hexdigest()[:8]
        self.current_session = CreativitySession(
            session_id=session_id,
            topic=topic,
        )
        self.sessions[session_id] = self.current_session
        return session_id
    
    def log_exploration(self, action: str, result: Any) -> None:
        """記錄一次探索"""
        if self.current_session:
            self.current_session.explorations.append({
                "action": action,
                "result": str(result)[:200],  # 截斷
            })
    
    def log_idea(self, idea: str, novelty_score: float = 0.0) -> None:
        """記錄一個想法"""
        if not self.current_session:
            raise RuntimeError("No active creativity session. Call start_session() first.")
        
        self.current_session.ideas_generated.append(idea)
        self.current_session.ideas_validated.append({
            "idea": idea,
            "novelty_score": novelty_score,
        })
        
        # 更新最佳想法
        if novelty_score > self.current_session.best_novelty_score:
            self.current_session.best_idea = idea
            self.current_session.best_novelty_score = novelty_score
    
    def get_session_summary(self) -> dict:
        """取得當前會話摘要"""
        if not self.current_session:
            return {}
        
        return {
            "session_id": self.current_session.session_id,
            "topic": self.current_session.topic,
            "total_explorations": len(self.current_session.explorations),
            "total_ideas": len(self.current_session.ideas_generated),
            "best_idea": self.current_session.best_idea,
            "best_novelty_score": self.current_session.best_novelty_score,
        }
    
    def get_exploration_history(self) -> list[dict]:
        """取得探索歷史"""
        if not self.current_session:
            return []
        return self.current_session.explorations


# ============================================================
# 統一工具箱 (Creativity Toolbox)
# ============================================================

class CreativityToolbox:
    """
    創意工具箱
    
    這是 Agent 的創意工具集。
    Agent 可以自由組合這些工具來探索創意。
    
    關鍵：我們不規定流程，Agent 自己決定怎麼用。
    """
    
    def __init__(self):
        self.concept_explorer = ConceptExplorer()
        self.connection_finder = ConnectionFinder(self.concept_explorer)
        self.novelty_checker = NoveltyChecker()
        self.idea_evolver = IdeaEvolver(self.concept_explorer)
        self.logger = CreativityLogger()
    
    # === 工具方法（供 Agent 調用）===
    
    def explore_concept(self, concept: str, include_cross_domain: bool = True) -> dict:
        """
        Tool: 探索概念
        
        輸入：概念名稱
        輸出：相關概念、跨域概念、意外發現
        """
        result = self.concept_explorer.search(concept, include_cross_domain)
        self.logger.log_exploration("explore_concept", result)
        return {
            "query": result.query,
            "related": result.found_concepts,
            "domains": result.related_domains,
            "unexpected": result.unexpected_finds,
        }
    
    def find_connection(self, concept_a: str, concept_b: str) -> dict:
        """
        Tool: 尋找連結
        
        輸入：兩個概念
        輸出：連結類型、路徑、新穎度
        """
        result = self.connection_finder.find_connection(concept_a, concept_b)
        self.logger.log_exploration("find_connection", result)
        if result:
            return {
                "concept_a": result.concept_a,
                "concept_b": result.concept_b,
                "connection_type": result.connection_type,
                "path": result.path,
                "explanation": result.explanation,
                "novelty_score": result.novelty_score,
            }
        return {"error": "No connection found"}
    
    def check_novelty(self, idea: str) -> dict:
        """
        Tool: 檢查新穎度
        
        輸入：想法
        輸出：是否新穎、分數、類似想法、建議
        """
        result = self.novelty_checker.check(idea)
        self.logger.log_exploration("check_novelty", result)
        return {
            "idea": result.idea,
            "is_novel": result.is_novel,
            "novelty_score": result.novelty_score,
            "similar_existing": result.similar_existing,
            "suggestions": result.differentiation_suggestions,
        }
    
    def evolve_idea(self, idea: str, mutation_type: str | None = None) -> dict:
        """
        Tool: 演化想法
        
        輸入：想法、突變類型（可選）
        輸出：演化後的想法、推理過程
        """
        result = self.idea_evolver.mutate(idea, mutation_type)
        self.logger.log_exploration("evolve_idea", result)
        return {
            "original": result.original,
            "evolved": result.evolved,
            "mutation_type": result.mutation_type,
            "reasoning": result.reasoning,
        }
    
    def get_random_concept(self) -> str:
        """
        Tool: 隨機概念
        
        用於「隨機探索」
        """
        concept = self.concept_explorer.random_concept()
        self.logger.log_exploration("random_concept", concept)
        return concept
    
    def suggest_bridges(self, concept_a: str, concept_b: str) -> list[str]:
        """
        Tool: 建議橋接
        
        找可能連接兩個概念的中間概念
        """
        bridges = self.connection_finder.suggest_bridge(concept_a, concept_b)
        self.logger.log_exploration("suggest_bridges", bridges)
        return bridges
    
    def start_session(self, topic: str) -> str:
        """
        Tool: 開始會話
        
        開始新的創意探索
        """
        return self.logger.start_session(topic)
    
    def record_idea(self, idea: str) -> dict:
        """
        Tool: 記錄想法
        
        驗證並記錄一個想法
        """
        if not self.logger.current_session:
            raise RuntimeError("No active creativity session. Call start_session() first.")
        
        novelty = self.novelty_checker.check(idea)
        self.logger.log_idea(idea, novelty.novelty_score)
        return {
            "idea": idea,
            "novelty_score": novelty.novelty_score,
            "is_best_so_far": idea == self.logger.current_session.best_idea if self.logger.current_session else False,
        }
    
    def get_progress(self) -> dict:
        """
        Tool: 查看進度
        
        查看當前探索進度
        """
        return self.logger.get_session_summary()
    
    def get_history(self) -> list[dict]:
        """
        Tool: 查看歷史
        
        查看探索歷史
        """
        return self.logger.get_exploration_history()


# ============================================================
# 測試：模擬 Agent 使用工具
# ============================================================

def simulate_agent_creativity(topic: str) -> dict:
    """
    模擬 Agent 使用工具探索創意
    
    這展示了 Agent 可以如何自主使用工具，
    而不是被動地接受 Prompt。
    """
    toolbox = CreativityToolbox()
    
    # Agent 開始會話
    session_id = toolbox.start_session(topic)
    print(f"🎯 開始創意探索：{topic} (Session: {session_id})")
    
    # Agent 決定先探索主題概念
    print("\n📚 Step 1: Agent 探索主題概念")
    exploration = toolbox.explore_concept(topic.split()[0] if topic else "創意")
    print(f"   相關概念：{exploration['related']}")
    print(f"   意外發現：{exploration['unexpected']}")
    
    # Agent 決定嘗試跨域連結
    if exploration['unexpected']:
        print("\n🔗 Step 2: Agent 嘗試跨域連結")
        unexpected = exploration['unexpected'][0]
        connection = toolbox.find_connection(topic.split()[0], unexpected)
        print(f"   連結類型：{connection['connection_type']}")
        print(f"   新穎度：{connection['novelty_score']:.2f}")
    
    # Agent 生成初始想法
    print("\n💡 Step 3: Agent 生成初始想法")
    initial_idea = f"將 {topic} 與 {exploration['unexpected'][0] if exploration['unexpected'] else '創新'} 結合"
    novelty = toolbox.check_novelty(initial_idea)
    print(f"   想法：{initial_idea}")
    print(f"   新穎度：{novelty['novelty_score']:.2f}")
    
    # 如果不夠新穎，Agent 決定演化
    if not novelty['is_novel']:
        print("\n🔄 Step 4: Agent 發現不夠新穎，進行演化")
        evolved = toolbox.evolve_idea(initial_idea, "combine")
        print(f"   演化類型：{evolved['mutation_type']}")
        print(f"   新想法：{evolved['evolved']}")
        
        # 再次檢查
        new_novelty = toolbox.check_novelty(evolved['evolved'])
        print(f"   新新穎度：{new_novelty['novelty_score']:.2f}")
        
        # 記錄
        toolbox.record_idea(evolved['evolved'])
    else:
        toolbox.record_idea(initial_idea)
    
    # 查看進度
    print("\n📊 最終進度：")
    progress = toolbox.get_progress()
    print(f"   總探索次數：{progress['total_explorations']}")
    print(f"   最佳想法：{progress['best_idea']}")
    print(f"   最佳新穎度：{progress['best_novelty_score']:.2f}")
    
    return progress


if __name__ == "__main__":
    print("=" * 60)
    print("CGU v3: Agent-Driven Creativity Tools 測試")
    print("=" * 60)
    
    result = simulate_agent_creativity("遠端工作")
    
    print("\n" + "=" * 60)
    print("✅ 測試完成")
    print("=" * 60)
