"""
Spark-Soup: Context Stuffing for Creativity

用碎片化資訊填充 context，模擬人類接收新聞/書籍/體驗後產生創意連結的過程。

核心概念：
1. 收集多來源碎片（搜尋、維基、名言等）
2. 組裝「創意湯」並重複錨定主題
3. 讓 LLM 從碎片中產生意外連結
"""

import logging
import random
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FragmentSource(Enum):
    """碎片來源"""

    DUCKDUCKGO = "duckduckgo"
    WIKIPEDIA = "wikipedia"
    QUOTES = "quotes"
    CONCEPTNET = "conceptnet"
    USER = "user"
    RANDOM = "random"


@dataclass
class Fragment:
    """創意碎片"""

    content: str
    source: FragmentSource
    relevance: float = 0.5  # 0-1，與主題的相關性

    def __str__(self) -> str:
        return f"📌 {self.content}"


@dataclass
class SparkSoupResult:
    """Spark Soup 結果"""

    soup: str
    topic: str
    fragments_used: list[Fragment]
    diversity_score: float
    trigger_words_used: list[str]

    def to_dict(self) -> dict:
        return {
            "soup": self.soup,
            "topic": self.topic,
            "fragments_count": len(self.fragments_used),
            "diversity_score": self.diversity_score,
            "trigger_words": self.trigger_words_used,
            "sources": list(set(f.source.value for f in self.fragments_used)),
        }


@dataclass
class Idea:
    """生成的想法"""

    title: str
    description: str
    connected_fragments: list[str]
    novelty_score: float

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "connected_fragments": self.connected_fragments,
            "novelty_score": self.novelty_score,
        }


# === 內建資料庫 ===

TRIGGER_WORDS = {
    "combination": [
        "如果把這兩個結合會怎樣？",
        "這些概念有什麼共通點？",
        "把這個放到另一個領域會變成什麼？",
        "如果 A 遇到 B 會發生什麼？",
    ],
    "inversion": [
        "如果完全相反會怎樣？",
        "把這個顛倒過來呢？",
        "如果缺點變成優點呢？",
        "如果禁止最常見的做法呢？",
    ],
    "scale": [
        "如果放大 10 倍呢？",
        "如果縮小到極致呢？",
        "如果給無限資源呢？",
        "如果只有 1% 的資源呢？",
    ],
    "time": [
        "100 年後會變成什麼樣子？",
        "如果在古代就有這個呢？",
        "如果必須在 1 小時內完成呢？",
        "如果可以時間旅行呢？",
    ],
    "perspective": [
        "如果是小孩來看這個問題呢？",
        "如果是外星人第一次看到呢？",
        "如果競爭對手這樣做呢？",
        "如果是動物/植物的視角呢？",
    ],
    "emotion": [
        "如果讓人感到驚喜呢？",
        "如果讓人大笑呢？",
        "如果讓人感動落淚呢？",
        "如果讓人感到舒適呢？",
    ],
}

CREATIVITY_QUOTES = [
    "創意就是連結事物。— Steve Jobs",
    "限制激發創意。",
    "好的藝術家複製，偉大的藝術家偷竊。— Picasso",
    "每個孩子都是藝術家，問題是長大後如何保持這種能力。— Picasso",
    "想像力比知識更重要。— Einstein",
    "創意需要勇氣。— Henri Matisse",
    "我沒有特別的天賦，只是強烈好奇心。— Einstein",
    "最好的預測未來的方式就是創造它。— Peter Drucker",
    "突破常規是創新的開始。",
    "問對問題比找到答案更重要。",
    "失敗是成功之母，每一次失敗都是學習。",
    "簡單是終極的複雜。— Da Vinci",
    "創意是一種習慣，而不是偶然。",
    "打破規則之前，先了解規則。",
    "邊界存在是為了被跨越。",
    "不同的觀點帶來不同的解決方案。",
    "創意來自於不同想法的碰撞。",
    "保持好奇心，永遠像個孩子。",
    "創意是看見別人看不見的連結。",
    "最瘋狂的想法往往最有價值。",
]

RANDOM_CONCEPTS = [
    "蜂巢",
    "星空",
    "咖啡",
    "森林",
    "機器人",
    "音樂",
    "海洋",
    "夢想",
    "旅行",
    "魔法",
    "時間",
    "彩虹",
    "風箏",
    "螢火蟲",
    "積木",
    "拼圖",
    "迷宮",
    "望遠鏡",
    "顯微鏡",
    "蠟燭",
    "鏡子",
    "影子",
    "河流",
    "瀑布",
    "火山",
    "冰山",
    "沙漠",
    "綠洲",
    "燈塔",
    "羅盤",
    "地圖",
    "寶藏",
    "種子",
    "蝴蝶",
    "蜻蜓",
    "珊瑚",
    "晨露",
    "黃昏",
    "極光",
    "閃電",
]

CROSS_DOMAIN_CONCEPTS = {
    "科技": ["AI", "區塊鏈", "量子計算", "物聯網", "VR/AR", "5G", "機器學習", "雲端"],
    "自然": ["光合作用", "生態系", "演化", "候鳥遷徙", "珊瑚礁", "熱帶雨林", "極地"],
    "藝術": ["印象派", "極簡主義", "巴洛克", "立體派", "街頭藝術", "互動藝術"],
    "心理": ["心流", "認知偏誤", "正念", "潛意識", "同理心", "創傷後成長"],
    "商業": ["精實創業", "藍海策略", "訂閱經濟", "共享經濟", "平台經濟"],
    "哲學": ["存在主義", "功利主義", "斯多葛", "禪宗", "蘇格拉底式"],
    "歷史": ["文藝復興", "工業革命", "資訊時代", "大航海時代", "啟蒙運動"],
    "生物": ["仿生學", "群體智慧", "適者生存", "共生關係", "基因突變"],
}


class FragmentCollector:
    """碎片收集器基底類別"""

    async def collect(self, topic: str, count: int, randomness: float = 0.5) -> list[Fragment]:
        raise NotImplementedError


class QuotesCollector(FragmentCollector):
    """名言金句收集器"""

    async def collect(self, topic: str, count: int, randomness: float = 0.5) -> list[Fragment]:
        selected = random.sample(CREATIVITY_QUOTES, min(count, len(CREATIVITY_QUOTES)))
        return [Fragment(content=q, source=FragmentSource.QUOTES, relevance=0.3) for q in selected]


class RandomConceptCollector(FragmentCollector):
    """隨機概念收集器"""

    async def collect(self, topic: str, count: int, randomness: float = 0.5) -> list[Fragment]:
        # 混合隨機概念和跨領域概念
        fragments = []

        # 隨機概念
        n_random = int(count * 0.6)
        random_items = random.sample(RANDOM_CONCEPTS, min(n_random, len(RANDOM_CONCEPTS)))
        fragments.extend(
            [
                Fragment(content=f"隨機概念：{c}", source=FragmentSource.RANDOM, relevance=0.2)
                for c in random_items
            ]
        )

        # 跨領域概念
        n_cross = count - n_random
        all_cross = []
        for domain, concepts in CROSS_DOMAIN_CONCEPTS.items():
            for c in concepts:
                all_cross.append(f"{domain}領域：{c}")

        cross_items = random.sample(all_cross, min(n_cross, len(all_cross)))
        fragments.extend(
            [Fragment(content=c, source=FragmentSource.RANDOM, relevance=0.3) for c in cross_items]
        )

        return fragments


class DuckDuckGoCollector(FragmentCollector):
    """DuckDuckGo 搜尋收集器"""

    async def collect(self, topic: str, count: int, randomness: float = 0.5) -> list[Fragment]:
        try:
            from duckduckgo_search import DDGS

            fragments = []

            # 主題相關搜尋
            async with DDGS() as ddgs:
                results = list(ddgs.text(f"{topic} 創新", max_results=count // 2))
                for r in results:
                    fragments.append(
                        Fragment(
                            content=f"🔍 {r.get('title', '')}: {r.get('body', '')[:100]}...",
                            source=FragmentSource.DUCKDUCKGO,
                            relevance=0.7,
                        )
                    )

                # 隨機延伸搜尋
                if randomness > 0.3:
                    random_word = random.choice(RANDOM_CONCEPTS)
                    random_results = list(ddgs.text(f"{random_word} 趨勢", max_results=count // 2))
                    for r in random_results:
                        fragments.append(
                            Fragment(
                                content=f"🎲 {r.get('title', '')}: {r.get('body', '')[:100]}...",
                                source=FragmentSource.DUCKDUCKGO,
                                relevance=0.3,
                            )
                        )

            return fragments[:count]

        except Exception as e:
            logger.warning(f"DuckDuckGo 搜尋失敗: {e}")
            return []


class SoupAssembler:
    """創意湯組裝器"""

    def __init__(self):
        self.collectors: dict[str, FragmentCollector] = {
            "quotes": QuotesCollector(),
            "random": RandomConceptCollector(),
            "duckduckgo": DuckDuckGoCollector(),
        }

    async def collect_fragments(
        self,
        topic: str,
        sources: list[str],
        count_per_source: int = 5,
        randomness: float = 0.5,
    ) -> list[Fragment]:
        """從多個來源收集碎片"""
        all_fragments = []

        for source in sources:
            collector = self.collectors.get(source)
            if collector:
                try:
                    fragments = await collector.collect(
                        topic=topic,
                        count=count_per_source,
                        randomness=randomness,
                    )
                    all_fragments.extend(fragments)
                except Exception as e:
                    logger.warning(f"收集 {source} 失敗: {e}")

        return all_fragments

    def assemble_soup(
        self,
        topic: str,
        fragments: list[Fragment],
        topic_repetition: int = 5,
        trigger_categories: list[str] | None = None,
    ) -> SparkSoupResult:
        """組裝創意湯"""

        # 確保多樣性：交錯排列不同來源的碎片
        fragments = self._ensure_diversity(fragments)

        # 選擇觸發詞
        trigger_words = self._select_triggers(
            trigger_categories or ["combination", "inversion", "perspective"]
        )

        # 組裝
        soup_parts = []
        interval = max(1, len(fragments) // (topic_repetition + 1))
        trigger_index = 0

        # 開頭：主題宣告
        soup_parts.append(f"🎯 **主要主題**: {topic}")
        soup_parts.append("---")
        soup_parts.append("以下是多元碎片資訊，請從中尋找意外連結：\n")

        for i, fragment in enumerate(fragments):
            # 每隔 N 個碎片插入主題錨定
            if i > 0 and i % interval == 0:
                soup_parts.append(f"\n🎯 **提醒主題**: {topic}\n")

                # 每次錨定時也加入一個觸發詞
                if trigger_index < len(trigger_words):
                    soup_parts.append(f"💡 **發想提示**: {trigger_words[trigger_index]}")
                    trigger_index += 1

            soup_parts.append(str(fragment))

        # 結尾：再次強調主題
        soup_parts.append("\n---")
        soup_parts.append(f"🎯 **核心主題**: {topic}")
        soup_parts.append("\n請基於以上碎片，為這個主題產生創意想法。尋找意外的連結！")

        soup = "\n".join(soup_parts)

        # 計算多樣性分數
        diversity_score = self._calculate_diversity(fragments)

        return SparkSoupResult(
            soup=soup,
            topic=topic,
            fragments_used=fragments,
            diversity_score=diversity_score,
            trigger_words_used=trigger_words[:trigger_index],
        )

    def _ensure_diversity(self, fragments: list[Fragment]) -> list[Fragment]:
        """確保碎片多樣性（交錯排列）"""
        from collections import defaultdict

        by_source = defaultdict(list)
        for f in fragments:
            by_source[f.source].append(f)

        result = []
        while any(by_source.values()):
            for source in list(by_source.keys()):
                if by_source[source]:
                    result.append(by_source[source].pop(0))

        return result

    def _select_triggers(self, categories: list[str], count: int = 5) -> list[str]:
        """選擇觸發詞"""
        selected = []
        for cat in categories:
            if cat in TRIGGER_WORDS:
                selected.extend(random.sample(TRIGGER_WORDS[cat], min(2, len(TRIGGER_WORDS[cat]))))
        return selected[:count]

    def _calculate_diversity(self, fragments: list[Fragment]) -> float:
        """計算多樣性分數"""
        if not fragments:
            return 0.0

        # 來源多樣性
        sources = set(f.source for f in fragments)
        source_diversity = len(sources) / len(FragmentSource)

        # 相關性分布（越分散越好）
        relevances = [f.relevance for f in fragments]
        if len(relevances) > 1:
            import statistics

            try:
                relevance_spread = statistics.stdev(relevances)
            except statistics.StatisticsError:
                relevance_spread = 0
        else:
            relevance_spread = 0

        return min(1.0, (source_diversity * 0.6 + relevance_spread * 0.4 + 0.3))


# === 主要入口 ===

_assembler: SoupAssembler | None = None


def get_assembler() -> SoupAssembler:
    """取得 SoupAssembler 單例"""
    global _assembler
    if _assembler is None:
        _assembler = SoupAssembler()
    return _assembler


async def spark_soup(
    topic: str,
    fragment_count: int = 20,
    topic_repetition: int = 5,
    auto_search: bool = True,
    custom_fragments: list[str] | None = None,
    trigger_categories: list[str] | None = None,
    randomness: float = 0.5,
) -> SparkSoupResult:
    """
    組裝「創意湯」- 用碎片化資訊填充 context

    Args:
        topic: 主題（會在 soup 中重複多次避免遺忘）
        fragment_count: 碎片數量（預設 20）
        topic_repetition: 主題重複次數（預設 5）
        auto_search: 是否自動搜尋外部資訊
        custom_fragments: 使用者自訂碎片
        trigger_categories: 觸發詞類別 ["combination", "inversion", "scale", "time", "perspective", "emotion"]
        randomness: 隨機性 0-1（越高越隨機）

    Returns:
        SparkSoupResult
    """
    assembler = get_assembler()

    # 決定來源
    sources = ["quotes", "random"]
    if auto_search:
        sources.append("duckduckgo")

    # 計算各來源數量
    count_per_source = max(3, fragment_count // len(sources))

    # 收集碎片
    fragments = await assembler.collect_fragments(
        topic=topic,
        sources=sources,
        count_per_source=count_per_source,
        randomness=randomness,
    )

    # 加入使用者自訂碎片
    if custom_fragments:
        for cf in custom_fragments:
            fragments.append(
                Fragment(
                    content=cf,
                    source=FragmentSource.USER,
                    relevance=0.8,
                )
            )

    # 隨機打亂（但保持一定結構）
    random.shuffle(fragments)

    # 組裝
    return assembler.assemble_soup(
        topic=topic,
        fragments=fragments[:fragment_count],
        topic_repetition=topic_repetition,
        trigger_categories=trigger_categories,
    )


async def collect_fragments(
    topic: str,
    sources: list[str] | None = None,
    count_per_source: int = 5,
    randomness: float = 0.5,
) -> list[Fragment]:
    """
    從多個來源收集碎片化資訊

    Args:
        topic: 相關主題
        sources: 資料來源 ["quotes", "random", "duckduckgo"]
        count_per_source: 每個來源收集數量
        randomness: 隨機性 0-1

    Returns:
        list[Fragment]
    """
    assembler = get_assembler()
    return await assembler.collect_fragments(
        topic=topic,
        sources=sources or ["quotes", "random"],
        count_per_source=count_per_source,
        randomness=randomness,
    )
