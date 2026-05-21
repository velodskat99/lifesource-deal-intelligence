from datetime import date

import pytest


def test_deal_model_valid():
    from lifesource.models import Deal

    deal = Deal(
        store="heb",
        item_name="Large Eggs 18ct",
        category="dairy",
        regular_price=3.49,
        sale_price=1.99,
        unit="each",
        start_date=date(2026, 4, 6),
        end_date=date(2026, 4, 12),
        source_type="scraper",
    )
    assert deal.store == "heb"
    assert deal.discount_pct == pytest.approx(0.4298, rel=1e-2)


def test_deal_model_no_regular_price():
    from lifesource.models import Deal

    deal = Deal(store="heb", item_name="Mystery Item", sale_price=5.99, source_type="scraper")
    assert deal.discount_pct == 0.0


def test_purchase_model_valid():
    from lifesource.models import Purchase

    purchase = Purchase(
        store="heb",
        item_name="Large Eggs 18ct",
        price=2.49,
        quantity=1,
        unit="each",
        purchase_date=date(2026, 4, 1),
        source="manual",
    )
    assert purchase.store == "heb"
    assert purchase.price == 2.49


def test_product_model_valid():
    from lifesource.models import Product

    product = Product(name="Large Eggs 18ct", category="dairy", aliases=["eggs 18ct", "lg eggs"])
    assert product.name == "Large Eggs 18ct"
    assert len(product.aliases) == 2
