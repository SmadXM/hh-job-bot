import html
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from database import get_stats_today, list_interesting

logger = logging.getLogger(__name__)
router = Router()

_SCHEDULE_LABELS = {
    "remote":   "Удалённо",
    "fullDay":  "Полный день",
    "shift":    "Сменный",
    "flexible": "Гибкий",
    "hybrid":   "Гибрид",
}


def _fmt_salary(sal_from, sal_to, currency) -> str:
    if not (sal_from or sal_to):
        return "не указана"
    parts: list[str] = []
    if sal_from:
        parts.append(f"от {sal_from:,}")
    if sal_to:
        parts.append(f"до {sal_to:,}")
    cur = {"RUR": "₽", "USD": "$", "EUR": "€"}.get(currency or "", currency or "")
    return " ".join(parts) + f" {cur}"


@router.message(Command("start"), F.chat.id == settings.telegram_chat_id)
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 <b>HH.ru Job Bot</b>\n\n"
        "Я мониторю свежие вакансии C# разработчика на hh.ru и присылаю "
        "карточки с оценкой и готовым сопроводительным письмом от Gemini AI "
        "(для копирования вручную — открытое API hh.ru с 2025-12-15 не "
        "поддерживает автоматическую подачу откликов).\n\n"
        "<b>Команды:</b>\n"
        "/status       — статистика за сегодня\n"
        "/interesting  — список сохранённых вакансий\n"
        "/filters      — текущие фильтры поиска\n"
        "/pause        — приостановить автопоиск\n"
        "/resume       — возобновить автопоиск",
        parse_mode="HTML",
    )


@router.message(Command("status"), F.chat.id == settings.telegram_chat_id)
async def cmd_status(message: Message) -> None:
    stats = await get_stats_today(settings.db_path)
    await message.answer(
        "📊 <b>Статистика за сегодня:</b>\n\n"
        f"🔍 Найдено:           <b>{stats['total']}</b>\n"
        f"👍 Интересных:        <b>{stats['interested']}</b>\n"
        f"⏳ Без реакции:       <b>{stats['pending']}</b>\n"
        f"👎 Не подошло:        <b>{stats['skipped']}</b>",
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


@router.message(Command("interesting"), F.chat.id == settings.telegram_chat_id)
async def cmd_interesting(message: Message) -> None:
    items = await list_interesting(settings.db_path, limit=20)
    if not items:
        await message.answer(
            "Пока нет вакансий, отмеченных как 👍. Жмите кнопку «Интересно» под карточками."
        )
        return

    lines = [f"⭐ <b>Сохранённые вакансии</b> ({len(items)}):\n"]
    for v in items:
        score_icon = "🟢" if v["fit_score"] >= 7 else ("🟡" if v["fit_score"] >= 4 else "🔴")
        title   = html.escape(v["title"])
        company = html.escape(v["company"])
        url     = v["url"]
        salary  = _fmt_salary(v["salary_from"], v["salary_to"], v["currency"])
        lines.append(
            f"{score_icon} <b><a href='{url}'>{title}</a></b>\n"
            f"   🏢 {company}\n"
            f"   💰 {salary}  ·  📊 {v['fit_score']}/10\n"
        )

    await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@router.message(Command("pause"), F.chat.id == settings.telegram_chat_id)
async def cmd_pause(message: Message, scheduler: AsyncIOScheduler) -> None:
    if scheduler.state == 1:  # STATE_RUNNING
        scheduler.pause()
        await message.answer("⏸ Автопоиск приостановлен. Используйте /resume для возобновления.")
    else:
        await message.answer("Планировщик уже остановлен или на паузе.")


@router.message(Command("resume"), F.chat.id == settings.telegram_chat_id)
async def cmd_resume(message: Message, scheduler: AsyncIOScheduler) -> None:
    if scheduler.state == 2:  # STATE_PAUSED
        scheduler.resume()
        await message.answer("▶️ Автопоиск возобновлён.")
    else:
        await message.answer("Планировщик уже работает.")
