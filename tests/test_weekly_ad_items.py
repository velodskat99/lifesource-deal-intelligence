from lifesource.sources.weekly_items import (
    WeeklyAdItem,
    list_weekly_ad_items,
    replace_weekly_ad_items,
)


def test_replace_weekly_ad_items_stores_reviewable_rows(tmp_db):
    items = [
        WeeklyAdItem(
            store="hmart",
            region="texas",
            source_url="https://www.hmart.com/weekly-ads-texas#/",
            asset_url="https://cdn.hmart.com/weekly-ad-page-1.jpg",
            item_name="Korean Pear",
            category="produce",
            regular_price=3.99,
            sale_price=2.49,
            unit="lb",
            start_date="2026-05-24",
            end_date="2026-05-30",
            confidence=0.82,
            raw_text="Korean Pear $2.49/lb",
        )
    ]

    replace_weekly_ad_items(tmp_db, store="hmart", region="texas", items=items)

    rows = list_weekly_ad_items(tmp_db, store="hmart", region="texas")
    assert len(rows) == 1
    assert rows[0]["item_name"] == "Korean Pear"
    assert rows[0]["sale_price"] == 2.49
    assert rows[0]["status"] == "pending_review"
    assert rows[0]["asset_url"] == "https://cdn.hmart.com/weekly-ad-page-1.jpg"


def test_replace_weekly_ad_items_replaces_only_matching_store_region(tmp_db):
    replace_weekly_ad_items(
        tmp_db,
        store="hmart",
        region="texas",
        items=[
            WeeklyAdItem(
                store="hmart",
                region="texas",
                source_url="https://www.hmart.com/weekly-ads-texas#/",
                item_name="Old Rice",
                sale_price=12.99,
            )
        ],
    )
    replace_weekly_ad_items(
        tmp_db,
        store="hmart",
        region="california",
        items=[
            WeeklyAdItem(
                store="hmart",
                region="california",
                source_url="https://www.hmart.com/weekly-ads-california#/",
                item_name="California Apple",
                sale_price=1.49,
            )
        ],
    )

    replace_weekly_ad_items(
        tmp_db,
        store="hmart",
        region="texas",
        items=[
            WeeklyAdItem(
                store="hmart",
                region="texas",
                source_url="https://www.hmart.com/weekly-ads-texas#/",
                item_name="Fresh Rice",
                sale_price=10.99,
            )
        ],
    )

    texas_rows = list_weekly_ad_items(tmp_db, store="hmart", region="texas")
    california_rows = list_weekly_ad_items(tmp_db, store="hmart", region="california")
    assert [row["item_name"] for row in texas_rows] == ["Fresh Rice"]
    assert [row["item_name"] for row in california_rows] == ["California Apple"]
