from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards import get_main_keyboard, get_close_inline_keyboard
from states import SearchStates
from services import GeoService
from database import db

router = Router()


# ─── /start ────────────────────────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message):
    user_name = message.from_user.full_name or "пользователь"

    await message.answer(
        f"👋 Привет, {user_name}!\n\n"
        f"<b>⚡ Я найду любой адрес, для начала работы отправь свое местоположение</b>",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )


# ─── Получение геолокации ──────────────────────────────────────────────────
@router.message(F.location)
async def handle_location(message: Message):
    lat = message.location.latitude
    lon = message.location.longitude

    geo_data = await GeoService.reverse_geocode(lat, lon)

    if not geo_data:
        await message.answer(
            "❌ Не удалось определить адрес. Попробуйте еще раз.",
            reply_markup=get_main_keyboard(),
        )
        return

    address_data = geo_data.get("address", {})

    city = (
        address_data.get("city")
        or address_data.get("town")
        or address_data.get("village")
        or address_data.get("state")
        or "Неизвестно"
    )

    road = address_data.get("road", "")
    house_number = address_data.get("house_number", "")

    if road:
        address = road
        if house_number:
            address += f", д.{house_number}"
    else:
        address = geo_data.get("display_name", "Неизвестный адрес")
        if len(address) > 60:
            address = address[:60] + "..."

    # Сохраняем в БД
    db.save_location(message.from_user.id, lat, lon, city, address)

    await message.answer(
        f"<b>✅ Местоположение определено!</b>\n\n"
        f"📍 Город : {city}\n"
        f"📍 Адрес : {address}\n"
        f"📍 Координаты : {lat:.6f}, {lon:.6f}",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )


# ─── Кнопка "🔍 Найти место" ───────────────────────────────────────────────
@router.message(F.text == "🔍 Найти место")
async def ask_for_query(message: Message, state: FSMContext):
    await state.set_state(SearchStates.waiting_for_query)

    await message.answer(
        f"<b>🔍 Поиск по адресу или координатам</b>\n\n"
        f"Введите адрес например : ул. Пример, д.1\n"
        f"Введите координаты например : 55.750289, 37.856334",
        parse_mode="HTML",
        reply_markup=get_close_inline_keyboard(),
    )


# ─── Обработка введенного запроса ──────────────────────────────────────────
@router.message(SearchStates.waiting_for_query)
async def process_search_query(message: Message, state: FSMContext):
    query = message.text.strip()

    # Проверяем: координаты или адрес?
    is_coordinates = False
    lat, lon = None, None

    try:
        parts = query.replace(" ", "").split(",")
        if len(parts) == 2:
            lat = float(parts[0])
            lon = float(parts[1])
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                is_coordinates = True
    except ValueError:
        pass

    # Получаем геоданные
    if is_coordinates:
        geo_data = await GeoService.reverse_geocode(lat, lon)
    else:
        geo_data = await GeoService.geocode(query)
        if geo_data:
            lat = float(geo_data["lat"])
            lon = float(geo_data["lon"])

    if not geo_data:
        await message.answer(
            "❌ Адрес не найден. Попробуйте другой запрос.",
            reply_markup=get_main_keyboard(),
        )
        await state.clear()
        return

    # Извлекаем данные
    address_data = geo_data.get("address", {})

    city = (
        address_data.get("city")
        or address_data.get("town")
        or address_data.get("village")
        or "Неизвестно"
    )

    road = address_data.get("road", "")
    house_number = address_data.get("house_number", "")

    if road:
        street = road
        if house_number:
            street += f", д.{house_number}"
    else:
        street = geo_data.get("display_name", query)
        if len(street) > 60:
            street = street[:60] + "..."

    found_lat = float(geo_data["lat"])
    found_lon = float(geo_data["lon"])

    # Считаем расстояние от сохраненного местоположения пользователя
    user_loc = db.get_location(message.from_user.id)

    distance_text = "Неизвестно"
    if user_loc:
        user_lat, user_lon, _, _ = user_loc
        route_data = await GeoService.get_distance(
            user_lat, user_lon, found_lat, found_lon
        )
        if route_data:
            distance_text = GeoService.format_distance(
                route_data["distance_m"], route_data["duration_s"]
            )

    await message.answer(
        f"<b>✅ Адрес найден!</b>\n\n"
        f"📍 Город : {city}\n"
        f"📍 Улица : {street}\n"
        f"📍 Координаты : {found_lat:.6f}, {found_lon:.6f}\n"
        f"🕒 Расстояние до места : {distance_text}",
        parse_mode="HTML",
        reply_markup=get_close_inline_keyboard(),
    )

    await state.clear()


# ─── Инлайн-кнопка "❌ Закрыть" ─────────────────────────────────────────────
@router.callback_query(F.data == "close_message")
async def close_message(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()