from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ChefMate Backend"
    app_env: str = "dev"
    app_debug: bool = True
    api_prefix: str = "/api"
    database_url: str = "mysql+pymysql://root:password@localhost:3306/chefmate"
    object_storage_bucket: str = "chefmate-assets"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4.1-mini"
    llm_timeout_seconds: float = 60.0
    vision_backend: str = "llm"
    vision_llm_base_url: str = ""
    vision_llm_api_key: str = ""
    vision_llm_model: str = ""
    vision_llm_timeout_seconds: float = 0.0
    vision_local_model_path: str | None = None
    vision_local_confidence_threshold: float = 0.35

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CHEFMATE_",
        extra="ignore",
    )


settings = Settings()
