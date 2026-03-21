from __future__ import annotations

import os
from dataclasses import dataclass

try:
    # 如果安装了 python-dotenv，就自动读取 demo/agent 下的 .env 文件。
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # 没装也没关系，继续使用系统环境变量即可。
    pass


@dataclass(slots=True)
class AppConfig:
    # 大模型鉴权信息。
    openai_api_key: str | None
    # 模型名称，例如 gpt-4o-mini。
    model_name: str
    # 兼容 OpenAI 协议的自定义网关地址。
    base_url: str | None
    # 是否打印 LangChain 详细日志。
    verbose: bool

    @property
    def langchain_enabled(self) -> bool:
        return bool(self.openai_api_key)


def load_config() -> AppConfig:
    # 同时兼容 BASEURL、OPENAI_BASE_URL 和项目私有变量名，少一点心智负担。
    base_url = os.getenv("BASEURL") or os.getenv("OPENAI_BASE_URL") or os.getenv("CHEFMATE_BASE_URL")
    return AppConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        model_name=os.getenv("CHEFMATE_MODEL", "gpt-4o-mini"),
        base_url=base_url,
        verbose=os.getenv("CHEFMATE_VERBOSE", "").lower() in {"1", "true", "yes"},
    )
