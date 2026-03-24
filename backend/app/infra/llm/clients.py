from __future__ import annotations

from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from openai import OpenAI

from app.config import settings


@dataclass(frozen=True)
class LLMEndpointConfig:
    base_url: str
    api_key: str
    model: str
    timeout_seconds: float


def resolve_general_llm_config() -> LLMEndpointConfig:
    return LLMEndpointConfig(
        base_url=settings.llm_base_url.rstrip("/"),
        api_key=settings.llm_api_key.strip(),
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )


def resolve_vision_llm_config() -> LLMEndpointConfig:
    general = resolve_general_llm_config()
    return LLMEndpointConfig(
        base_url=(settings.vision_llm_base_url or general.base_url).rstrip("/"),
        api_key=(settings.vision_llm_api_key or general.api_key).strip(),
        model=settings.vision_llm_model or general.model,
        timeout_seconds=settings.vision_llm_timeout_seconds or general.timeout_seconds,
    )


def build_openai_client(config: LLMEndpointConfig | None = None) -> OpenAI:
    resolved = config or resolve_general_llm_config()
    return OpenAI(
        base_url=resolved.base_url,
        api_key=resolved.api_key,
        timeout=resolved.timeout_seconds,
    )


def build_langchain_chat_model(
    *,
    config: LLMEndpointConfig | None = None,
    temperature: float = 0.1,
) -> ChatOpenAI:
    resolved = config or resolve_general_llm_config()
    return ChatOpenAI(
        base_url=resolved.base_url,
        api_key=resolved.api_key,
        model=resolved.model,
        timeout=resolved.timeout_seconds,
        temperature=temperature,
    )
