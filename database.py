import sqlite3
from typing import Optional, Tuple

from config import DATABASE_PATH


class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_locations (
                    user_id INTEGER PRIMARY KEY,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    city TEXT,
                    address TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def save_location(
        self,
        user_id: int,
        lat: float,
        lon: float,
        city: str,
        address: str,
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_locations
                (user_id, latitude, longitude, city, address)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, lat, lon, city, address))
            conn.commit()

    def get_location(self, user_id: int) -> Optional[Tuple[float, float, str, str]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT latitude, longitude, city, address "
                "FROM user_locations WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            return row if row else None


db = Database()