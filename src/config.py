from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str
    openai_project_id: str = ""
    anthropic_api_key: str = ""
    database_url: str = "postgresql+asyncpg://genie:genie_pass@localhost:5432/genie_db"
    chroma_persist_dir: str = "./chroma_store"
    log_level: str = "INFO"


settings = Settings()
