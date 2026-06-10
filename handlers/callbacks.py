import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery

from config import settings
from database import get_vacancy, update_vacancy_status
from keyboards import VacancyCallback

logger = logging.getLogger(__name__)
router = Router()

_CHAT_FILTER = F.message.chat.id == settings.telegram_chat_id


async def _mark_done(callback: CallbackQuery, label: str) -> None:
    """Append a status line to the message and remove the inline keyboard."""
    try:
        current = callback.message.html_text or callback.message.text or ""
        await callback.message.edit_text(
            current + f"\n\n{label}",
            parse_mode="HTML",
            reply_markup=None,
            disable_web_page_preview=True,
        )
    except Exception:
        # If the message can't be edited (too old / parse error), just drop the keyboard.
        await callback.message.edit_reply_markup(reply_markup=None)


@router.callback_query(VacancyCallback.filter(F.action == "interested"), _CHAT_FILTER)
async def handle_interested(callback: CallbackQuery, callback_data: VacancyCallback) -> None:
    vid = callback_data.vacancy_id
    vacancy = await get_vacancy(settings.db_path, vid)
    if not vacancy:
        await callback.answer("Вакансия не найдена в БД", show_alert=True)
        return

    await update_vacancy_status(settings.db_path, vid, "interested")
    await _mark_done(callback, "👍 <b>Сохранено как интересное</b>")
    await callback.answer("Добавлено в список интересных")


@router.callback_query(VacancyCallback.filter(F.action == "not_interested"), _CHAT_FILTER)
async def handle_not_interested(callback: CallbackQuery, callback_data: VacancyCallback) -> None:
    vid = callback_data.vacancy_id
    await update_vacancy_status(settings.db_path, vid, "not_interested")
    await _mark_done(callback, "👎 <b>Не подходит</b>")
    await callback.answer("Помечено как не подходящее")
