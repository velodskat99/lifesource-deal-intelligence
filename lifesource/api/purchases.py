from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from lifesource.db import get_db


class PurchaseCreate(BaseModel):
    store: str
    item_name: str
    price: float
    quantity: float = 1
    unit: Optional[str] = None
    purchase_date: str
    source: str = "manual"


def create_purchases_router(db_path: str) -> APIRouter:
    router = APIRouter()

    @router.get("/purchases")
    def list_purchases(
        store: Optional[str] = Query(None),
        limit: int = Query(50),
    ):
        with get_db(db_path) as conn:
            query = "SELECT * FROM purchase_history WHERE 1=1"
            params = []

            if store:
                query += " AND store = ?"
                params.append(store)

            query += " ORDER BY purchase_date DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    @router.post("/purchases", status_code=201)
    def create_purchase(purchase: PurchaseCreate):
        with get_db(db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO purchase_history (store, item_name, price, quantity, unit,
                   purchase_date, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    purchase.store, purchase.item_name, purchase.price,
                    purchase.quantity, purchase.unit, purchase.purchase_date,
                    purchase.source,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM purchase_history WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        return dict(row)

    return router
