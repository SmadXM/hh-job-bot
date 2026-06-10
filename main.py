import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from database import get_tokens, init_db
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
    # 1. Validate config
    settings.validate_required()
    logger.info("Конфигурация проверена ✓")

    # 2. Init DB
    await init_db(settings.db_path)

    # 3. Load fresher tokens from DB (written after last refresh)
    db_tokens = await get_tokens(settings.db_path)
    if db_tokens:
        hh_client.update_tokens(*db_tokens)
        logger.info("Токены загружены из БД")

    # 4. Pre-fetch resume ID so the first apply works without delay
    resume_id = await hh_client.get_resume_id()
    if not resume_id:
        logger.warning(
            "Не удалось получить ID резюме при старте. "
            "Убедитесь, что на hh.ru есть хотя бы одно резюме."
        )

    # 5. Bot + Dispatcher
    bot = Bot(token=settings.telegram_bot_token)
    dp  = Dispatcher(storage=MemoryStorage())

    # Routers — callbacks first so FSM filter runs before generic message handlers
    dp.include_router(callbacks.router)
    dp.include_router(commands.router)

    # 6. Scheduler — fires immediately on start, then every N hours
    scheduler = create_scheduler(bot, hh_client)
    dp.shutdown.register(on_shutdown)
    scheduler.start()
    logger.info(
        "Планировщик запущен. Поиск каждые %d ч. (первый запуск — сейчас)",
        settings.search_interval_hours,
    )

    # 7. Start polling — inject scheduler into handler DI
    logger.info("Бот запущен, ожидаю сообщений…")
    await dp.start_polling(
        bot,
        scheduler=scheduler,
        allowed_updates=["message", "callback_query"],
    )


if __name__ == "__main__":
    asyncio.run(main())
