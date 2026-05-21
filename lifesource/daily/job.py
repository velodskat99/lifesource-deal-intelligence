import asyncio
import logging

from lifesource.config import get_settings
from lifesource.db import get_connection, init_db
from lifesource.daily.backup import backup_database
from lifesource.models import Deal
from lifesource.notifications.digest import format_digest
from lifesource.notifications.telegram import send_telegram_message
from lifesource.scrapers.base import ScraperError
from lifesource.scrapers.heb import HebScraper
from lifesource.scrapers.costco import CostcoScraper
from lifesource.scrapers.ranch99 import Ranch99Scraper
from lifesource.scrapers.hmart import HmartScraper
from lifesource.scoring.engine import score_deals

logger = logging.getLogger(__name__)


def store_deals(deals: list[Deal], db_path: str) -> int:
    """Store deals in the database. Returns count stored."""
    conn = get_connection(db_path)
    count = 0
    for deal in deals:
        conn.execute(
            """INSERT INTO deals (store, item_name, product_id, category,
               regular_price, sale_price, unit, start_date, end_date,
               source_url, source_type, confidence, image_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                deal.store, deal.item_name, deal.product_id, deal.category,
                deal.regular_price, deal.sale_price, deal.unit,
                str(deal.start_date) if deal.start_date else None,
                str(deal.end_date) if deal.end_date else None,
                deal.source_url, deal.source_type, deal.confidence,
                deal.image_url,
            ),
        )
        count += 1
    conn.commit()
    conn.close()
    return count


def run_daily_job(db_path: str | None = None) -> dict:
    """Run the full daily scraping and notification pipeline."""
    settings = get_settings()
    db_path = db_path or settings.db_path
    init_db(db_path)

    all_deals: list[Deal] = []
    errors: list[str] = []

    # --- Step 1: Scrape all stores ---
    scrapers = [
        ("H-E-B", HebScraper),
        ("Costco", CostcoScraper),
        ("99 Ranch", Ranch99Scraper),
        ("H Mart", HmartScraper),
    ]

    for store_name, scraper_cls in scrapers:
        try:
            scraper = scraper_cls()
            deals = scraper.scrape()
            all_deals.extend(deals)
            logger.info(f"{store_name}: {len(deals)} deals")
        except (ScraperError, Exception) as e:
            errors.append(f"{store_name}: {e}")
            logger.error(f"{store_name} scraper failed: {e}")

    # --- Step 2: Store deals ---
    stored = store_deals(all_deals, db_path)
    logger.info(f"Stored {stored} deals in database")

    # --- Step 3: Score deals ---
    scored = score_deals(all_deals, user_prefs={})

    # --- Step 4: Send Telegram digest ---
    above_threshold = [
        d for d in scored if (d.score or 0) >= settings.deal_score_threshold
    ]
    digest = format_digest(deals=above_threshold)

    if errors:
        digest += "\n\n--- WARNINGS ---\n"
        for err in errors:
            digest += f"  {err}\n"

    try:
        asyncio.run(
            send_telegram_message(
                digest, settings.telegram_bot_token, settings.telegram_chat_id
            )
        )
    except Exception as e:
        errors.append(f"Telegram send failed: {e}")
        logger.error(f"Failed to send Telegram digest: {e}")

    # --- Step 5: Backup ---
    try:
        backup_database(db_path, settings.backup_dir, settings.backup_retention_days)
    except Exception as e:
        logger.error(f"Backup failed: {e}")

    return {
        "deals_found": len(all_deals),
        "deals_above_threshold": len(above_threshold),
        "errors": errors,
    }
