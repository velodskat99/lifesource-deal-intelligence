import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch

from lifesource.models import Deal


def _mock_all_scrapers():
    """Return context managers that mock all scraper classes."""
    return (
        patch("lifesource.daily.job.HebScraper"),
        patch("lifesource.daily.job.CostcoScraper"),
        patch("lifesource.daily.job.Ranch99Scraper"),
        patch("lifesource.daily.job.HmartScraper"),
        patch("lifesource.daily.job.send_telegram_message", new_callable=AsyncMock),
        patch("lifesource.daily.job.get_settings"),
        patch("lifesource.daily.job.backup_database"),
    )


def test_run_daily_job_scrapes_and_stores(tmp_db):
    from lifesource.db import init_db
    from lifesource.daily.job import run_daily_job

    init_db(tmp_db)

    mock_deals = [
        Deal(
            store="heb",
            item_name="Eggs",
            regular_price=3.49,
            sale_price=1.99,
            source_type="scraper",
        ),
    ]

    with (
        patch("lifesource.daily.job.HebScraper") as MockHeb,
        patch("lifesource.daily.job.CostcoScraper") as MockCostco,
        patch("lifesource.daily.job.Ranch99Scraper") as MockRanch99,
        patch("lifesource.daily.job.HmartScraper") as MockHmart,
        patch("lifesource.daily.job.send_telegram_message", new_callable=AsyncMock),
        patch("lifesource.daily.job.get_settings") as mock_settings,
        patch("lifesource.daily.job.backup_database"),
    ):
        mock_settings.return_value = MagicMock(
            db_path=tmp_db,
            telegram_bot_token="test",
            telegram_chat_id="123",
            deal_score_threshold=40,
            backup_dir="backups",
            backup_retention_days=30,
        )
        MockHeb.return_value.scrape.return_value = mock_deals
        MockCostco.return_value.scrape.return_value = []
        MockRanch99.return_value.scrape.return_value = []
        MockHmart.return_value.scrape.return_value = []

        result = run_daily_job(db_path=tmp_db)

    assert result["deals_found"] == 1
    assert result["errors"] == []

    # Verify deals were stored
    conn = sqlite3.connect(tmp_db)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM deals").fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0]["item_name"] == "Eggs"


def test_run_daily_job_handles_scraper_failure(tmp_db):
    from lifesource.db import init_db
    from lifesource.daily.job import run_daily_job
    from lifesource.scrapers.base import ScraperError

    init_db(tmp_db)

    with (
        patch("lifesource.daily.job.HebScraper") as MockHeb,
        patch("lifesource.daily.job.CostcoScraper") as MockCostco,
        patch("lifesource.daily.job.Ranch99Scraper") as MockRanch99,
        patch("lifesource.daily.job.HmartScraper") as MockHmart,
        patch("lifesource.daily.job.send_telegram_message", new_callable=AsyncMock),
        patch("lifesource.daily.job.get_settings") as mock_settings,
        patch("lifesource.daily.job.backup_database"),
    ):
        mock_settings.return_value = MagicMock(
            db_path=tmp_db,
            telegram_bot_token="test",
            telegram_chat_id="123",
            deal_score_threshold=40,
            backup_dir="backups",
            backup_retention_days=30,
        )
        MockHeb.return_value.scrape.side_effect = ScraperError("H-E-B down")
        MockCostco.return_value.scrape.return_value = []
        MockRanch99.return_value.scrape.return_value = []
        MockHmart.return_value.scrape.return_value = []

        result = run_daily_job(db_path=tmp_db)

    assert result["deals_found"] == 0
    assert len(result["errors"]) == 1
    assert "H-E-B" in result["errors"][0]
