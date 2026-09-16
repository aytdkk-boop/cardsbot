import html
import logging
import traceback

from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ErrorEvent

from config import ADMIN_ID, SHOW_FULL_TRACEBACK
from database import get_user_location, save_user_location
from keyboards import close_inline_kb, main_menu_kb, result_kb
from utils import (
    forward_geocode,
    reverse_geocode,
    parse_coordinates,
    calculate_straight_distance,
    osrm_route,
    format_route,
    make_viewbox,
)

router = Router()
logger = logging.getLogger(__name__)


class SearchState(StatesGroup):
    waiting_query = State()


# ================= /start =================
@router.message(CommandStart())
async def cmd_start(message: types.Message):
    name = message.from_user.full_name or message.from_user.username or "друг"
    await message.answer(
        f"👋 Привет, <b>{name}</b>!\n\n"
        f"<b>⚡ Я найду любой адрес, для начала работы отправь свое местоположение</b>",
        reply_markup=main_menu_kb(),
    )


# ================= Приём локации =================
@router.message(F.location)
async def handle_location(message: types.Message):
    lat = message.location.latitude
    lon = message.location.longitude

    info = await reverse_geocode(lat, lon)

    if not info:
        await message.answer("⚠️ Не удалось определить адрес. Попробуйте ещё раз.")
        return

    await save_user_location(
        user_id=message.from_user.id,
        username=message.from_user.username or message.from_user.full_name,
        latitude=info["lat"],
        longitude=info["lon"],
        city=info["city"],
        address=info["address"],
    )

    await message.answer(
        f"<b>✅ Местоположение определено!</b>\n"
        f"📍 Город : {info['city']}\n"
        f"📍 Адрес : {info['address']}\n"
        f"📍 Координаты : {info['lat']:.6f}, {info['lon']:.6f}",
        reply_markup=result_kb(info["lat"], info["lon"]),
    )


# ================= Кнопка "🔍 Найти место" =================
@router.message(F.text == "🔍 Найти место")
async def ask_query(message: types.Message, state: FSMContext):
    user_loc = await get_user_location(message.from_user.id)
    if not user_loc:
        await message.answer(
            "⚠️ Сначала отправьте своё местоположение кнопкой ниже 👇",
            reply_markup=main_menu_kb(),
        )
        return

    await state.set_state(SearchState.waiting_query)
    await message.answer(
        "<b>🔍 Поиск по адресу или координатам</b>\n"
        "Введите адрес, например : ул. Пример, д.1\n"
        "Введите координаты, например : 55.750289, 37.856334",
        reply_markup=close_inline_kb(),
    )


# ================= Обработка ввода =================
@router.message(SearchState.waiting_query)
async def handle_query(message: types.Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("⚠️ Отправьте текст с адресом или координатами.")
        return

    await state.clear()

    user_loc = await get_user_location(message.from_user.id)
    if not user_loc:
        await message.answer("⚠️ Сначала отправьте своё местоположение.")
        return

    origin = (user_loc["latitude"], user_loc["longitude"])
    user_city = user_loc.get("city") or None

    # Пробуем как координаты, иначе — как адрес (в городе пользователя)
    coords = parse_coordinates(text)
    if coords:
        info = await reverse_geocode(coords[0], coords[1])
    else:
        viewbox = make_viewbox(origin[0], origin[1])
        info = await forward_geocode(text, city=user_city, viewbox=viewbox)

    if not info:
        await message.answer("❌ Ничего не найдено. Попробуйте другой адрес.")
        return

    dest = (info["lat"], info["lon"])

    route = await osrm_route(origin, dest)
    fallback = calculate_straight_distance(origin, dest)
    distance_str = format_route(route, fallback)

    await message.answer(
        f"<b>✅ Адрес найден!</b>\n"
        f"📍 Город : {info['city']}\n"
        f"📍 Улица : {info['address']}\n"
        f"📍 Координаты : {info['lat']:.6f}, {info['lon']:.6f}\n"
        f"🕒 Расстояние до места : {distance_str}",
        reply_markup=result_kb(info["lat"], info["lon"]),
    )


# ================= Кнопка "❌ Закрыть" =================
@router.callback_query(F.data == "close")
async def close_message(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
    await callback.answer("Закрыто")


# ================= Глобальный обработчик ошибок =================
@router.errors()
async def global_error_handler(event: ErrorEvent):
    exc = event.exception
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    logger.error("❌ Ошибка при обработке апдейта:\n%s", tb)

    update = event.update
    chat_id = None
    user_info = "—"

    if update.message:
        chat_id = update.message.chat.id
        u = update.message.from_user
        user_info = f"{u.full_name} (id={u.id}, @{u.username})"
    elif update.callback_query:
        chat_id = update.callback_query.message.chat.id
        u = update.callback_query.from_user
        user_info = f"{u.full_name} (id={u.id}, @{u.username})"

    if chat_id:
        if SHOW_FULL_TRACEBACK:
            error_text = f"❌ <b>Ошибка!</b>\n\n<pre>{html.escape(tb[-3500:])}</pre>"
        else:
            error_text = (
                f"❌ <b>Ошибка!</b>\n\n"
                f"<code>{html.escape(type(exc).__name__)}: "
                f"{html.escape(str(exc))}</code>"
            )
        try:
            await event.bot.send_message(chat_id, error_text)
        except Exception as send_err:
            logger.error("Не удалось отправить ошибку в чат: %s", send_err)

    if ADMIN_ID and ADMIN_ID != chat_id:
        try:
            await event.bot.send_message(
                ADMIN_ID,
                f"⚠️ Ошибка у {user_info}:\n"
                f"<code>{html.escape(type(exc).__name__)}: "
                f"{html.escape(str(exc))}</code>\n\n"
                f"<pre>{html.escape(tb[-2500:])}</pre>",
            )
        except Exception as admin_err:
            logger.error("Не удалось уведомить админа: %s", admin_err)

    return True