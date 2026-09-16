import asyncio
import time
from typing import Optional, Tuple

import aiohttp
from geopy.distance import geodesic

from config import (
    FAKE_USER_AGENT,
    NOMINATIM_SEARCH_URL,
    NOMINATIM_REVERSE_URL,
    OSRM_ROUTE_URL,
    NOMINATIM_MIN_INTERVAL,
    SEARCH_VIEWBOX_PADDING,
)

# Глобальный "замок" для соблюдения rate-limit Nominatim (1 запрос/сек)
_nominatim_lock = asyncio.Lock()
_last_nominatim_call = 0.0


async def _nominatim_request(url: str, params: dict) -> Optional[dict | list]:
    """Единая точка для запросов к Nominatim с rate-limit и fake UA."""
    global _last_nominatim_call

    async with _nominatim_lock:
        now = time.monotonic()
        wait = NOMINATIM_MIN_INTERVAL - (now - _last_nominatim_call)
        if wait > 0:
            await asyncio.sleep(wait)

        headers = {"User-Agent": FAKE_USER_AGENT}
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, params=params, timeout=15) as resp:
                    _last_nominatim_call = time.monotonic()
                    if resp.status != 200:
                        return None
                    return await resp.json()
        except Exception:
            _last_nominatim_call = time.monotonic()
            return None


# ---------- Форматирование короткого адреса ----------
def _short_road(road: str) -> str:
    """Приводит 'улица Котовского' → 'ул. Котовского'."""
    if not road:
        return ""
    road = road.strip()
    replacements = [
        ("улица ", "ул. "),
        ("Улица ", "ул. "),
        ("проспект ", "пр-т "),
        ("Проспект ", "пр-т "),
        ("переулок ", "пер. "),
        ("Переулок ", "пер. "),
        ("бульвар ", "б-р "),
        ("Бульвар ", "б-р "),
        ("площадь ", "пл. "),
        ("Площадь ", "пл. "),
        ("шоссе ", "ш. "),
        ("Шоссе ", "ш. "),
        ("набережная ", "наб. "),
        ("Набережная ", "наб. "),
    ]
    for old, new in replacements:
        if road.startswith(old):
            return new + road[len(old):]
    return road


def build_short_address(addr: dict) -> str:
    """
    Собирает короткий адрес вида 'ул. Котовского, д. 12'
    из полей Nominatim: road + house_number.
    """
    road = addr.get("road") or addr.get("pedestrian") or addr.get("footway") or ""
    house = addr.get("house_number") or ""

    road_short = _short_road(road)

    if road_short and house:
        return f"{road_short}, д. {house}"
    if road_short:
        return road_short
    if house:
        return f"д. {house}"
    return "—"


def extract_city(addr: dict) -> str:
    """Достаёт город из ответа Nominatim."""
    return (
        addr.get("city")
        or addr.get("town")
        or addr.get("village")
        or addr.get("municipality")
        or addr.get("state")
        or "Неизвестно"
    )


async def reverse_geocode(lat: float, lon: float) -> Optional[dict]:
    """Координаты -> короткий адрес, город."""
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "accept-language": "ru",
        "zoom": 18,
        "addressdetails": 1,
    }
    data = await _nominatim_request(NOMINATIM_REVERSE_URL, params)
    if not data or "address" not in data:
        return None

    addr = data["address"]
    return {
        "city": extract_city(addr),
        "address": build_short_address(addr),
        "address_full": data.get("display_name", "—"),
        "lat": float(data["lat"]),
        "lon": float(data["lon"]),
    }


async def forward_geocode(
    query: str,
    city: Optional[str] = None,
    viewbox: Optional[Tuple[float, float, float, float]] = None,
) -> Optional[dict]:
    """
    Адрес -> координаты/инфо.
    Если передан city — ограничиваем поиск этим городом.
    Если передан viewbox (min_lat, max_lat, min_lon, max_lon) —
    ограничиваем прямоугольником вокруг пользователя.
    """
    # Если город известен — добавляем его к запросу
    q = f"{query}, {city}" if city else query

    params = {
        "q": q,
        "format": "json",
        "accept-language": "ru",
        "limit": 1,
        "addressdetails": 1,
    }

    if viewbox:
        min_lat, max_lat, min_lon, max_lon = viewbox
        # Nominatim ждёт: left,top,right,bottom (lon_min, lat_max, lon_max, lat_min)
        params["viewbox"] = f"{min_lon},{max_lat},{max_lon},{min_lat}"
        params["bounded"] = 1  # строго внутри viewbox

    data = await _nominatim_request(NOMINATIM_SEARCH_URL, params)

    # Если ничего не нашли в городе — пробуем без привязки
    if (not data or not isinstance(data, list)) and (city or viewbox):
        params["q