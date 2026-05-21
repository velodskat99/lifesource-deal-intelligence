import asyncio
import argparse
from datetime import date
from typing import Awaitable, Callable

from lifesource.config import get_settings
from lifesource.db import get_db, init_db
from lifesource.models import Deal
from lifesource.notifications.hmart_weekly import (
    format_hmart_refresh_alert,
    format_hmart_weekly_planning_digest,
)
from lifesource.notifications.telegram import send_telegram_message
from lifesource.sources.hmart_weekly import HmartTexasWeeklyAdSource
from lifesource.sources.snapshots import SourceSnapshot, record_source_snapshot

TelegramSender = Callable[[str, str, str], Awaitable[None]]


def run_hmart_weekly_ad_monitor(
    *,
    db_path: str | None = None,
    source: HmartTexasWeeklyAdSource | None = None,
    sender: TelegramSender = send_telegram_message,
    telegram_bot_token: str | None = None,
    telegram_chat_id: str | None = None,
    today: date | None = None,
) -> dict:
    settings = None
    if db_path is None or telegram_bot_token is None or telegram_chat_id is None:
        settings = get_settings()
    db_path = db_path or settings.db_path
    token = telegram_bot_token or settings.telegram_bot_token
    chat_id = telegram_chat_id or settings.telegram_chat_id
    source = source or HmartTexasWeeklyAdSource()
    init_db(db_path)

    inspection = source.check()
    snapshot_result = record_source_snapshot(
        db_path,
        SourceSnapshot(
            store=source.store,
            region=source.region,
            source_url=inspection.source_url,
            source_type=source.source_type,
            fingerprint=inspection.fingerprint,
            raw_metadata={
                "assets": inspection.assets,
                **inspection.metadata,
            },
        ),
    )

    if not snapshot_result.changed:
        return {
            "changed": False,
            "sent": False,
            "fingerprint": snapshot_result.current_fingerprint,
        }

    deals = _load_hmart_weekly_deals(db_path)
    message = format_hmart_refresh_alert(
        source_url=inspection.source_url,
        deals=deals,
        warnings=inspection.warnings,
        today=today,
    )
    asyncio.run(sender(message, token, chat_id))
    return {
        "changed": True,
        "sent": True,
        "fingerprint": snapshot_result.current_fingerprint,
        "deals": len(deals),
    }


def run_hmart_weekly_planning_digest(
    *,
    db_path: str | None = None,
    source: HmartTexasWeeklyAdSource | None = None,
    sender: TelegramSender = send_telegram_message,
    telegram_bot_token: str | None = None,
    telegram_chat_id: str | None = None,
    today: date | None = None,
) -> dict:
    settings = None
    if db_path is None or telegram_bot_token is None or telegram_chat_id is None:
        settings = get_settings()
    db_path = db_path or settings.db_path
    token = telegram_bot_token or settings.telegram_bot_token
    chat_id = telegram_chat_id or settings.telegram_chat_id
    source = source or HmartTexasWeeklyAdSource()
    init_db(db_path)

    inspection = source.check()
    snapshot_result = record_source_snapshot(
        db_path,
        SourceSnapshot(
            store=source.store,
            region=source.region,
            source_url=inspection.source_url,
            source_type=source.source_type,
            fingerprint=inspection.fingerprint,
            raw_metadata={
                "assets": inspection.assets,
                **inspection.metadata,
            },
        ),
    )
    deals = _load_hmart_weekly_deals(db_path)
    message = format_hmart_weekly_planning_digest(
        source_url=inspection.source_url,
        deals=deals,
        changed=snapshot_result.changed,
        today=today,
    )
    asyncio.run(sender(message, token, chat_id))
    return {
        "changed": snapshot_result.changed,
        "sent": True,
        "fingerprint": snapshot_result.current_fingerprint,
        "deals": len(deals),
    }


def _load_hmart_weekly_deals(db_path: str) -> list[Deal]:
    with get_db(db_path) as conn:
        rows = conn.execute(
            """SELECT * FROM deals
               WHERE store = 'hmart' AND source_type = 'weekly_ad'
               ORDER BY confidence DESC, sale_price ASC
               LIMIT 25"""
        ).fetchall()

    return [
        Deal(
            id=row["id"],
            store=row["store"],
            item_name=row["item_name"],
            product_id=row["product_id"],
            category=row["category"],
            regular_price=row["regular_price"],
            sale_price=row["sale_price"],
            unit=row["unit"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            source_url=row["source_url"],
            source_type=row["source_type"],
            confidence=row["confidence"],
            image_url=row["image_url"],
        )
        for row in rows
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run H Mart Texas weekly-ad jobs.")
    parser.add_argument("job", choices=["monitor", "digest"])
    args = parser.parse_args(argv)

    if args.job == "monitor":
        result = run_hmart_weekly_ad_monitor()
    else:
        result = run_hmart_weekly_planning_digest()

    print(
        f"H Mart weekly job complete: changed={result['changed']} "
        f"sent={result['sent']} deals={result.get('deals', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
