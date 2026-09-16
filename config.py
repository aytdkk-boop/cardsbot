# ⚠️ Вставь сюда свой токен, полученный у @BotFather
BOT_TOKEN = "8934569747:AAFkXDxP2wwIMe5jZbefFMr-MMvW-HdIw3I"

# ID администратора (узнать у @userinfobot). 0 = не отправлять админу
ADMIN_ID = 7317419505

# Показывать пользователю полный traceback (True) или короткое сообщение (False)
SHOW_FULL_TRACEBACK = False

# Fake User-Agent для Nominatim (обязателен!)
FAKE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Nominatim API (OpenStreetMap, бесплатно)
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

# OSRM API (для маршрутов по дорогам, бесплатно)
OSRM_ROUTE_URL = "http://router.project-osrm.org/route/v1/driving"

DB_PATH = "users.db"

# Минимальный интервал между запросами к Nominatim (сек) — правило OSM
NOMINATIM_MIN_INTERVAL = 1.0

# Радиус поиска адреса вокруг города пользователя (в градусах, ~0.15° ≈ 15 км)
SEARCH_VIEWBOX_PADDING = 0.15