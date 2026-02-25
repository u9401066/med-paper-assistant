"""
ConceptGraph - 概念圖譜遍歷引擎

核心理念：在知識空間中，創意 = 找到「非顯而易見但有意義」的路徑

直接路徑（無聊）：
    咖啡 → 飲料 → 提神

間接路徑（有創意）：
    咖啡 → 衣索比亞 → 殖民歷史 → 全球化 → 程式外包 → 程式設計
"""

from __future__ import annotations

import heapq
import logging
import random
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterator

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EdgeType(str, Enum):
    """邊的類型 - 關係種類"""
    IS_A = "is_a"                # 是一種
    PART_OF = "part_of"          # 是...的一部分
    CAUSES = "causes"            # 導致
    USED_FOR = "used_for"        # 用於
    LOCATED_IN = "located_in"    # 位於
    RELATED_TO = "related_to"    # 相關於
    OPPOSITE_OF = "opposite_of"  # 相反於
    SIMILAR_TO = "similar_to"    # 類似於
    MADE_OF = "made_of"          # 由...組成
    SYMBOL_OF = "symbol_of"      # 象徵
    ORIGIN = "origin"            # 起源
    LEADS_TO = "leads_to"        # 通往


@dataclass
class ConceptNode:
    """概念節點"""
    id: str
    name: str
    domain: str = "general"
    attributes: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ConceptNode):
            return self.id == other.id
        return False


@dataclass
class ConceptEdge:
    """概念間的邊（關係）"""
    source: str       # 來源節點 ID
    target: str       # 目標節點 ID
    edge_type: EdgeType
    weight: float = 1.0      # 關係強度（越小越常見）
    novelty: float = 0.5     # 新穎度（越大越不常見）

    @property
    def creative_weight(self) -> float:
        """
        創意權重 = 常見度低 + 新穎度高

        用於找「非顯而易見」的路徑
        """
        return self.weight * (1 - self.novelty * 0.5)


class ConceptPath(BaseModel):
    """一條概念路徑"""
    nodes: list[str] = Field(default_factory=list)
    edges: list[str] = Field(default_factory=list)  # edge types

    # 評估指標
    total_weight: float = 0.0
    hop_count: int = 0
    novelty_score: float = 0.0
    semantic_coherence: float = 0.0

    @property
    def is_creative(self) -> bool:
        """是否是創意路徑（3-7跳，高新穎度）"""
        return 3 <= self.hop_count <= 7 and self.novelty_score > 0.5

    @property
    def quality_score(self) -> float:
        """
        路徑品質 = 適當長度 × 新穎度 × 連貫性
        """
        length_score = 1.0 - abs(self.hop_count - 5) * 0.1  # 5跳最佳
        length_score = max(0.3, min(1.0, length_score))
        return length_score * self.novelty_score * self.semantic_coherence

    def to_string(self) -> str:
        """路徑的字串表示"""
        if not self.nodes:
            return ""

        parts = [self.nodes[0]]
        for i, edge_type in enumerate(self.edges):
            if i + 1 < len(self.nodes):
                parts.append(f" --[{edge_type}]--> ")
                parts.append(self.nodes[i + 1])
        return "".join(parts)


class ConceptGraph:
    """
    概念圖譜

    一個簡單的圖結構，用於概念間的路徑探索
    """

    def __init__(self):
        self.nodes: dict[str, ConceptNode] = {}
        self.edges: dict[str, list[ConceptEdge]] = defaultdict(list)  # source_id -> edges
        self.reverse_edges: dict[str, list[ConceptEdge]] = defaultdict(list)  # target_id -> edges

    def add_node(self, node: ConceptNode) -> None:
        """添加節點"""
        self.nodes[node.id] = node

    def add_edge(self, edge: ConceptEdge) -> None:
        """添加邊"""
        self.edges[edge.source].append(edge)
        self.reverse_edges[edge.target].append(edge)

    def get_neighbors(self, node_id: str, reverse: bool = False) -> list[tuple[str, ConceptEdge]]:
        """取得鄰居節點"""
        if reverse:
            return [(e.source, e) for e in self.reverse_edges.get(node_id, [])]
        return [(e.target, e) for e in self.edges.get(node_id, [])]

    def has_node(self, node_id: str) -> bool:
        return node_id in self.nodes

    def node_count(self) -> int:
        return len(self.nodes)

    def edge_count(self) -> int:
        return sum(len(edges) for edges in self.edges.values())


# === 預設的概念圖譜 ===

def build_default_graph() -> ConceptGraph:
    """
    建構預設的概念圖譜

    這是一個示範用的小型圖譜，實際應用需要更大的知識庫
    """
    graph = ConceptGraph()

    # === 添加節點 ===
    domains_nodes = {
        "food": ["咖啡", "茶", "飲料", "食物", "能量", "味道", "苦", "甜"],
        "tech": ["程式設計", "軟體", "電腦", "演算法", "Debug", "重構", "自動化"],
        "nature": ["樹木", "森林", "生態", "種子", "生長", "根", "養分"],
        "history": ["殖民", "貿易", "全球化", "文化交流", "傳播"],
        "work": ["效率", "疲勞", "專注", "創意", "協作", "遠端工作"],
        "abstract": ["累積", "循環", "突破", "連結", "抽象", "具體"],
        "geography": ["衣索比亞", "亞洲", "歐洲", "美洲", "非洲"],
        "society": ["儀式", "習慣", "文化", "社群", "孤獨", "歸屬"],
    }

    for domain, concepts in domains_nodes.items():
        for concept in concepts:
            graph.add_node(ConceptNode(
                id=concept,
                name=concept,
                domain=domain,
            ))

    # === 添加邊 ===
    edges_data = [
        # 咖啡相關
        ("咖啡", "飲料", EdgeType.IS_A, 0.3, 0.1),
        ("咖啡", "能量", EdgeType.CAUSES, 0.4, 0.2),
        ("咖啡", "苦", EdgeType.RELATED_TO, 0.3, 0.1),
        ("咖啡", "衣索比亞", EdgeType.ORIGIN, 0.8, 0.7),
        ("咖啡", "專注", EdgeType.CAUSES, 0.5, 0.3),
        ("咖啡", "儀式", EdgeType.SYMBOL_OF, 0.7, 0.6),

        # 程式設計相關
        ("程式設計", "軟體", EdgeType.USED_FOR, 0.3, 0.1),
        ("程式設計", "演算法", EdgeType.PART_OF, 0.4, 0.2),
        ("程式設計", "Debug", EdgeType.PART_OF, 0.4, 0.2),
        ("程式設計", "重構", EdgeType.RELATED_TO, 0.5, 0.3),
        ("程式設計", "抽象", EdgeType.RELATED_TO, 0.6, 0.5),
        ("程式設計", "自動化", EdgeType.LEADS_TO, 0.5, 0.3),

        # 跨域連結（創意的來源）
        ("衣索比亞", "非洲", EdgeType.LOCATED_IN, 0.3, 0.1),
        ("衣索比亞", "貿易", EdgeType.RELATED_TO, 0.7, 0.6),
        ("貿易", "全球化", EdgeType.LEADS_TO, 0.5, 0.4),
        ("全球化", "遠端工作", EdgeType.CAUSES, 0.7, 0.7),
        ("遠端工作", "程式設計", EdgeType.RELATED_TO, 0.6, 0.5),

        # 自然類比
        ("樹木", "根", EdgeType.PART_OF, 0.3, 0.1),
        ("根", "養分", EdgeType.USED_FOR, 0.4, 0.2),
        ("樹木", "生長", EdgeType.RELATED_TO, 0.4, 0.2),
        ("種子", "樹木", EdgeType.LEADS_TO, 0.4, 0.2),

        # 抽象概念
        ("累積", "循環", EdgeType.RELATED_TO, 0.6, 0.4),
        ("累積", "突破", EdgeType.OPPOSITE_OF, 0.7, 0.6),
        ("抽象", "具體", EdgeType.OPPOSITE_OF, 0.3, 0.1),

        # 工作相關
        ("效率", "疲勞", EdgeType.OPPOSITE_OF, 0.5, 0.3),
        ("專注", "效率", EdgeType.CAUSES, 0.4, 0.2),
        ("創意", "專注", EdgeType.RELATED_TO, 0.6, 0.5),
        ("遠端工作", "孤獨", EdgeType.CAUSES, 0.6, 0.5),
        ("孤獨", "歸屬", EdgeType.OPPOSITE_OF, 0.4, 0.3),

        # 社會文化
        ("儀式", "習慣", EdgeType.SIMILAR_TO, 0.4, 0.2),
        ("儀式", "歸屬", EdgeType.CAUSES, 0.6, 0.5),
        ("社群", "歸屬", EdgeType.CAUSES, 0.4, 0.2),
        ("文化", "儀式", EdgeType.PART_OF, 0.5, 0.3),
    ]

    for source, target, edge_type, weight, novelty in edges_data:
        if graph.has_node(source) and graph.has_node(target):
            graph.add_edge(ConceptEdge(
                source=source,
                target=target,
                edge_type=edge_type,
                weight=weight,
                novelty=novelty,
            ))
            # 添加反向邊（較弱）
            graph.add_edge(ConceptEdge(
                source=target,
                target=source,
                edge_type=edge_type,
                weight=weight * 1.5,
                novelty=novelty,
            ))

    return graph


class GraphTraversalEngine:
    """
    圖譜遍歷引擎

    核心功能：
    1. 找最短路徑（顯而易見）
    2. 找非常規路徑（創意）
    3. 評估路徑的創意價值
    """

    def __init__(self, graph: ConceptGraph | None = None, llm_client: Any = None):
        self.graph = graph or build_default_graph()
        self.llm = llm_client

    def find_shortest_path(
        self,
        source: str,
        target: str,
        max_hops: int = 10,
    ) -> ConceptPath | None:
        """
        找最短路徑（Dijkstra）

        這是「顯而易見」的路徑，用於對比
        """
        if not self.graph.has_node(source) or not self.graph.has_node(target):
            return None

        # Dijkstra
        distances: dict[str, float] = {source: 0}
        previous: dict[str, tuple[str, ConceptEdge] | None] = {source: None}
        pq = [(0, source)]
        visited = set()

        while pq:
            dist, current = heapq.heappop(pq)

            if current in visited:
                continue
            visited.add(current)

            if current == target:
                break

            if len(visited) > max_hops * 10:  # 防止無限搜索
                break

            for neighbor, edge in self.graph.get_neighbors(current):
                if neighbor in visited:
                    continue

                new_dist = dist + edge.weight
                if neighbor not in distances or new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    previous[neighbor] = (current, edge)
                    heapq.heappush(pq, (new_dist, neighbor))

        # 重建路徑
        if target not in previous:
            return None

        path_nodes = []
        path_edges = []
        current = target

        while current is not None:
            path_nodes.append(current)
            prev = previous.get(current)
            if prev:
                prev_node, edge = prev
                path_edges.append(edge.edge_type.value)
                current = prev_node
            else:
                current = None

        path_nodes.reverse()
        path_edges.reverse()

        return ConceptPath(
            nodes=path_nodes,
            edges=path_edges,
            total_weight=distances.get(target, 0),
            hop_count=len(path_nodes) - 1,
            novelty_score=0.2,  # 最短路徑新穎度低
            semantic_coherence=0.9,  # 但連貫性高
        )

    def find_creative_paths(
        self,
        source: str,
        target: str,
        avoid_direct: bool = True,
        max_paths: int = 5,
        min_hops: int = 3,
        max_hops: int = 7,
    ) -> list[ConceptPath]:
        """
        找創意路徑 - 非顯而易見的連結

        策略：
        1. 先找最短路徑
        2. 排除最短路徑上的中間節點
        3. 找替代路徑
        """
        if not self.graph.has_node(source) or not self.graph.has_node(target):
            return []

        # 1. 找最短路徑
        direct_path = self.find_shortest_path(source, target)
        avoid_nodes = set()
        if direct_path and avoid_direct:
            # 排除中間節點（但保留起終點）
            avoid_nodes = set(direct_path.nodes[1:-1])

        # 2. 用 DFS 找替代路徑
        all_paths: list[ConceptPath] = []

        def dfs(
            current: str,
            visited: set[str],
            path_nodes: list[str],
            path_edges: list[ConceptEdge],
            depth: int,
        ) -> None:
            if depth > max_hops:
                return

            if current == target and depth >= min_hops:
                # 計算路徑品質
                novelty = sum(e.novelty for e in path_edges) / max(len(path_edges), 1)
                coherence = 1.0 - (0.1 * sum(1 for e in path_edges if e.novelty > 0.7))
                coherence = max(0.3, coherence)

                all_paths.append(ConceptPath(
                    nodes=path_nodes.copy(),
                    edges=[e.edge_type.value for e in path_edges],
                    total_weight=sum(e.weight for e in path_edges),
                    hop_count=len(path_edges),
                    novelty_score=novelty,
                    semantic_coherence=coherence,
                ))
                return

            for neighbor, edge in self.graph.get_neighbors(current):
                if neighbor in visited:
                    continue
                if neighbor in avoid_nodes and neighbor != target:
                    continue

                visited.add(neighbor)
                path_nodes.append(neighbor)
                path_edges.append(edge)

                dfs(neighbor, visited, path_nodes, path_edges, depth + 1)

                path_nodes.pop()
                path_edges.pop()
                visited.remove(neighbor)

        # 開始搜索
        dfs(source, {source}, [source], [], 0)

        # 3. 排序並返回最佳
        all_paths.sort(key=lambda p: p.quality_score, reverse=True)
        return all_paths[:max_paths]

    def find_unexpected_connection(
        self,
        concept_a: str,
        concept_b: str,
    ) -> dict:
        """
        找兩個概念之間的「意外連結」

        返回：
        - 直接路徑（如果有）
        - 創意路徑
        - 連結的洞察
        """
        result = {
            "concept_a": concept_a,
            "concept_b": concept_b,
            "direct_path": None,
            "creative_paths": [],
            "insight": "",
            "surprise_score": 0.0,
        }

        # 直接路徑
        direct = self.find_shortest_path(concept_a, concept_b)
        if direct:
            result["direct_path"] = {
                "path": direct.to_string(),
                "hops": direct.hop_count,
            }

        # 創意路徑
        creative = self.find_creative_paths(concept_a, concept_b)
        if creative:
            result["creative_paths"] = [
                {
                    "path": p.to_string(),
                    "hops": p.hop_count,
                    "novelty": p.novelty_score,
                    "quality": p.quality_score,
                }
                for p in creative[:3]
            ]

            # 取最佳創意路徑產生洞察
            best = creative[0]
            result["insight"] = self._generate_path_insight(best)
            result["surprise_score"] = best.novelty_score * (1 - 1/max(best.hop_count, 1))

        return result

    def _generate_path_insight(self, path: ConceptPath) -> str:
        """從路徑生成洞察"""
        if len(path.nodes) < 3:
            return f"{path.nodes[0]} 和 {path.nodes[-1]} 直接相關"

        # 找出關鍵的中間概念
        middle_concepts = path.nodes[1:-1]

        if self.llm:
            # TODO: 使用 LLM 生成更深入的洞察
            pass

        # 啟發式生成
        key_concept = middle_concepts[len(middle_concepts) // 2]
        return (
            f"從「{path.nodes[0]}」到「{path.nodes[-1]}」，"
            f"透過「{key_concept}」這個意想不到的中介，"
            f"揭示了兩者在更深層的連結。"
        )

    def explore_from(
        self,
        start: str,
        max_depth: int = 3,
    ) -> dict[str, list[str]]:
        """
        從一個概念出發探索

        返回各深度可達的概念
        """
        if not self.graph.has_node(start):
            return {}

        result: dict[str, list[str]] = {}
        visited = {start}
        current_layer = [start]

        for depth in range(1, max_depth + 1):
            next_layer = []
            for node in current_layer:
                for neighbor, _ in self.graph.get_neighbors(node):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_layer.append(neighbor)

            if next_layer:
                result[f"depth_{depth}"] = next_layer
                current_layer = next_layer
            else:
                break

        return result

    def add_concept(self, concept: str, domain: str = "general") -> None:
        """動態添加概念"""
        if not self.graph.has_node(concept):
            self.graph.add_node(ConceptNode(
                id=concept,
                name=concept,
                domain=domain,
            ))

    def add_relation(
        self,
        source: str,
        target: str,
        relation: EdgeType,
        weight: float = 0.5,
        novelty: float = 0.5,
    ) -> None:
        """動態添加關係"""
        self.add_concept(source)
        self.add_concept(target)

        self.graph.add_edge(ConceptEdge(
            source=source,
            target=target,
            edge_type=relation,
            weight=weight,
            novelty=novelty,
        ))


# === 便捷函數 ===

_default_engine: GraphTraversalEngine | None = None


def get_graph_engine() -> GraphTraversalEngine:
    """取得全域圖譜引擎"""
    global _default_engine
    if _default_engine is None:
        _default_engine = GraphTraversalEngine()
    return _default_engine


def find_connection(concept_a: str, concept_b: str) -> dict:
    """快速查找兩概念的連結"""
    engine = get_graph_engine()
    return engine.find_unexpected_connection(concept_a, concept_b)


def explore_concept(concept: str, depth: int = 3) -> dict[str, list[str]]:
    """從概念出發探索"""
    engine = get_graph_engine()
    return engine.explore_from(concept, depth)
