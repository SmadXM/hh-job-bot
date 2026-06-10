import html
import logging
import re
from datetime import datetime
from typing import Optional

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ai_client import analyze_vacancy
from config import settings
from database import is_vacancy_seen, save_vacancy
from hh_client import HHClient
from keyboards import vacancy_actions_keyboard

logger = logging.getLogger(__name__)

_STRIP_TAGS = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _STRIP_TAGS.sub(" ", text).strip()


def _fmt_salary(vacancy: dict) -> str:
    sal = vacancy.get("salary")
    if not sal:
        return "не указана"
    parts: list[str] = []
    if sal.get("from"):
        parts.append(f"от {sal['from']:,}")
    if sal.get("to"):
        parts.append(f"до {sal['to']:,}")
    cur = {"RUR": "₽", "USD": "$", "EUR": "€"}.get(sal.get("currency", ""), sal.get("currency", ""))
    return " ".join(parts) + f" {cur}"


def build_vacancy_card(details: dict, fit_score: int, fit_reasoning: str, cover_letter: str) -> str:
    title   = html.escape(details.get("name", "Без названия"))
    company = html.escape(details.get("employer", {}).get("name", "Неизвестно"))
    salary  = _fmt_salary(details)
    area    = html.escape(details.get("area", {}).get("name", ""))
    sched   = html.escape(details.get("schedule", {}).get("name", ""))
    url     = details.get("alternate_url", "")

    score_icon = "🟢" if fit_score >= 7 else ("🟡" if fit_score >= 4 else "🔴")

    return (
        f"🏢 <b>{company}</b>\n"
        f"💼 <b><a href='{url}'>{title}</a></b>\n"
        f"💰 {salary}\n"
        f"📍 {area}  ·  {sched}\n\n"
        f"{score_icon} <b>Оценка: {fit_score}/10</b>\n"
        f"<i>{html.escape(fit_reasoning)}</i>\n\n"
        f"📝 <b>Сопроводительное письмо:</b>\n"
        f"{html.escape(cover_letter)}"
    )


async def search_and_notify(bot: Bot, hh: HHClient) -> None:
    logger.info("Запуск поиска вакансий...")
    try:
        vacancies = await hh.search_vacancies(page=0)
        logger.info("Получено %d вакансий из API", len(vacancies))

        new_count = 0
        for item in vacancies:
            vid = item["id"]
            if await is_vacancy_seen(settings.db_path, vid):
                continue

            details = await hh.get_vacancy_details(vid)
            if not details:
                continue

            description = _strip_html(details.get("description") or "")
            title   = details.get("name", "")
            company = details.get("employer", {}).get("name", "")

            analysis = await analyze_vacancy(title, company, description)
            fit_score     = analysis["fit_score"]
            fit_reasoning = analysis["fit_reasoning"]
            cover_letter  = analysis["cover_letter"]

            sal      = details.get("salary") or {}
            sal_from = sal.get("from")
            sal_to   = sal.get("to")
            currency = sal.get("currency")

            card_text = build_vacancy_card(details, fit_score, fit_reasoning, cover_letter)
            keyboard  = vacancy_actions_keyboard(vid)

            msg = await bot.send_message(
                chat_id=settings.telegram_chat_id,
                text=card_text,
                parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )

            await save_vacancy(
                settings.db_path,
                vacancy_id=vid,
                title=title,
                company=company,
                salary_from=sal_from,
                salary_to=sal_to,
                currency=currency,
                city=details.get("area", {}).get("name", ""),
                schedule=details.get("schedule", {}).get("name", ""),
                url=details.get("alternate_url", ""),
                fit_score=fit_score,
                fit_reasoning=fit_reasoning,
                cover_letter=cover_letter,
                telegram_message_id=msg.message_id,
            )
            new_count += 1
            logger.info("Вакансия %s «%s» — оценка %d/10", vid, title, fit_score)

        logger.info("Новых вакансий обработано: %d", new_count)
    except Exception:
        logger.exception("Критическая ошибка в search_and_notify")


def create_scheduler(bot: Bot, hh: HHClient) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        search_and_notify,
        trigger=IntervalTrigger(hours=settings.search_interval_hours),
        args=[bot, hh],
        id="job_search",
        name="Поиск вакансий",
        replace_existing=True,
        misfire_grace_time=300,
        next_run_time=datetime.utcnow(),  # run immediately on start
    )
    return scheduler
