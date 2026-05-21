from datetime import date
from unittest.mock import AsyncMock

from lifesource.db import init_db
from lifesource.daily.hmart_weekly import (
    run_hmart_weekly_ad_monitor,
    run_hmart_weekly_planning_digest,
)
from lifesource.sources.hmart_weekly import HMART_TEXAS_WEEKLY_AD_URL, WeeklyAdInspection


class FakeSource:
    store = "hmart"
    region = "texas"
    source_type = "weekly_ad"
    source_url = HMART_TEXAS_WEEKLY_AD_URL

    def __init__(self, fingerprint="abc123", warnings=None):
        self.fingerprint = fingerprint
        self.warnings = warnings or []

    def check(self):
        return WeeklyAdInspection(
            source_url=self.source_url,
            fingerprint=self.fingerprint,
            assets=["https://cdn.hmart.com/weekly-ads/texas/page-1.jpg"],
            metadata={"strategy": "weekly_ad_assets"},
            warnings=self.warnings,
        )


def test_hmart_weekly_ad_monitor_sends_when_fingerprint_changes(tmp_db):
    init_db(tmp_db)
    sender = AsyncMock()

    result = run_hmart_weekly_ad_monitor(
        db_path=tmp_db,
        source=FakeSource(),
        sender=sender,
        telegram_bot_token="token",
        telegram_chat_id="chat",
        today=date(2026, 5, 21),
    )

    assert result["changed"] is True
    assert result["sent"] is True
    sender.assert_awaited_once()
    assert "H Mart Texas weekly ad refreshed" in sender.await_args.args[0]


def test_hmart_weekly_ad_monitor_sends_nothing_when_unchanged(tmp_db):
    init_db(tmp_db)
    sender = AsyncMock()
    source = FakeSource()

    run_hmart_weekly_ad_monitor(
        db_path=tmp_db,
        source=source,
        sender=sender,
        telegram_bot_token="token",
        telegram_chat_id="chat",
    )
    sender.reset_mock()
    result = run_hmart_weekly_ad_monitor(
        db_path=tmp_db,
        source=source,
        sender=sender,
        telegram_bot_token="token",
        telegram_chat_id="chat",
    )

    assert result["changed"] is False
    assert result["sent"] is False
    sender.assert_not_awaited()


def test_hmart_weekly_planning_digest_sends_even_when_unchanged(tmp_db):
    init_db(tmp_db)
    sender = AsyncMock()
    source = FakeSource()

    run_hmart_weekly_ad_monitor(
        db_path=tmp_db,
        source=source,
        sender=AsyncMock(),
        telegram_bot_token="token",
        telegram_chat_id="chat",
    )
    result = run_hmart_weekly_planning_digest(
        db_path=tmp_db,
        source=source,
        sender=sender,
        telegram_bot_token="token",
        telegram_chat_id="chat",
        today=date(2026, 5, 21),
    )

    assert result["changed"] is False
    assert result["sent"] is True
    sender.assert_awaited_once()
    assert "H Mart Texas weekly planning" in sender.await_args.args[0]
