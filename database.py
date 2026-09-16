import aiosqlite
from config import DB_PATH


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                latitude    REAL,
                longitude   REAL,
                city        TEXT,
                address     TEXT
            )
            """
        )
        await db.commit()


async def save_user_location(
    user_id: int,
    username: str,
    latitude: float,
    longitude: float,
    city: str,
    address: str,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, username, latitude, longitude, city, address)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                latitude=excluded.latitude,
                longitude=excluded.longitude,
                city=excluded.city,
                address=excluded.address
            """,
            (user_id, username, latitude, longitude, city, address),
        )
        await db.commit()


async def get_user_location(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None