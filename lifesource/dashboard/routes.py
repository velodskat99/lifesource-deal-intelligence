from fastapi import APIRouter, Request, Query, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional

from lifesource.db import get_db
from lifesource.sources.hmart_weekly import HmartTexasWeeklyAdSource
from lifesource.sources.status import get_hmart_texas_status, record_hmart_texas_inspection
from lifesource.sources.weekly_items import list_weekly_ad_items

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _render(name: str, request: Request, **ctx):
    """Render a template with Starlette 1.0 compatible API."""
    return templates.TemplateResponse(request=request, name=name, context=ctx)


def create_dashboard_router(db_path: str) -> APIRouter:
    router = APIRouter()

    @router.get("/")
    def deal_feed(request: Request):
        with get_db(db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM deals ORDER BY created_at DESC LIMIT 200"
            ).fetchall()
            deals = [dict(row) for row in rows]

            # Get purchase history for similarity scoring
            purchases = conn.execute(
                """SELECT LOWER(item_name) as name, COUNT(*) as freq
                   FROM purchase_history GROUP BY LOWER(item_name)"""
            ).fetchall()
            purchase_map = {p["name"]: p["freq"] for p in purchases}

        # Score deals by purchase history similarity
        for deal in deals:
            deal_name = deal["item_name"].lower()
            score = 0
            match_reason = None

            # Exact match
            if deal_name in purchase_map:
                score = 100 + purchase_map[deal_name]
                match_reason = f"You buy this ({purchase_map[deal_name]}x)"
            else:
                # Token overlap with purchase history
                deal_tokens = set(deal_name.split())
                best_overlap = 0
                best_match = None
                for pname, freq in purchase_map.items():
                    ptokens = set(pname.split())
                    overlap = len(deal_tokens & ptokens)
                    if overlap > best_overlap and overlap >= 1:
                        best_overlap = overlap
                        best_match = pname
                        score = overlap * 20 + freq
                if best_match and best_overlap >= 1:
                    match_reason = f"Similar to {best_match.title()} you buy"

            # Bonus for having a discount
            if deal.get("regular_price") and deal["regular_price"] > 0:
                discount = (deal["regular_price"] - deal["sale_price"]) / deal["regular_price"]
                score += int(discount * 30)

            deal["_score"] = score
            deal["match_reason"] = match_reason

        deals.sort(key=lambda d: d["_score"], reverse=True)

        # Group by category, ordered: meat, produce, seafood, dairy, frozen, pantry, beverages, bakery, household, other
        CATEGORY_ORDER = ["meat", "produce", "seafood", "dairy", "frozen", "pantry", "beverages", "bakery", "household", "other"]
        CATEGORY_LABELS = {
            "meat": "Meat",
            "produce": "Produce & Fruits",
            "seafood": "Seafood",
            "dairy": "Dairy & Eggs",
            "frozen": "Frozen",
            "pantry": "Pantry & Snacks",
            "beverages": "Beverages",
            "bakery": "Bakery",
            "household": "Household",
            "other": "Other",
        }
        CATEGORY_EMOJI = {
            "meat": "🥩", "produce": "🥬", "seafood": "🐟", "dairy": "🥛",
            "frozen": "🧊", "pantry": "🥫", "beverages": "🥤", "bakery": "🍞",
            "household": "🧹", "other": "🛒",
        }
        grouped = {}
        for deal in deals:
            cat = deal.get("category") or "other"
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(deal)

        categories = []
        for cat in CATEGORY_ORDER:
            if cat in grouped:
                categories.append({
                    "key": cat,
                    "label": CATEGORY_LABELS.get(cat, cat),
                    "emoji": CATEGORY_EMOJI.get(cat, "🛒"),
                    "deals": grouped[cat],
                    "count": len(grouped[cat]),
                })

        return _render("deals.html", request, deals=deals, categories=categories)

    @router.get("/partials/deals")
    def deal_list_partial(
        request: Request,
        store: Optional[str] = Query(None),
        q: Optional[str] = Query(None),
    ):
        with get_db(db_path) as conn:
            query = "SELECT * FROM deals WHERE 1=1"
            params = []

            if store:
                query += " AND store = ?"
                params.append(store)
            if q:
                query += " AND item_name LIKE ?"
                params.append(f"%{q}%")

            query += " ORDER BY created_at DESC LIMIT 100"
            rows = conn.execute(query, params).fetchall()
            deals = [dict(row) for row in rows]
        return _render("partials/deal_list.html", request, deals=deals)

    @router.get("/purchases")
    def purchase_log(request: Request):
        with get_db(db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM purchase_history ORDER BY purchase_date DESC LIMIT 100"
            ).fetchall()
            purchases = [dict(row) for row in rows]
        return _render("purchases.html", request, purchases=purchases)

    @router.post("/partials/purchases/create")
    def create_purchase_htmx(
        request: Request,
        store: str = Form(),
        item_name: str = Form(),
        price: float = Form(),
        quantity: float = Form(1),
        unit: str = Form(""),
        purchase_date: str = Form(),
        source: str = Form("manual"),
    ):
        with get_db(db_path) as conn:
            conn.execute(
                """INSERT INTO purchase_history (store, item_name, price, quantity, unit,
                   purchase_date, source) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (store, item_name, price, quantity, unit or None, purchase_date, source),
            )
            conn.commit()
            rows = conn.execute(
                "SELECT * FROM purchase_history ORDER BY purchase_date DESC LIMIT 100"
            ).fetchall()
            purchases = [dict(row) for row in rows]
        return _render("partials/purchase_list.html", request, purchases=purchases)

    @router.get("/gas")
    def gas_prices(request: Request):
        with get_db(db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM gas_stations ORDER BY regular_price ASC"
            ).fetchall()
            stations = [dict(row) for row in rows]
            avg_price = (
                sum(s["regular_price"] for s in stations) / len(stations)
                if stations else 0
            )
        return _render("gas.html", request, stations=stations, avg_price=avg_price)

    @router.get("/watchlist")
    def watchlist_page(request: Request):
        with get_db(db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM watchlist WHERE active = TRUE ORDER BY created_at DESC"
            ).fetchall()
            items = [dict(row) for row in rows]
        return _render("watchlist.html", request, items=items)

    @router.get("/spending")
    def spending_page(request: Request):
        with get_db(db_path) as conn:
            by_store = conn.execute(
                """SELECT store, SUM(price * quantity) as total, COUNT(*) as items
                   FROM purchase_history WHERE purchase_date >= date('now', '-3 months')
                   GROUP BY store ORDER BY total DESC"""
            ).fetchall()
            by_month = conn.execute(
                """SELECT strftime('%Y-%m', purchase_date) as month,
                          SUM(price * quantity) as total, COUNT(*) as items
                   FROM purchase_history WHERE purchase_date >= date('now', '-3 months')
                   GROUP BY month ORDER BY month DESC"""
            ).fetchall()
            top_items = conn.execute(
                """SELECT item_name, store, SUM(price * quantity) as total_spent,
                          COUNT(*) as times_bought, AVG(price) as avg_price
                   FROM purchase_history WHERE purchase_date >= date('now', '-3 months')
                   GROUP BY item_name ORDER BY total_spent DESC LIMIT 20"""
            ).fetchall()
            total_spent = sum(r["total"] for r in by_store) if by_store else 0
        spending = {
            "period_months": 3,
            "total_spent": round(total_spent, 2),
            "by_store": [dict(r) for r in by_store],
            "by_month": [dict(r) for r in by_month],
            "top_items": [dict(r) for r in top_items],
        }
        return _render("spending.html", request, spending=spending)

    @router.get("/settings")
    def settings_page(request: Request):
        import json
        with get_db(db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            rows = conn.execute("SELECT * FROM settings").fetchall()
        settings = {}
        for row in rows:
            try:
                settings[row["key"]] = json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                settings[row["key"]] = row["value"]
        return _render("settings.html", request, settings=settings)

    @router.get("/sources")
    def sources_page(
        request: Request,
        checked: Optional[int] = Query(None),
        changed: Optional[int] = Query(None),
    ):
        check_result = None
        if checked is not None:
            check_result = {"changed": bool(changed)}
        return _render(
            "sources.html",
            request,
            hmart_status=get_hmart_texas_status(db_path),
            hmart_items=list_weekly_ad_items(db_path, store="hmart", region="texas"),
            check_result=check_result,
        )

    @router.post("/sources/hmart-texas/check")
    def check_hmart_texas_source(request: Request):
        inspection = HmartTexasWeeklyAdSource().check()
        result = record_hmart_texas_inspection(db_path, inspection)
        changed = 1 if result["changed"] else 0
        return RedirectResponse(f"/sources?checked=1&changed={changed}", status_code=303)

    @router.get("/plan")
    def shopping_plan(request: Request):
        from lifesource.scoring.planner import generate_shopping_plan
        plan = generate_shopping_plan(db_path)
        return _render("plan.html", request, plan=plan)

    @router.get("/list")
    def shopping_list(request: Request):
        with get_db(db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM shopping_list ORDER BY checked ASC, created_at DESC"
            ).fetchall()
            items = [dict(row) for row in rows]
        return _render("list.html", request, items=items)

    @router.get("/savings")
    def savings_page(request: Request):
        STORE_NAMES = {
            "heb": "H-E-B", "costco": "Costco",
            "99ranch": "99 Ranch", "hmart": "H Mart",
        }

        with get_db(db_path) as conn:
            # --- 1. Coupon savings (items bought below their regular price) ---
            coupon_savings = []
            total_coupon_savings = 0.0

            # --- 2. Cross-store price comparison ---
            cross_store_savings = []

            # Get items you buy and their avg price
            your_items = conn.execute("""
                SELECT LOWER(item_name) as name, item_name, store,
                       AVG(price) as avg_price, COUNT(*) as times
                FROM purchase_history
                GROUP BY LOWER(item_name)
                ORDER BY times DESC
            """).fetchall()

            for item in your_items:
                item_name = item["name"]
                your_price = item["avg_price"]
                tokens = item_name.split()

                # Search for similar deals at other stores
                alt_prices = []
                for token in tokens:
                    if len(token) < 3:
                        continue
                    deals = conn.execute("""
                        SELECT store, item_name, sale_price, regular_price
                        FROM deals
                        WHERE LOWER(item_name) LIKE ?
                        AND store != ?
                        ORDER BY sale_price ASC
                        LIMIT 5
                    """, (f"%{token}%", item["store"])).fetchall()

                    for d in deals:
                        store_name = STORE_NAMES.get(d["store"], d["store"])
                        alt_prices.append({
                            "store": d["store"],
                            "store_name": store_name,
                            "name": d["item_name"],
                            "price": d["sale_price"],
                        })

                # Deduplicate by store
                seen_stores = set()
                unique_alts = []
                for alt in alt_prices:
                    if alt["store"] not in seen_stores:
                        seen_stores.add(alt["store"])
                        unique_alts.append(alt)

                # Calculate savings vs alternatives
                max_alt_price = max([a["price"] for a in unique_alts], default=0)
                saved = max(0, max_alt_price - your_price) * item["times"] if unique_alts else 0

                if unique_alts:
                    cross_store_savings.append({
                        "name": item["item_name"],
                        "store": item["store"],
                        "your_price": your_price,
                        "times": item["times"],
                        "alt_prices": unique_alts[:3],
                        "saved": round(saved, 2),
                    })

            cross_store_savings.sort(key=lambda x: x["saved"], reverse=True)

            # --- 3. Potential savings this week ---
            potential_savings = []

            for item in your_items:
                tokens = item["name"].split()
                for token in tokens:
                    if len(token) < 3:
                        continue
                    deals = conn.execute("""
                        SELECT store, item_name, sale_price
                        FROM deals
                        WHERE LOWER(item_name) LIKE ?
                        AND sale_price < ?
                        AND sale_price > 0
                        ORDER BY sale_price ASC
                        LIMIT 1
                    """, (f"%{token}%", item["avg_price"])).fetchall()

                    for d in deals:
                        potential_savings.append({
                            "deal_name": d["item_name"],
                            "store": d["store"],
                            "deal_price": d["sale_price"],
                            "your_avg": item["avg_price"],
                        })
                    if deals:
                        break

            # Deduplicate by deal name
            seen = set()
            unique_potential = []
            for p in potential_savings:
                if p["deal_name"] not in seen:
                    seen.add(p["deal_name"])
                    unique_potential.append(p)
            potential_savings = sorted(
                unique_potential,
                key=lambda x: x["your_avg"] - x["deal_price"],
                reverse=True,
            )[:15]

            # --- Totals ---
            total_spent = conn.execute(
                "SELECT SUM(price * quantity) as t FROM purchase_history"
            ).fetchone()["t"] or 0

            total_saved = total_coupon_savings + sum(
                s["saved"] for s in cross_store_savings
            )
            total_would_have = total_spent + total_saved
            savings_pct = int(
                total_saved / total_would_have * 100
            ) if total_would_have > 0 else 0

        return _render(
            "savings.html", request,
            total_saved=round(total_saved, 2),
            total_spent=round(total_spent, 2),
            total_would_have=round(total_would_have, 2),
            savings_pct=savings_pct,
            cross_store_savings=cross_store_savings[:20],
            coupon_savings=coupon_savings,
            total_coupon_savings=round(total_coupon_savings, 2),
            potential_savings=potential_savings,
        )

    return router
