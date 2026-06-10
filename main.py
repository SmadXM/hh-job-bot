import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ai_client import load_resume
from config import settings
from database import init_db
from handlers import callbacks, commands
from hh_client import hh_client
from scheduler import create_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def on_shutdown(scheduler: AsyncIOScheduler) -> None:
    scheduler.shutdown(wait=False)
    logger.info("Планировщик остановлен")


async def main() -> None:
    settings.validate_required()
    logger.info("Конфигурация проверена ✓")

    load_resume("resume.txt")

    await init_db(settings.db_path)

    bot = Bot(token=settings.telegram_bot_token)
    dp  = Dispatcher(storage=MemoryStorage())
    dp.include_router(callbacks.router)
    dp.include_router(commands.router)

    scheduler = create_scheduler(bot, hh_client)
    dp.shutdown.register(on_shutdown)
    scheduler.start()
    logger.info(
        "Планировщик запущен. Поиск каждые %d ч. (первый запуск — сейчас)",
        settings.search_interval_hours,
    )

    logger.info("Бот запущен, ожидаю сообщений…")
    await dp.start_polling(
        bot,
        scheduler=scheduler,
        allowed_updates=["message", "callback_query"],
    )


if __name__ == "__main__":
    asyncio.run(main())
