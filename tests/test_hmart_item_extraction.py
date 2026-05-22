from lifesource.db import init_db
from lifesource.sources.hmart_weekly import HMART_TEXAS_WEEKLY_AD_URL
from lifesource.sources.hmart_items import extract_hmart_texas_items
from lifesource.sources.snapshots import SourceSnapshot, record_source_snapshot
from lifesource.sources.weekly_items import WeeklyAdItem, list_weekly_ad_items, replace_weekly_ad_items


class FakeExtractor:
    def __init__(self, items_by_asset):
        self.items_by_asset = items_by_asset
        self.seen_assets = []

    def extract(self, asset_url: str):
        self.seen_assets.append(asset_url)
        return self.items_by_asset.get(asset_url, [])


def test_extract_hmart_texas_items_writes_pending_review_rows(tmp_db):
    init_db(tmp_db)
    asset_url = "https://cdn.hmart.com/weekly-ads/texas/page-1.jpg"
    record_source_snapshot(
        tmp_db,
        SourceSnapshot(
            store="hmart",
            region="texas",
            source_url=HMART_TEXAS_WEEKLY_AD_URL,
            source_type="weekly_ad",
            fingerprint="abc123",
            raw_metadata={"assets": [asset_url], "strategy": "weekly_ad_assets"},
        ),
    )
    extractor = FakeExtractor(
        {
            asset_url: [
                {
                    "item_name": "Short Rib",
                    "category": "meat",
                    "regular_price": 12.99,
                    "sale_price": "8.99",
                    "unit": "lb",
                    "confidence": 0.91,
                    "raw_text": "Short Rib $8.99/lb",
                }
            ]
        }
    )

    result = extract_hmart_texas_items(tmp_db, extractor=extractor)

    rows = list_weekly_ad_items(tmp_db, store="hmart", region="texas")
    assert result["status"] == "success"
    assert result["item_count"] == 1
    assert extractor.seen_assets == [asset_url]
    assert rows[0]["item_name"] == "Short Rib"
    assert rows[0]["sale_price"] == 8.99
    assert rows[0]["status"] == "pending_review"
    assert rows[0]["asset_url"] == asset_url


def test_extract_hmart_texas_items_skips_malformed_rows(tmp_db):
    init_db(tmp_db)
    asset_url = "https://cdn.hmart.com/weekly-ads/texas/page-1.jpg"
    record_source_snapshot(
        tmp_db,
        SourceSnapshot(
            store="hmart",
            region="texas",
            source_url=HMART_TEXAS_WEEKLY_AD_URL,
            source_type="weekly_ad",
            fingerprint="abc123",
            raw_metadata={"assets": [asset_url], "strategy": "weekly_ad_assets"},
        ),
    )
    extractor = FakeExtractor(
        {
            asset_url: [
                {"item_name": "Unreadable Price", "sale_price": "not a price"},
                {"sale_price": 3.99},
                {"item_name": "Napa Cabbage", "sale_price": 0.99},
            ]
        }
    )

    result = extract_hmart_texas_items(tmp_db, extractor=extractor)

    rows = list_weekly_ad_items(tmp_db, store="hmart", region="texas")
    assert result["status"] == "partial"
    assert result["item_count"] == 1
    assert result["skipped_count"] == 2
    assert [row["item_name"] for row in rows] == ["Napa Cabbage"]


def test_extract_hmart_texas_items_preserves_existing_rows_when_no_assets(tmp_db):
    replace_weekly_ad_items(
        tmp_db,
        store="hmart",
        region="texas",
        items=[
            WeeklyAdItem(
                store="hmart",
                region="texas",
                source_url=HMART_TEXAS_WEEKLY_AD_URL,
                item_name="Existing Item",
                sale_price=1.99,
            )
        ],
    )

    result = extract_hmart_texas_items(tmp_db, extractor=FakeExtractor({}))

    rows = list_weekly_ad_items(tmp_db, store="hmart", region="texas")
    assert result["status"] == "skipped"
    assert result["reason"] == "no_weekly_ad_assets"
    assert [row["item_name"] for row in rows] == ["Existing Item"]
