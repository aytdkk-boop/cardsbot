from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура с не инлайн кнопками"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Найти место")],
            [KeyboardButton(text="📍 Отправить местоположение", request_location=True)],
        ],
        resize_keyboard=True,
    )


def get_close_inline_keyboard() -> InlineKeyboardMarkup:
    """Инлайн клавиатура с кнопкой закрыть"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="close_message")]
        ]
    )