from datetime import date

from lifesource.models import Deal


def format_hmart_refresh_alert(
    *,
    source_url: str,
    deals: list[Deal],
    warnings: list[str],
    today: date | None = None,
    max_deals: int = 8,
) -> str:
    today = today or date.today()
    lines = [
        "H Mart Texas weekly ad refreshed",
        today.isoformat(),
        "",
        f"Source: {source_url}",
        "",
    ]

    weekly_deals = _weekly_ad_deals(deals)
    if weekly_deals:
        lines.append("Highlights:")
        lines.extend(_format_deal_lines(weekly_deals[:max_deals]))
        lines.extend(["", _meal_plan_angle(weekly_deals)])
    else:
        lines.append("No parsed weekly-ad items yet. Review the source page before planning a trip.")

    if warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in warnings)

    return "\n".join(lines)


def format_hmart_weekly_planning_digest(
    *,
    source_url: str,
    deals: list[Deal],
    changed: bool,
    today: date | None = None,
    max_deals: int = 10,
) -> str:
    today = today or date.today()
    status = "refreshed this cycle" if changed else "no refresh detected"
    lines = [
        "H Mart Texas weekly planning",
        today.isoformat(),
        f"Status: {status}",
        "",
        f"Source: {source_url}",
        "",
    ]

    weekly_deals = _weekly_ad_deals(deals)
    if not weekly_deals:
        lines.extend([
            "No parsed weekly-ad deals are stored yet.",
            "Use the source page as the planning fallback for this week.",
        ])
        return "\n".join(lines)

    lines.append("Plan around:")
    lines.extend(_format_deal_lines(weekly_deals[:max_deals]))
    lines.extend(["", _meal_plan_angle(weekly_deals)])
    return "\n".join(lines)


def _weekly_ad_deals(deals: list[Deal]) -> list[Deal]:
    return [deal for deal in deals if deal.source_type == "weekly_ad"]


def _format_deal_lines(deals: list[Deal]) -> list[str]:
    return [f"- {deal.item_name}: {_price(deal)}" for deal in deals]


def _price(deal: Deal) -> str:
    unit = f"/{deal.unit}" if deal.unit else ""
    return f"${deal.sale_price:.2f}{unit}"


def _meal_plan_angle(deals: list[Deal]) -> str:
    categories = {deal.category for deal in deals if deal.category}
    if "meat" in categories or "seafood" in categories:
        return "Meal plan angle: choose one protein anchor, then add produce and pantry staples."
    if "produce" in categories:
        return "Meal plan angle: build simple bowls, stir-fries, or side dishes around the produce."
    return "Meal plan angle: use these as shopping-list candidates, then confirm meals after review."
