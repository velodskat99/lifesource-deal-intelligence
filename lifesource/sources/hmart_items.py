from typing import Protocol

from lifesource.scrapers.vision import download_image, parse_flyer_image
from lifesource.sources.hmart_weekly import HMART_TEXAS_WEEKLY_AD_URL
from lifesource.sources.status import get_hmart_texas_status
from lifesource.sources.weekly_items import WeeklyAdItem, list_weekly_ad_items, replace_weekly_ad_items


class WeeklyAdAssetExtractor(Protocol):
    def extract(self, asset_url: str) -> list[dict]:
        ...


class VisionWeeklyAdAssetExtractor:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def extract(self, asset_url: str) -> list[dict]:
        image_data = download_image(asset_url)
        return parse_flyer_image(image_data, self.api_key)


def extract_hmart_texas_items(
    db_path: str,
    *,
    extractor: WeeklyAdAssetExtractor | None = None,
) -> dict:
    """Extract H Mart Texas weekly-ad assets into pending review item rows."""
    status = get_hmart_texas_status(db_path)
    assets = status.get("assets", [])
    if not assets:
        return {
            "status": "skipped",
            "reason": "no_weekly_ad_assets",
            "item_count": status.get("item_count", 0),
            "skipped_count": 0,
            "assets_processed": 0,
            "items": list_weekly_ad_items(db_path, store="hmart", region="texas"),
        }
    if extractor is None:
        return {
            "status": "skipped",
            "reason": "extractor_not_configured",
            "item_count": status.get("item_count", 0),
            "skipped_count": 0,
            "assets_processed": 0,
            "items": list_weekly_ad_items(db_path, store="hmart", region="texas"),
        }

    items: list[WeeklyAdItem] = []
    skipped_count = 0
    for asset_url in assets:
        extracted_rows = extractor.extract(asset_url)
        for row in extracted_rows:
            weekly_item = _coerce_weekly_item(row, asset_url=asset_url)
            if weekly_item is None:
                skipped_count += 1
                continue
            items.append(weekly_item)

    replace_weekly_ad_items(db_path, store="hmart", region="texas", items=items)
    saved_items = list_weekly_ad_items(db_path, store="hmart", region="texas")
    if skipped_count and saved_items:
        status_label = "partial"
    elif saved_items:
        status_label = "success"
    else:
        status_label = "empty"
    return {
        "status": status_label,
        "item_count": len(saved_items),
        "skipped_count": skipped_count,
        "assets_processed": len(assets),
        "items": saved_items,
    }


def _coerce_weekly_item(row: dict, *, asset_url: str) -> WeeklyAdItem | None:
    item_name = str(row.get("item_name") or "").strip()
    if not item_name:
        return None
    try:
        sale_price = float(row["sale_price"])
    except (KeyError, TypeError, ValueError):
        return None

    return WeeklyAdItem(
        store="hmart",
        region="texas",
        source_url=HMART_TEXAS_WEEKLY_AD_URL,
        asset_url=asset_url,
        item_name=item_name,
        category=_optional_str(row.get("category")),
        regular_price=_optional_float(row.get("regular_price")),
        sale_price=sale_price,
        unit=_optional_str(row.get("unit")),
        start_date=_optional_str(row.get("start_date")),
        end_date=_optional_str(row.get("end_date")),
        confidence=_optional_float(row.get("confidence")),
        raw_text=_optional_str(row.get("raw_text")),
    )


def _optional_str(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
