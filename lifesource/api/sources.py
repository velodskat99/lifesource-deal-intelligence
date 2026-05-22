from fastapi import APIRouter
from pydantic import BaseModel

from lifesource.sources.hmart_weekly import HmartTexasWeeklyAdSource
from lifesource.sources.status import get_hmart_texas_status, record_hmart_texas_inspection
from lifesource.sources.weekly_items import WeeklyAdItem, list_weekly_ad_items, replace_weekly_ad_items


class WeeklyAdItemPayload(BaseModel):
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


class WeeklyAdItemsPayload(BaseModel):
    items: list[WeeklyAdItemPayload]


def create_sources_router(db_path: str) -> APIRouter:
    router = APIRouter()

    @router.get("/sources/hmart-texas/status")
    def hmart_texas_status():
        return get_hmart_texas_status(db_path)

    @router.get("/sources/hmart-texas/items")
    def hmart_texas_items():
        items = list_weekly_ad_items(db_path, store="hmart", region="texas")
        return {
            "store": "hmart",
            "region": "texas",
            "item_count": len(items),
            "items": items,
        }

    @router.post("/sources/hmart-texas/items")
    def replace_hmart_texas_items(payload: WeeklyAdItemsPayload):
        replace_weekly_ad_items(
            db_path,
            store="hmart",
            region="texas",
            items=[
                WeeklyAdItem(
                    store="hmart",
                    region="texas",
                    source_url=item.source_url,
                    asset_url=item.asset_url,
                    item_name=item.item_name,
                    category=item.category,
                    regular_price=item.regular_price,
                    sale_price=item.sale_price,
                    unit=item.unit,
                    start_date=item.start_date,
                    end_date=item.end_date,
                    confidence=item.confidence,
                    status=item.status,
                    raw_text=item.raw_text,
                )
                for item in payload.items
            ],
        )
        items = list_weekly_ad_items(db_path, store="hmart", region="texas")
        return {
            "store": "hmart",
            "region": "texas",
            "item_count": len(items),
            "items": items,
        }

    @router.post("/sources/hmart-texas/check")
    def check_hmart_texas():
        inspection = HmartTexasWeeklyAdSource().check()
        return record_hmart_texas_inspection(db_path, inspection)

    return router
