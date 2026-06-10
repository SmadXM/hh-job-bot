import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from database import get_stats_today

logger = logging.getLogger(__name__)
router = Router()

_SCHEDULE_LABELS = {
    "remote":   "Удалённо",
    "fullDay":  "Полный день",
    "shift":    "Сменный",
    "flexible": "Гибкий",
    "hybrid":   "Гибрид",
}


@router.message(Command("start"), F.chat.id == settings.telegram_chat_id)
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 <b>HH.ru Job Bot</b>\n\n"
        "Я автоматически ищу вакансии C# разработчика на hh.ru и отправляю "
        "персонализированные отклики с сопроводительными письмами от Claude AI.\n\n"
        "<b>Команды:</b>\n"
        "/status  — статистика за сегодня\n"
        "/filters — текущие фильтры поиска\n"
        "/pause   — приостановить автопоиск\n"
        "/resume  — возобновить автопоиск",
        parse_mode="HTML",
    )


@router.message(Command("status"), F.chat.id == settings.telegram_chat_id)
async def cmd_status(message: Message) -> None:
    stats = await get_stats_today(settings.db_path)
    await message.answer(
        "📊 <b>Статистика за сегодня:</b>\n\n"
        f"🔍 Найдено:            <b>{stats['total']}</b>\n"
        f"✅ Откликнулся:        <b>{stats['applied']}</b>\n"
        f"⏳ Ожидают решения:    <b>{stats['pending']}</b>\n"
        f"❌ Пропущено:          <b>{stats['skipped']}</b>",
        parse_mode="HTML",
    )


@router.message(Command("filters"), F.chat.id == settings.telegram_chat_id)
async def cmd_filters(message: Message) -> None:
    sched_label = _SCHEDULE_LABELS.get(settings.search_schedule, settings.search_schedule)
    await message.answer(
        "🔧 <b>Текущие фильтры:</b>\n\n"
        f"🔍 Запрос:           <code>{settings.search_query}</code>\n"
        f"📍 ID города:        <code>{settings.search_city_id}</code>\n"
        f"💰 Зарплата от:      <code>{settings.search_salary_from:,} ₽</code>\n"
        f"🏠 График:           <code>{sched_label}</code>\n"
        f"⏰ Интервал:         <code>каждые {settings.search_interval_hours} ч.</code>",
        parse_mode="HTML",
    )


@router.message(Command("pause"), F.chat.id == settings.telegram_chat_id)
async def cmd_pause(message: Message, scheduler: AsyncIOScheduler) -> None:
    if scheduler.state == 1:  # STATE_RUNNING = 1
        scheduler.pause()
        await message.answer("⏸ Автопоиск приостановлен. Используйте /resume для возобновления.")
    else:
        await message.answer("Планировщик уже остановлен или на паузе.")


@router.message(Command("resume"), F.chat.id == settings.telegram_chat_id)
async def cmd_resume(message: Message, scheduler: AsyncIOScheduler) -> None:
    if scheduler.state == 2:  # STATE_PAUSED = 2
        scheduler.resume()
        await message.answer("▶️ Автопоиск возобновлён.")
    else:
        await message.answer("Планировщик уже работает.")
