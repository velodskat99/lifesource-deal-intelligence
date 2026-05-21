from datetime import date
from typing import Optional

from lifesource.models import Deal, UserPreference


def score_deal(
    deal: Deal,
    user_pref: Optional[UserPreference],
    today: Optional[date] = None,
) -> float:
    """Score a single deal (0-100) based on savings and purchase history."""
    today = today or date.today()

    # --- Purchase Score (0-40) ---
    purchase_score = 0.0
    if user_pref and user_pref.total_purchases > 0:
        base = min(user_pref.total_purchases / 10.0, 1.0) * 40.0

        timing_factor = 1.0
        if (
            user_pref.last_purchased
            and user_pref.avg_purchase_frequency_days
            and user_pref.avg_purchase_frequency_days > 0
        ):
            days_until_restock = (
                (user_pref.last_purchased.toordinal()
                 + int(user_pref.avg_purchase_frequency_days))
                - today.toordinal()
            )
            timing_factor = 1.0 - (
                days_until_restock / user_pref.avg_purchase_frequency_days
            )
            timing_factor = max(0.5, min(1.5, timing_factor))

        purchase_score = min(base * timing_factor, 40.0)

    # --- Savings Score (0-50) ---
    savings_score = 0.0
    if deal.regular_price and deal.regular_price > 0:
        discount_pct = (deal.regular_price - deal.sale_price) / deal.regular_price
        pct_score = discount_pct * 40.0

        dollar_savings = deal.regular_price - deal.sale_price
        dollar_score = min(dollar_savings / 5.0, 1.0) * 10.0

        savings_score = min(pct_score + dollar_score, 50.0)

    # --- Store Bonus (0-10) ---
    store_bonus = 0.0
    if user_pref:
        if user_pref.preferred_store == deal.store:
            store_bonus = 10.0

    return purchase_score + savings_score + store_bonus


def score_deals(
    deals: list[Deal],
    user_prefs: dict[int, UserPreference],
    today: Optional[date] = None,
) -> list[Deal]:
    """Score and sort a list of deals by relevance. Returns new list."""
    scored = []
    for deal in deals:
        pref = user_prefs.get(deal.product_id) if deal.product_id else None
        deal_copy = deal.model_copy()
        deal_copy.score = score_deal(deal_copy, pref, today)
        scored.append(deal_copy)

    scored.sort(key=lambda d: d.score or 0, reverse=True)
    return scored
