from dataclasses import dataclass
from typing import Any

from lifesource.db import get_db, init_db


@dataclass(frozen=True)
class WeeklyAdItem:
    store: str
    region: str
    source_url: str
    item_name: str
    sale_price: float
    asset_url: str | None = None
    category: str | None = None
    regular_price: float | None = None
    unit: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    confidence: float | None = None
    status: str = "pending_review"
    raw_text: str | None = None


def replace_weekly_ad_items(
    db_path: str,
    *,
    store: str,
    region: str,
    items: list[WeeklyAdItem],
) -> None:
    """Replace extracted weekly-ad rows for one store and region."""
    init_db(db_path)
    with get_db(db_path) as conn:
        conn.execute(
            "DELETE FROM weekly_ad_items WHERE store = ? AND region = ?",
            (store, region),
        )
        conn.executemany(
            """INSERT INTO weekly_ad_items (
                   store, region, source_url, asset_url, item_name, category,
                   regular_price, sale_price, unit, start_date, end_date,
                   confidence, status, raw_text
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    item.store,
                    item.region,
                    item.source_url,
                    item.asset_url,
                    item.item_name,
                    item.category,
                    item.regular_price,
                    item.sale_price,
                    item.unit,
                    item.start_date,
                    item.end_date,
                    item.confidence,
                    item.status,
                    item.raw_text,
                )
                for item in items
            ],
        )
        conn.commit()


def list_weekly_ad_items(
    db_path: str,
    *,
    store: str,
    region: str,
) -> list[dict[str, Any]]:
    """List extracted weekly-ad rows for one store and region."""
    init_db(db_path)
    with get_db(db_path) as conn:
        rows = conn.execute(
            """SELECT * FROM weekly_ad_items
               WHERE store = ? AND region = ?
               ORDER BY id ASC""",
            (store, region),
        ).fetchall()
    return [dict(row) for row in rows]


def count_weekly_ad_items(db_path: str, *, store: str, region: str) -> int:
    init_db(db_path)
    with get_db(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS item_count FROM weekly_ad_items WHERE store = ? AND region = ?",
            (store, region),
        ).fetchone()
    return int(row["item_count"]) if row else 0
