from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_UPLOAD_DIR = BACKEND_DIR / "storage" / "uploads"


class Settings(BaseSettings):
    app_name: str = "ChefMate Backend"
    app_env: str = "dev"
    app_debug: bool = True
    api_prefix: str = "/api"
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str = "mysql+pymysql://root:password@localhost:3306/chefmate"

    auth_session_ttl_hours: int = 24 * 7
    auth_token_prefix: str = "cm_"
    password_hash_iterations: int = 480000

    conversation_memory_window: int = 12
    conversation_summary_trigger_messages: int = 24
    conversation_history_task_limit: int = 10
    conversation_suggestion_count: int = 3
    conversation_title_max_length: int = 36

    object_storage_bucket: str = "chefmate-assets"
    upload_dir: str = str(DEFAULT_UPLOAD_DIR)
    asset_url_prefix: str = "/assets"
    max_upload_size_bytes: int = 8 * 1024 * 1024

    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4.1-mini"
    llm_timeout_seconds: float = 120.0
    llm_temperature: float = 0.25

    vision_backend: str = "llm"
    vision_llm_base_url: str = ""
    vision_llm_api_key: str = ""
    vision_llm_model: str = ""
    vision_llm_timeout_seconds: float = 0.0
    vision_local_model_path: str | None = None
    vision_local_confidence_threshold: float = 0.35

    recommendation_sample_size: int = 3

    voice_volcengine_ws_url: str = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
    voice_volcengine_app_key: str = ""
    voice_volcengine_access_key: str = ""
    voice_volcengine_resource_id: str = "volc.bigasr.sauc.duration"
    voice_sample_rate_hz: int = 16000
    voice_chunk_ms: int = 200
    voice_wakeup_clip_ms: int = 1500
    voice_silence_timeout_ms: int = 2000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CHEFMATE_",
        extra="ignore",
    )

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir).resolve()

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_allowed_origins.split(",") if item.strip()]


settings = Settings()
