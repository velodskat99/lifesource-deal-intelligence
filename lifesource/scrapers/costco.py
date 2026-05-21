"""Costco deals scraper.

Costco publishes deals via:
1. Monthly coupon book (image-based, parsed via AI vision)
2. Warehouse savings on costco.com (structured data when available)

This scraper attempts structured scraping first, falls back to AI vision.
"""
import logging

from bs4 import BeautifulSoup

from lifesource.config import get_settings
from lifesource.models import Deal
from lifesource.scrapers.base import BaseScraper
from lifesource.scrapers.vision import parse_flyer_to_deals

logger = logging.getLogger(__name__)

# Aggregator sites that host Costco coupon book scans
FLYER_SOURCES = [
    "https://www.costcoinsider.com/",  # Weekly insider deals
]


class CostcoScraper(BaseScraper):
    store_name = "costco"

    def get_url(self) -> str:
        return FLYER_SOURCES[0]

    def parse(self, html: str) -> list[Deal]:
        """Extract Costco deals from aggregator pages using AI vision."""
        image_urls = self._extract_flyer_images(html)
        if not image_urls:
            logger.warning("[costco] No flyer images found")
            return []

        settings = get_settings()
        return parse_flyer_to_deals(image_urls, "costco", settings.anthropic_api_key)

    def _extract_flyer_images(self, html: str) -> list[str]:
        """Extract coupon book/deal image URLs from Costco aggregator pages."""
        soup = BeautifulSoup(html, "html.parser")
        image_urls = []

        # Look for deal/coupon images
        for img in soup.find_all("img"):
            src = img.get("src", "") or img.get("data-src", "") or img.get("data-lazy-src", "")
            if not src:
                continue

            # Match Costco deal images
            if any(
                pattern in src.lower()
                for pattern in [
                    "costco", "coupon", "deal", "insider",
                    "warehouse", "savings", "upload", "flyer",
                ]
            ):
                # Skip tiny thumbnails
                if "150x150" in src or "icon" in src.lower():
                    continue
                if src not in image_urls:
                    image_urls.append(src)

        # Check article content for deal images
        for container in soup.select(
            ".entry-content, .post-content, article, .wp-block-image"
        ):
            for img in container.find_all("img"):
                src = img.get("src", "") or img.get("data-src", "")
                if src and src not in image_urls:
                    image_urls.append(src)

        logger.info(f"[costco] Found {len(image_urls)} deal images")
        return image_urls[:15]  # Coupon books can have many pages
