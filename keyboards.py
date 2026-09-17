from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)


# ✅ Ссылка на Web App с картой (GitHub Pages)
MAP_WEBAPP_BASE_URL = "https://aytdkk-boop.github.io/geo-mapcardsbot/"

# 🔄 Версия карты. Увеличивай при каждом изменении index.html,
#    чтобы Telegram не показывал старую версию из кэша.
MAP_VERSION = 8


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
    """Клавиатура с кнопкой «👁 Карта» (открывает Яндекс.Карты в Web App)."""
    map_url = f"{MAP_WEBAPP_BASE_URL}?lat={lat}&lon={lon}&v={MAP_VERSION}"
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