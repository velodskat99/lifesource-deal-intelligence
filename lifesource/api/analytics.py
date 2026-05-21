"""Spending analytics and price history API."""
from fastapi import APIRouter, Query

from lifesource.db import get_db


def create_analytics_router(db_path: str) -> APIRouter:
    router = APIRouter()

    @router.get("/spending")
    def get_spending(
        months: int = Query(3, description="Number of months to analyze"),
    ):
        with get_db(db_path) as conn:
            # Total spending by store
            by_store = conn.execute(
                """SELECT store, SUM(price * quantity) as total, COUNT(*) as items
                   FROM purchase_history
                   WHERE purchase_date >= date('now', ?)
                   GROUP BY store ORDER BY total DESC""",
                (f"-{months} months",),
            ).fetchall()

            # Total spending by month
            by_month = conn.execute(
                """SELECT strftime('%Y-%m', purchase_date) as month,
                          SUM(price * quantity) as total, COUNT(*) as items
                   FROM purchase_history
                   WHERE purchase_date >= date('now', ?)
                   GROUP BY month ORDER BY month DESC""",
                (f"-{months} months",),
            ).fetchall()

            # Top items by spend
            top_items = conn.execute(
                """SELECT item_name, store, SUM(price * quantity) as total_spent,
                          COUNT(*) as times_bought, AVG(price) as avg_price
                   FROM purchase_history
                   WHERE purchase_date >= date('now', ?)
                   GROUP BY item_name ORDER BY total_spent DESC LIMIT 20""",
                (f"-{months} months",),
            ).fetchall()

            # Estimated savings (deals bought below regular price)
            total_spent = sum(r["total"] for r in by_store) if by_store else 0

        return {
            "period_months": months,
            "total_spent": round(total_spent, 2),
            "by_store": [dict(r) for r in by_store],
            "by_month": [dict(r) for r in by_month],
            "top_items": [dict(r) for r in top_items],
        }

    @router.get("/products/{product_id}/price-history")
    def get_price_history(product_id: int, limit: int = 90):
        with get_db(db_path) as conn:
            rows = conn.execute(
                """SELECT * FROM price_history
                   WHERE product_id = ?
                   ORDER BY date DESC LIMIT ?""",
                (product_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    return router
