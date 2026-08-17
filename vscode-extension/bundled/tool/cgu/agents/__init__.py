"""
CGU Multi-Agent System

多 Agent 並發創意架構 - 避免 Context 污染
"""

from cgu.agents.base import AgentPersonality, CreativeAgent
from cgu.agents.critic import CriticAgent
from cgu.agents.explorer import ExplorerAgent
from cgu.agents.orchestrator import AgentOrchestrator
from cgu.agents.spark import SparkEngine
from cgu.agents.wildcard import WildcardAgent

__all__ = [
    "CreativeAgent",
    "AgentPersonality",
    "ExplorerAgent",
    "CriticAgent",
    "WildcardAgent",
    "AgentOrchestrator",
    "SparkEngine",
]
