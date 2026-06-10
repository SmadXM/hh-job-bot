from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup


class VacancyCallback(CallbackData, prefix="vac"):
    action: str     # apply | skip | edit | confirm_edit | cancel_edit
    vacancy_id: str


def vacancy_actions_keyboard(vacancy_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Откликнуться",
        callback_data=VacancyCallback(action="apply", vacancy_id=vacancy_id),
    )
    builder.button(
        text="❌ Пропустить",
        callback_data=VacancyCallback(action="skip", vacancy_id=vacancy_id),
    )
    builder.button(
        text="✏️ Редактировать письмо",
        callback_data=VacancyCallback(action="edit", vacancy_id=vacancy_id),
    )
    builder.adjust(2, 1)
    return builder.as_markup()


def confirm_edit_keyboard(vacancy_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Подтвердить и откликнуться",
        callback_data=VacancyCallback(action="confirm_edit", vacancy_id=vacancy_id),
    )
    builder.button(
        text="❌ Отмена",
        callback_data=VacancyCallback(action="cancel_edit", vacancy_id=vacancy_id),
    )
    builder.adjust(1)
    return builder.as_markup()
