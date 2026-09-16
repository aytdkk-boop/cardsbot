from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)


# ✅ Ссылка на твой Web App с картой (GitHub Pages)
MAP_WEBAPP_BASE_URL = "https://aytdkk-boop.github.io/geo-mapcardsbot/"


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Найти место")],
            [KeyboardButton(text="📍 Отправить местоположение", request_location=True)],
        ],
        resize_keyboard=True,
    )


def close_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
        ]
    )


def result_kb(lat: float, lon: float) -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой «👁 Карта»."""
    map_url = f"{MAP_WEBAPP_BASE_URL}?lat={lat}&lon={lon}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Закрыть", callback_data="close"),
                InlineKeyboardButton(
                    text="👁 Карта",
                    web_app=WebAppInfo(url=map_url),
                ),
            ]
        ]
    )