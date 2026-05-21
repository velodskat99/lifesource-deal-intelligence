from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from lifesource.db import get_db


class ShoppingListItemCreate(BaseModel):
    item_name: str
    quantity: float = 1
    unit: Optional[str] = None
    notes: Optional[str] = None


def create_shopping_list_router(db_path: str) -> APIRouter:
    router = APIRouter()

    @router.get("/shopping-list")
    def list_items():
        with get_db(db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM shopping_list ORDER BY checked ASC, created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    @router.post("/shopping-list", status_code=201)
    def add_item(item: ShoppingListItemCreate):
        with get_db(db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO shopping_list (item_name, quantity, unit, notes) VALUES (?, ?, ?, ?)",
                (item.item_name, item.quantity, item.unit, item.notes),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM shopping_list WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        return dict(row)

    @router.patch("/shopping-list/{item_id}/toggle")
    def toggle_item(item_id: int):
        with get_db(db_path) as conn:
            conn.execute(
                "UPDATE shopping_list SET checked = NOT checked WHERE id = ?", (item_id,)
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM shopping_list WHERE id = ?", (item_id,)
            ).fetchone()
        return dict(row) if row else {"error": "not found"}

    @router.delete("/shopping-list/{item_id}")
    def delete_item(item_id: int):
        with get_db(db_path) as conn:
            conn.execute("DELETE FROM shopping_list WHERE id = ?", (item_id,))
            conn.commit()
        return {"status": "deleted"}

    return router
