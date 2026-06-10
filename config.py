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

    hh_client_id: str = ""
    hh_client_secret: str = ""
    hh_access_token: str = ""
    hh_refresh_token: str = ""

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
            "HH_CLIENT_ID": self.hh_client_id,
            "HH_CLIENT_SECRET": self.hh_client_secret,
            "HH_ACCESS_TOKEN": self.hh_access_token,
            "HH_REFRESH_TOKEN": self.hh_refresh_token,
            "TELEGRAM_BOT_TOKEN": self.telegram_bot_token,
            "TELEGRAM_CHAT_ID": self.telegram_chat_id,
            "ANTHROPIC_API_KEY": self.anthropic_api_key,
        }
        missing = [name for name, val in required.items() if not val]
        if missing:
            logger.critical(
                "Отсутствуют обязательные переменные окружения: %s",
                ", ".join(missing),
            )
            sys.exit(1)


settings = Settings()
