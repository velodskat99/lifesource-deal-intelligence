import logging
import time
from abc import ABC, abstractmethod

import httpx

from lifesource.models import Deal

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Raised when a scraper fails after all retries."""
    pass


class BaseScraper(ABC):
    store_name: str

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )

    def fetch(self, url: str) -> str:
        """Fetch a URL with retry logic. Returns HTML string."""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.get(url)
                response.raise_for_status()
                return response.text
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                last_error = e
                logger.warning(
                    f"[{self.store_name}] Attempt {attempt + 1}/{self.max_retries} "
                    f"failed for {url}: {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))

        raise ScraperError(
            f"[{self.store_name}] Failed after {self.max_retries} attempts: {last_error}"
        )

    @abstractmethod
    def get_url(self) -> str:
        """Return the URL to scrape."""
        ...

    @abstractmethod
    def parse(self, html: str) -> list[Deal]:
        """Parse HTML into a list of Deal objects."""
        ...

    def scrape(self) -> list[Deal]:
        """Fetch and parse deals. Main entry point."""
        url = self.get_url()
        logger.info(f"[{self.store_name}] Scraping {url}")
        html = self.fetch(url)
        deals = self.parse(html)
        logger.info(f"[{self.store_name}] Found {len(deals)} deals")
        return deals
