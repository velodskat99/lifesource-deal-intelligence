"""Shopping plan generator.

Analyzes current deals and purchase history to generate an optimized
weekly shopping plan: which items to buy at which stores.
"""
import logging
from datetime import date, timedelta
from typing import Optional

from lifesource.db import get_db

logger = logging.getLogger(__name__)

STORE_DISPLAY = {
    "heb": "H-E-B",
    "costco": "Costco",
    "99ranch": "99 Ranch",
    "hmart": "H Mart",
}


def generate_shopping_plan(db_path: str, today: Optional[date] = None) -> dict:
    """Generate a weekly shopping plan based on current deals and buying patterns.

    Returns:
        {
            "date": "2026-04-08",
            "stores": {
                "heb": {"deals": [...], "est_savings": 8.40},
                "99ranch": {"deals": [...], "est_savings": 6.50},
            },
            "skip_stores": ["costco", "hmart"],
            "total_savings": 14.90,
            "restock_items": [...],
        }
    """
    today = today or date.today()

    with get_db(db_path) as conn:
        # Get active deals (not expired)
        today_str = today.isoformat()
        rows = conn.execute(
            """SELECT * FROM deals
               WHERE (end_date IS NULL OR end_date >= ?)
               ORDER BY sale_price ASC""",
            (today_str,),
        ).fetchall()
        deals = [dict(r) for r in rows]

        # Get user preferences for restock prediction
        prefs = conn.execute("SELECT * FROM user_preferences").fetchall()

        # Find items due for restock
        restock_items = []
        for pref in prefs:
            if pref["last_purchased"] and pref["avg_purchase_frequency_days"]:
                last = date.fromisoformat(pref["last_purchased"])
                freq = int(pref["avg_purchase_frequency_days"])
                next_buy = last + timedelta(days=freq)
                if next_buy <= today + timedelta(days=7):
                    product = conn.execute(
                        "SELECT name FROM products WHERE id = ?", (pref["product_id"],)
                    ).fetchone()
                    if product:
                        restock_items.append({
                            "product_id": pref["product_id"],
                            "name": product["name"],
                            "days_overdue": (today - next_buy).days,
                            "preferred_store": pref["preferred_store"],
                        })

    # Group deals by store and calculate savings
    stores = {}
    for deal in deals:
        store = deal["store"]
        if store not in stores:
            stores[store] = {"deals": [], "est_savings": 0.0}

        savings = 0.0
        if deal.get("regular_price") and deal.get("sale_price"):
            savings = deal["regular_price"] - deal["sale_price"]

        stores[store]["deals"].append({
            "item_name": deal["item_name"],
            "sale_price": deal["sale_price"],
            "regular_price": deal.get("regular_price"),
            "savings": savings,
            "category": deal.get("category"),
        })
        stores[store]["est_savings"] += savings

    # Determine which stores to visit vs skip
    active_stores = {s: v for s, v in stores.items() if v["deals"]}
    all_stores = {"heb", "costco", "99ranch", "hmart"}
    skip_stores = list(all_stores - set(active_stores.keys()))

    # Sort deals within each store by savings (best deals first)
    for store_data in active_stores.values():
        store_data["deals"].sort(key=lambda d: d["savings"], reverse=True)
        store_data["est_savings"] = round(store_data["est_savings"], 2)

    total_savings = sum(s["est_savings"] for s in active_stores.values())

    return {
        "date": today.isoformat(),
        "stores": active_stores,
        "skip_stores": skip_stores,
        "total_savings": round(total_savings, 2),
        "restock_items": restock_items,
    }
