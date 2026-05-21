from fastapi import APIRouter

from lifesource.db import get_db


def create_gas_router(db_path: str) -> APIRouter:
    router = APIRouter()

    @router.get("/gas")
    def get_gas_prices(zone: str = None):
        with get_db(db_path) as conn:
            query = "SELECT * FROM gas_stations ORDER BY regular_price ASC"
            params = []
            if zone:
                query = "SELECT * FROM gas_stations WHERE zone = ? ORDER BY regular_price ASC"
                params = [zone]
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    @router.get("/gas/history")
    def get_gas_history(station_id: int = None, limit: int = 30):
        with get_db(db_path) as conn:
            if station_id:
                rows = conn.execute(
                    "SELECT * FROM gas_price_history WHERE station_id = ? ORDER BY date DESC LIMIT ?",
                    (station_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM gas_price_history ORDER BY date DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [dict(row) for row in rows]

    return router
