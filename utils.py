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
    """Приводит 'улица Котовского' -> 'ул. Котовского'."""
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
        params["q"] = query
        params.pop("viewbox", None)
        params.pop("bounded", None)
        data = await _nominatim_request(NOMINATIM_SEARCH_URL, params)

    if not data or not isinstance(data, list):
        return None

    item = data[0]
    addr = item.get("address", {})
    return {
        "city": extract_city(addr) or (city or "Неизвестно"),
        "address": build_short_address(addr),
        "address_full": item.get("display_name", "—"),
        "lat": float(item["lat"]),
        "lon": float(item["lon"]),
    }


def make_viewbox(lat: float, lon: float) -> Tuple[float, float, float, float]:
    """Прямоугольник вокруг пользователя: (min_lat, max_lat, min_lon, max_lon)."""
    p = SEARCH_VIEWBOX_PADDING
    return (lat - p, lat + p, lon - p, lon + p)


async def osrm_route(
    origin: Tuple[float, float], dest: Tuple[float, float]
) -> Optional[dict]:
    """Реальное расстояние по дорогам и время в пути через OSRM."""
    coords = f"{origin[1]},{origin[0]};{dest[1]},{dest[0]}"
    url = f"{OSRM_ROUTE_URL}/{coords}"
    params = {"overview": "false", "alternatives": "false", "steps": "false"}

    headers = {"User-Agent": FAKE_USER_AGENT}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, params=params, timeout=15) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if data.get("code") != "Ok" or not data.get("routes"):
                    return None
                route = data["routes"][0]
                return {
                    "distance_km": route["distance"] / 1000.0,
                    "duration_min": route["duration"] / 60.0,
                }
    except Exception:
        return None


def calculate_straight_distance(
    origin: Tuple[float, float], dest: Tuple[float, float]
) -> str:
    """Расстояние по прямой (запасной вариант)."""
    dist_km = geodesic(origin, dest).km
    if dist_km < 1:
        meters = int(round(dist_km * 1000))
        return f"{meters} м"
    return f"{dist_km:.2f} км"


def format_route(route: Optional[dict], fallback: str) -> str:
    """Форматирует блок расстояния/времени."""
    if not route:
        return f"{fallback} (по прямой)"

    km = route["distance_km"]
    minutes = route["duration_min"]

    if km < 1:
        dist_str = f"{int(round(km * 1000))} м"
    else:
        dist_str = f"{km:.2f} км"

    if minutes < 1:
        time_str = "0 мин"
    elif minutes < 60:
        time_str = f"{int(round(minutes))} мин"
    else:
        hours = int(minutes // 60)
        mins = int(round(minutes % 60))
        time_str = f"{hours} ч {mins} мин"

    return f"{dist_str} (~{time_str} в пути)"


def parse_coordinates(text: str) -> Optional[Tuple[float, float]]:
    """Парсит строку типа '55.750289, 37.856334'."""
    try:
        parts = text.replace(" ", "").split(",")
        if len(parts) != 2:
            return None
        lat, lon = float(parts[0]), float(parts[1])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None
        return lat, lon
    except ValueError:
        return None