"""User settings API."""
import json

from fastapi import APIRouter
from pydantic import BaseModel

from lifesource.db import get_db


# Create settings table if not exists
SETTINGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

DEFAULT_SETTINGS = {
    "gas_zones": json.dumps([
        {"name": "home", "address": "Your city, ST", "radius_miles": 5},
    ]),
    "active_stores": json.dumps(["heb", "costco", "99ranch", "hmart"]),
    "deal_score_threshold": "40",
    "telegram_digest_sections": json.dumps(["deals", "gas", "watchlist", "plan"]),
}


class SettingUpdate(BaseModel):
    key: str
    value: str


def create_settings_router(db_path: str) -> APIRouter:
    router = APIRouter()

    def _ensure_settings_table(conn):
        conn.executescript(SETTINGS_SCHEMA)
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        conn.commit()

    @router.get("/settings")
    def get_settings_api():
        with get_db(db_path) as conn:
            _ensure_settings_table(conn)
            rows = conn.execute("SELECT * FROM settings").fetchall()
        result = {}
        for row in rows:
            try:
                result[row["key"]] = json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                result[row["key"]] = row["value"]
        return result

    @router.put("/settings")
    def update_setting(setting: SettingUpdate):
        with get_db(db_path) as conn:
            _ensure_settings_table(conn)
            conn.execute(
                """INSERT INTO settings (key, value, updated_at)
                   VALUES (?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP""",
                (setting.key, setting.value, setting.value),
            )
            conn.commit()
        return {"status": "updated", "key": setting.key}

    return router
