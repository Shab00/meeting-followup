from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    checkpoint_db_url: str
    openai_api_key: str
    allowed_origin: str = "http://localhost:8002"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
