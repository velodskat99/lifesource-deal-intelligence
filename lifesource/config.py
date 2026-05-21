import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Required secrets
    telegram_bot_token: str
    telegram_chat_id: str
    anthropic_api_key: str

    # Database
    db_path: str = str(Path(__file__).parent.parent / "lifesource.db")
    backup_dir: str = "backups"
    backup_retention_days: int = 30

    # Scoring
    deal_score_threshold: int = 40
    deal_highlight_threshold: int = 70

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
