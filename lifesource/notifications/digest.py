from datetime import date
from typing import Optional

from lifesource.models import Deal

STORE_DISPLAY = {
    "heb": "H-E-B",
    "costco": "Costco",
    "99ranch": "99 Ranch",
    "hmart": "H Mart",
    "traderjoes": "Trader Joe's",
}


def format_digest(
    deals: list[Deal],
    today: Optional[date] = None,
    max_deals: int = 10,
) -> str:
    """Format the daily digest message for Telegram."""
    today = today or date.today()
    date_str = today.strftime("%b %-d")

    lines = [f"--- LifeSource Daily Digest ({date_str}) ---", ""]

    if not deals:
        lines.append("No deals found today. Scrapers may have failed -- check logs.")
        return "\n".join(lines)

    lines.append("TOP DEALS FOR YOU:")
    for i, deal in enumerate(deals[:max_deals], 1):
        store_display = STORE_DISPLAY.get(deal.store, deal.store)
        price_str = f"${deal.sale_price:.2f}"

        if deal.regular_price and deal.regular_price > 0:
            pct = int(deal.discount_pct * 100)
            lines.append(
                f"{i}. {deal.item_name} -- {price_str} at {store_display} "
                f"(usually ${deal.regular_price:.2f}, save {pct}%)"
            )
        else:
            lines.append(f"{i}. {deal.item_name} -- {price_str} at {store_display}")

    return "\n".join(lines)
