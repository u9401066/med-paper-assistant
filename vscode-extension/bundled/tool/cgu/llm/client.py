"""
CGU LLM Client

使用 LangChain + Ollama 整合，提供 Structured Output
Ollama 服務持續運行（ollama serve），客戶端只需連接 API
"""

import os
from typing import TypeVar, Type

from pydantic import BaseModel
from langchain_ollama import ChatOllama

# 預設配置（Ollama）
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:3b"


T = TypeVar("T", bound=BaseModel)


class LLMConfig(BaseModel):
    """LLM 配置"""
    base_url: str = DEFAULT_OLLAMA_BASE_URL
    model: str = DEFAULT_MODEL
    temperature: float = 0.7
    timeout: float = 120.0


def get_llm_config() -> LLMConfig:
    """取得 LLM 配置（從環境變數）"""
    return LLMConfig(
        base_url=os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
        model=os.getenv("CGU_OLLAMA_MODEL", os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)),
        temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
        timeout=float(os.getenv("OLLAMA_TIMEOUT", "120.0")),
    )


class CGULLMClient:
    """
    CGU LLM 客戶端

    整合 LangChain + Ollama，使用 with_structured_output 產生結構化輸出
    Ollama 服務持續運行（ollama serve），客戶端只是連接 API
    """

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or get_llm_config()

        # 建立 LangChain Ollama 客戶端
        self._llm = ChatOllama(
            base_url=self.config.base_url,
            model=self.config.model,
            temperature=self.config.temperature,
        )

    @property
    def llm(self) -> ChatOllama:
        """LangChain ChatOllama 實例"""
        return self._llm

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """
        基本生成（非結構化）

        Args:
            prompt: 使用者提示
            system_prompt: 系統提示
            temperature: 溫度（覆蓋預設）

        Returns:
            生成的文字
        """
        from langchain_core.messages import SystemMessage, HumanMessage

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        # 如果需要不同溫度，創建臨時客戶端
        if temperature is not None and temperature != self.config.temperature:
            llm = ChatOllama(
                base_url=self.config.base_url,
                model=self.config.model,
                temperature=temperature,
            )
            response = llm.invoke(messages)
        else:
            response = self._llm.invoke(messages)

        content = response.content
        if isinstance(content, str):
            return content
        return str(content) if content else ""

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: str | None = None,
        temperature: float | None = None,
    ) -> T:
        """
        結構化生成（使用 LangChain with_structured_output）

        Args:
            prompt: 使用者提示
            response_model: Pydantic 模型類別
            system_prompt: 系統提示
            temperature: 溫度

        Returns:
            Pydantic 模型實例
        """
        from langchain_core.messages import SystemMessage, HumanMessage

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        # 使用 with_structured_output 取得結構化輸出
        if temperature is not None and temperature != self.config.temperature:
            llm = ChatOllama(
                base_url=self.config.base_url,
                model=self.config.model,
                temperature=temperature,
            )
            structured_llm = llm.with_structured_output(response_model)
        else:
            structured_llm = self._llm.with_structured_output(response_model)

        response = structured_llm.invoke(messages)
        return response  # type: ignore[return-value]

    # 保留同步別名以保持向後相容
    def generate_sync(self, *args, **kwargs) -> str:
        """同步版本（別名）"""
        return self.generate(*args, **kwargs)

    def generate_structured_sync(self, *args, **kwargs):
        """同步版本（別名）"""
        return self.generate_structured(*args, **kwargs)


# 全域客戶端實例
_llm_client: CGULLMClient | None = None


def get_llm_client(config: LLMConfig | None = None) -> CGULLMClient:
    """
    取得全域 LLM 客戶端

    Args:
        config: 可選的 LLM 配置，傳入時會重新創建客戶端
    """
    global _llm_client
    if config is not None:
        # 傳入新配置時，重新創建客戶端
        _llm_client = CGULLMClient(config)
    elif _llm_client is None:
        _llm_client = CGULLMClient()
    return _llm_client


def reset_llm_client() -> None:
    """重置全域 LLM 客戶端"""
    global _llm_client
    _llm_client = None
