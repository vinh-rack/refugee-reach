from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    database_url: str
    rabbitmq_url: str
    redis_url: str
    openai_api_key: str
    telegram_bot_token: str
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_graph_api_version: str = "v23.0"
    app_base_url: str
    newsapi_key: str

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        extra="ignore",
    )

settings = Settings()
