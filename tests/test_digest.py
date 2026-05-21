from datetime import date


def test_format_digest_with_deals():
    from lifesource.notifications.digest import format_digest
    from lifesource.models import Deal

    deals = [
        Deal(
            store="heb",
            item_name="Large Eggs 18ct",
            regular_price=3.49,
            sale_price=1.99,
            source_type="scraper",
            score=70.2,
        ),
        Deal(
            store="heb",
            item_name="Whole Milk 1gal",
            regular_price=4.99,
            sale_price=3.49,
            source_type="scraper",
            score=45.0,
        ),
    ]
    result = format_digest(deals=deals, today=date(2026, 4, 8))

    assert "LifeSource Daily Digest" in result
    assert "Apr 8" in result
    assert "Large Eggs 18ct" in result
    assert "$1.99" in result
    assert "H-E-B" in result
    assert "42%" in result  # int(0.4298 * 100) = 42


def test_format_digest_empty_deals():
    from lifesource.notifications.digest import format_digest

    result = format_digest(deals=[], today=date(2026, 4, 8))
    assert "No deals found" in result


def test_format_digest_truncates_long_list():
    from lifesource.notifications.digest import format_digest
    from lifesource.models import Deal

    deals = [
        Deal(
            store="heb",
            item_name=f"Item {i}",
            regular_price=10.0,
            sale_price=5.0,
            source_type="scraper",
            score=50.0 - i,
        )
        for i in range(20)
    ]
    result = format_digest(deals=deals, today=date(2026, 4, 8), max_deals=10)
    assert "Item 0" in result
    assert "Item 9" in result
    assert "Item 10" not in result
