import aiohttp
from typing import Optional, Dict, Any

from config import (
    NOMINATIM_BASE_URL,
    OSRM_BASE_URL,
    USER_AGENT,
    REQUEST_TIMEOUT,
    USE_BROWSER_UA,
)


class GeoService:
    """Сервис геокодинга и расчета расстояний (бесплатные API)"""

    @staticmethod
    def _headers() -> Dict[str, str]:
        """Возвращает заголовки HTTP-запроса."""
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

        # Если эмулируем браузер — добавляем браузерные заголовки
        if USE_BROWSER_UA:
            headers.update({
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            })

        return headers

    # ─── Координаты → адрес (Nominatim) ────────────────────────────────────
    @staticmethod
    async def reverse_geocode(lat: float, lon: float) -> Optional[Dict[str, Any]]:
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "addressdetails": 1,
            "accept-language": "ru",
        }

        try:
            async with aiohttp.ClientSession(
                headers=GeoService._headers(),
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as session:
                async with session.get(
                    f"{NOMINATIM_BASE_URL}/reverse", params=params
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return None
        except Exception:
            return None

    # ─── Адрес → координаты (Nominatim) ────────────────────────────────────
    @staticmethod
    async def geocode(query: str) -> Optional[Dict[str, Any]]:
        params = {
            "q": query,
            "format": "json",
            "addressdetails": 1,
            "limit": 1,
            "accept-language": "ru",
        }

        try:
            async with aiohttp.ClientSession(
                headers=GeoService._headers(),
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as session:
                async with session.get(
                    f"{NOMINATIM_BASE_URL}/search", params=params
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data[0] if data else None
                    return None
        except Exception:
            return None

    # ─── Расстояние и время маршрута (OSRM) ────────────────────────────────
    @staticmethod
    async def get_distance(
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float,
    ) -> Optional[Dict[str, Any]]:
        coords = f"{from_lon},{from_lat};{to_lon},{to_lat}"
        url = f"{OSRM_BASE_URL}/route/v1/driving/{coords}"
        params = {"overview": "false", "steps": "false"}

        try:
            async with aiohttp.ClientSession(
                headers=GeoService._headers(),
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("code") == "Ok" and data.get("routes"):
                            route = data["routes"][0]
                            return {
                                "distance_m": route["distance"],
                                "duration_s": route["duration"],
                            }
                    return None
        except Exception:
            return None

    # ─── Форматирование расстояния и времени ───────────────────────────────
    @staticmethod
    def format_distance(distance_m: float, duration_s: float) -> str:
        if distance_m < 1000:
            dist_str = f"{int(distance_m)} м"
        else:
            dist_str = f"{distance_m / 1000:.1f} км"

        if duration_s < 60:
            time_str = f"{int(duration_s)} сек"
        elif duration_s < 3600:
            time_str = f"{int(duration_s / 60)} мин"
        else:
            hours = int(duration_s // 3600)
            minutes = int((duration_s % 3600) // 60)
            time_str = f"{hours} ч {minutes} мин"

        return f"{dist_str} (~{time_str})"