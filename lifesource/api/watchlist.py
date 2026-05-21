"""Ad-hoc purchase watchlist API."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from lifesource.db import get_db


class WatchlistItemCreate(BaseModel):
    query: str
    target_price: Optional[float] = None
    include_used: bool = True


def create_watchlist_router(db_path: str) -> APIRouter:
    router = APIRouter()

    @router.get("/watchlist")
    def list_watchlist(active_only: bool = True):
        with get_db(db_path) as conn:
            query = "SELECT * FROM watchlist"
            if active_only:
                query += " WHERE active = TRUE"
            query += " ORDER BY created_at DESC"
            rows = conn.execute(query).fetchall()
        return [dict(row) for row in rows]

    @router.post("/watchlist", status_code=201)
    def add_to_watchlist(item: WatchlistItemCreate):
        with get_db(db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO watchlist (query, target_price, include_used) VALUES (?, ?, ?)",
                (item.query, item.target_price, item.include_used),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM watchlist WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        return dict(row)

    @router.delete("/watchlist/{item_id}")
    def remove_from_watchlist(item_id: int):
        with get_db(db_path) as conn:
            conn.execute("UPDATE watchlist SET active = FALSE WHERE id = ?", (item_id,))
            conn.commit()
        return {"status": "deactivated"}

    return router
