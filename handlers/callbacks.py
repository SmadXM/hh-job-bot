import html
import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from config import settings
from database import (
    get_vacancy,
    update_cover_letter,
    update_vacancy_status,
)
from hh_client import hh_client
from keyboards import VacancyCallback, confirm_edit_keyboard

logger = logging.getLogger(__name__)
router = Router()

_CHAT_FILTER = F.message.chat.id == settings.telegram_chat_id


class EditState(StatesGroup):
    waiting_for_text    = State()
    waiting_for_confirm = State()


# ── helpers ──────────────────────────────────────────────────────────────────

async def _mark_done(callback: CallbackQuery, label: str) -> None:
    """Remove inline keyboard and append a status line to the message."""
    try:
        current = callback.message.html_text or callback.message.text or ""
        await callback.message.edit_text(
            current + f"\n\n{label}",
            parse_mode="HTML",
            reply_markup=None,
            disable_web_page_preview=True,
        )
    except Exception:
        # If the message can't be edited (e.g. too old), just remove the keyboard
        await callback.message.edit_reply_markup(reply_markup=None)


# ── Apply ─────────────────────────────────────────────────────────────────────

@router.callback_query(VacancyCallback.filter(F.action == "apply"), _CHAT_FILTER)
async def handle_apply(callback: CallbackQuery, callback_data: VacancyCallback) -> None:
    vid = callback_data.vacancy_id
    vacancy = await get_vacancy(settings.db_path, vid)
    if not vacancy:
        await callback.answer("Вакансия не найдена в БД", show_alert=True)
        return

    if vacancy["status"] == "applied":
        await callback.answer("Вы уже откликнулись на эту вакансию", show_alert=True)
        return

    await callback.answer("Отправляем отклик…")
    success = await hh_client.apply_to_vacancy(vid, vacancy["cover_letter"])

    if success:
        await update_vacancy_status(settings.db_path, vid, "applied")
        await _mark_done(callback, "✅ <b>Отклик отправлен!</b>")
    else:
        await callback.answer(
            "Ошибка при отправке отклика. Проверьте логи.", show_alert=True
        )


# ── Skip ──────────────────────────────────────────────────────────────────────

@router.callback_query(VacancyCallback.filter(F.action == "skip"), _CHAT_FILTER)
async def handle_skip(callback: CallbackQuery, callback_data: VacancyCallback) -> None:
    vid = callback_data.vacancy_id
    await update_vacancy_status(settings.db_path, vid, "skipped")
    await _mark_done(callback, "❌ <b>Пропущено</b>")
    await callback.answer("Вакансия пропущена")


# ── Edit ──────────────────────────────────────────────────────────────────────

@router.callback_query(VacancyCallback.filter(F.action == "edit"), _CHAT_FILTER)
async def handle_edit(
    callback: CallbackQuery,
    callback_data: VacancyCallback,
    state: FSMContext,
) -> None:
    vid = callback_data.vacancy_id
    vacancy = await get_vacancy(settings.db_path, vid)
    if not vacancy:
        await callback.answer("Вакансия не найдена в БД", show_alert=True)
        return

    await state.set_state(EditState.waiting_for_text)
    await state.update_data(vacancy_id=vid)

    await callback.message.answer(
        f"✏️ Текущее письмо:\n\n<blockquote>{html.escape(vacancy['cover_letter'])}</blockquote>\n\n"
        "Отправьте <b>новый текст</b> сопроводительного письма:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(EditState.waiting_for_text, F.chat.id == settings.telegram_chat_id)
async def receive_new_letter(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    vid  = data["vacancy_id"]
    new_text = (message.text or "").strip()

    if not new_text:
        await message.answer("Письмо не может быть пустым. Попробуйте ещё раз:")
        return

    await state.set_state(EditState.waiting_for_confirm)
    await state.update_data(new_cover_letter=new_text)

    await message.answer(
        f"📝 <b>Предварительный просмотр:</b>\n\n{html.escape(new_text)}\n\n"
        "Откликнуться с этим письмом?",
        parse_mode="HTML",
        reply_markup=confirm_edit_keyboard(vid),
    )


@router.callback_query(VacancyCallback.filter(F.action == "confirm_edit"), _CHAT_FILTER)
async def handle_confirm_edit(
    callback: CallbackQuery,
    callback_data: VacancyCallback,
    state: FSMContext,
) -> None:
    data  = await state.get_data()
    vid   = callback_data.vacancy_id
    letter = data.get("new_cover_letter", "")

    await update_cover_letter(settings.db_path, vid, letter)
    await callback.answer("Отправляем отклик…")

    success = await hh_client.apply_to_vacancy(vid, letter)
    if success:
        await update_vacancy_status(settings.db_path, vid, "applied")
        await callback.message.edit_text(
            "✅ <b>Отклик отправлен с вашим письмом!</b>",
            parse_mode="HTML",
            reply_markup=None,
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка при отправке отклика. Проверьте логи.",
            reply_markup=None,
        )

    await state.clear()


@router.callback_query(VacancyCallback.filter(F.action == "cancel_edit"), _CHAT_FILTER)
async def handle_cancel_edit(
    callback: CallbackQuery,
    callback_data: VacancyCallback,
    state: FSMContext,
) -> None:
    await state.clear()
    await callback.message.edit_text("↩️ Редактирование отменено.", reply_markup=None)
    await callback.answer("Отменено")
