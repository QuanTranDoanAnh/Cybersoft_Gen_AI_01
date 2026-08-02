from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "InsightFlow API"
    database_url: str = "postgresql://copilot:copilot@db:5432/powerbi_copilot"
    data_dir: str = "/data/tvshows"
    openai_api_key: str = ""
    openai_model: str = "gpt-5.6-sol"
    frontend_origin: str = "http://localhost:3000"
    query_timeout_ms: int = 15_000
    max_query_rows: int = 500

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
