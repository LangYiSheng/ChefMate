from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ChefMate Backend"
    app_env: str = "dev"
    app_debug: bool = True
    api_prefix: str = "/api"
    database_url: str = "mysql+pymysql://root:password@localhost:3306/chefmate"
    object_storage_bucket: str = "chefmate-assets"
    llm_provider: str = "placeholder"
    llm_model: str = "placeholder-model"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CHEFMATE_",
        extra="ignore",
    )


settings = Settings()
