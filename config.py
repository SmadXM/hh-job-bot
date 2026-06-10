import sys
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    telegram_bot_token: str = ""
    telegram_chat_id: int = 0

    anthropic_api_key: str = ""

    search_interval_hours: int = 3
    search_query: str = "C# developer"
    search_city_id: int = 1202
    search_salary_from: int = 80000
    search_schedule: str = "remote"

    db_path: str = "/data/bot.db"

    def validate_required(self) -> None:
        required = {
            "TELEGRAM_BOT_TOKEN": self.telegram_bot_token,
            "TELEGRAM_CHAT_ID":   self.telegram_chat_id,
            "ANTHROPIC_API_KEY":  self.anthropic_api_key,
        }
        missing = [name for name, val in required.items() if not val]
        if missing:
            logger.critical(
                "Отсутствуют обязательные переменные окружения: %s",
                ", ".join(missing),
            )
            sys.exit(1)


settings = Settings()
