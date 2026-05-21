from fastapi import APIRouter, Query
from typing import Optional

from lifesource.db import get_db


def create_deals_router(db_path: str) -> APIRouter:
    router = APIRouter()

    @router.get("/deals")
    def list_deals(
        store: Optional[str] = Query(None),
        category: Optional[str] = Query(None),
    ):
        with get_db(db_path) as conn:
            query = "SELECT * FROM deals WHERE 1=1"
            params = []

            if store:
                query += " AND store = ?"
                params.append(store)
            if category:
                query += " AND category = ?"
                params.append(category)

            query += " ORDER BY created_at DESC"
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    @router.get("/deals/search")
    def search_deals(q: str = Query(...)):
        with get_db(db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM deals WHERE item_name LIKE ? ORDER BY created_at DESC",
                (f"%{q}%",),
            ).fetchall()
        return [dict(row) for row in rows]

    return router
