from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup


class VacancyCallback(CallbackData, prefix="vac"):
    action: str     # interested | not_interested
    vacancy_id: str


def vacancy_actions_keyboard(vacancy_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="👍 Интересно",
        callback_data=VacancyCallback(action="interested", vacancy_id=vacancy_id),
    )
    builder.button(
        text="👎 Не подходит",
        callback_data=VacancyCallback(action="not_interested", vacancy_id=vacancy_id),
    )
    builder.adjust(2)
    return builder.as_markup()
