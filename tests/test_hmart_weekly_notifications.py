from datetime import date

from lifesource.models import Deal
from lifesource.notifications.hmart_weekly import (
    format_hmart_refresh_alert,
    format_hmart_weekly_planning_digest,
)
from lifesource.sources.hmart_weekly import HMART_TEXAS_WEEKLY_AD_URL


def test_format_hmart_refresh_alert_includes_highlights_and_source():
    deals = [
        Deal(
            store="hmart",
            item_name="Pork Belly",
            category="meat",
            regular_price=8.99,
            sale_price=5.99,
            unit="lb",
            source_url=HMART_TEXAS_WEEKLY_AD_URL,
            source_type="weekly_ad",
            confidence=0.95,
        )
    ]

    message = format_hmart_refresh_alert(
        source_url=HMART_TEXAS_WEEKLY_AD_URL,
        deals=deals,
        warnings=[],
        today=date(2026, 5, 21),
    )

    assert "H Mart Texas weekly ad refreshed" in message
    assert HMART_TEXAS_WEEKLY_AD_URL in message
    assert "Pork Belly" in message
    assert "$5.99/lb" in message
    assert "Meal plan angle" in message


def test_format_hmart_refresh_alert_with_no_deals_asks_for_review():
    message = format_hmart_refresh_alert(
        source_url=HMART_TEXAS_WEEKLY_AD_URL,
        deals=[],
        warnings=["No weekly-ad assets found; fingerprint uses raw HTML."],
        today=date(2026, 5, 21),
    )

    assert "H Mart Texas weekly ad refreshed" in message
    assert "No parsed weekly-ad items yet" in message
    assert "No weekly-ad assets found" in message
    assert "catalog" not in message.lower()


def test_format_hmart_weekly_planning_digest_sends_even_without_deals():
    message = format_hmart_weekly_planning_digest(
        source_url=HMART_TEXAS_WEEKLY_AD_URL,
        deals=[],
        changed=False,
        today=date(2026, 5, 21),
    )

    assert "H Mart Texas weekly planning" in message
    assert "No parsed weekly-ad deals are stored yet" in message
    assert HMART_TEXAS_WEEKLY_AD_URL in message
