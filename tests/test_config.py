import os
from unittest.mock import patch

from lifesource.config import get_settings, Settings


def test_config_loads_from_env():
    env = {
        "TELEGRAM_BOT_TOKEN": "test-token-123",
        "TELEGRAM_CHAT_ID": "456",
        "ANTHROPIC_API_KEY": "test-anthropic-key",
    }
    with patch.dict(os.environ, env, clear=False):
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.telegram_bot_token == "test-token-123"
        assert settings.telegram_chat_id == "456"
        assert settings.anthropic_api_key == "test-anthropic-key"


def test_config_has_defaults():
    env = {
        "TELEGRAM_BOT_TOKEN": "t",
        "TELEGRAM_CHAT_ID": "1",
        "ANTHROPIC_API_KEY": "k",
    }
    with patch.dict(os.environ, env, clear=False):
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.db_path.endswith("lifesource.db")
        assert settings.backup_dir == "backups"
        assert settings.deal_score_threshold == 40
