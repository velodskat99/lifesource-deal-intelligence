import pytest
from datetime import date


def test_score_deal_high_savings():
    from lifesource.scoring.engine import score_deal
    from lifesource.models import Deal

    deal = Deal(
        store="heb",
        item_name="Large Eggs 18ct",
        regular_price=3.49,
        sale_price=1.99,
        source_type="scraper",
    )
    score = score_deal(deal, user_pref=None)
    # savings_score: discount_pct=0.43 -> 17.2 pts, dollar_savings=$1.50 -> 3 pts = 20.2
    assert score == pytest.approx(20.2, abs=0.5)


def test_score_deal_no_regular_price():
    from lifesource.scoring.engine import score_deal
    from lifesource.models import Deal

    deal = Deal(
        store="heb",
        item_name="Mystery Item",
        sale_price=5.99,
        source_type="scraper",
    )
    score = score_deal(deal, user_pref=None)
    assert score == 0.0


def test_score_deal_with_purchase_history():
    from lifesource.scoring.engine import score_deal
    from lifesource.models import Deal, UserPreference

    deal = Deal(
        store="heb",
        item_name="Large Eggs 18ct",
        regular_price=3.49,
        sale_price=1.99,
        source_type="scraper",
    )
    pref = UserPreference(
        product_id=1,
        total_purchases=15,
        avg_purchase_frequency_days=10,
        last_purchased=date(2026, 3, 30),  # 9 days ago from Apr 8
        preferred_store="heb",
        avg_price_paid=3.00,
    )
    score = score_deal(deal, user_pref=pref, today=date(2026, 4, 8))
    # purchase_score: base=40, timing=1.1 -> capped at 40
    # savings_score: ~20.2
    # store_bonus: +10
    # Actual: purchase_score(40*0.9=36) + savings(20.2) + store(10) = ~66.2
    assert score == pytest.approx(66.2, abs=1.0)


def test_score_deal_recently_purchased():
    from lifesource.scoring.engine import score_deal
    from lifesource.models import Deal, UserPreference

    deal = Deal(
        store="heb",
        item_name="Milk",
        regular_price=4.99,
        sale_price=3.99,
        source_type="scraper",
    )
    pref = UserPreference(
        product_id=2,
        total_purchases=5,
        avg_purchase_frequency_days=7,
        last_purchased=date(2026, 4, 7),  # yesterday
        preferred_store="heb",
        avg_price_paid=4.50,
    )
    score = score_deal(deal, user_pref=pref, today=date(2026, 4, 8))
    # purchase_score: base=20, timing~0.5 -> ~10
    # savings_score: ~10
    # store_bonus: +10
    assert score == pytest.approx(30.0, abs=2.0)


def test_score_deals_returns_sorted_list():
    from lifesource.scoring.engine import score_deals
    from lifesource.models import Deal

    deals = [
        Deal(store="heb", item_name="A", regular_price=10.0, sale_price=9.50,
             source_type="scraper"),
        Deal(store="heb", item_name="B", regular_price=10.0, sale_price=5.00,
             source_type="scraper"),
        Deal(store="heb", item_name="C", regular_price=10.0, sale_price=2.00,
             source_type="scraper"),
    ]
    scored = score_deals(deals, user_prefs={})
    scores = [d.score for d in scored]
    assert scores == sorted(scores, reverse=True)
