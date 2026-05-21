"""99 Ranch Market scraper.

Uses 99 Ranch's internal API (be-api/product/web/home) to get structured
product data with images, prices, and sale information. No AI vision needed.
"""
import logging

from lifesource.models import Deal
from lifesource.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Store ID mapping - 8899 is the default/online store
# TODO: Find Austin-specific store ID if different
STORE_ID = "8899"


class Ranch99Scraper(BaseScraper):
    store_name = "99ranch"

    def get_url(self) -> str:
        return f"https://www.99ranch.com/be-api/product/web/home?storeId={STORE_ID}"

    def scrape(self) -> list[Deal]:
        """Override to use JSON API directly instead of HTML parsing."""
        url = self.get_url()
        logger.info(f"[{self.store_name}] Fetching API: {url}")

        try:
            response = self.client.get(url)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.error(f"[{self.store_name}] API request failed: {e}")
            return []

        return self._parse_api_response(data)

    def parse(self, html: str) -> list[Deal]:
        """Not used - we use the JSON API directly."""
        return []

    def _parse_api_response(self, data: dict) -> list[Deal]:
        """Parse 99 Ranch API response into Deal objects."""
        deals = []
        sections = data.get("data", [])

        for section in sections:
            section_name = section.get("name", "")
            variants = section.get("variants") or []

            for product in variants:
                deal = self._parse_product(product, section_name)
                if deal:
                    deals.append(deal)

        logger.info(f"[{self.store_name}] Parsed {len(deals)} deals from API")
        return deals

    def _parse_product(self, product: dict, section_name: str) -> Deal | None:
        """Parse a single product from the API response."""
        name = product.get("productName", "")
        if not name:
            return None

        price = product.get("price")
        if price is None:
            return None

        try:
            sale_price = float(price)
        except (ValueError, TypeError):
            return None

        # Get regular/retail price
        regular_price = None
        retail = product.get("retailPrice")
        if retail and retail != price:
            try:
                regular_price = float(retail)
            except (ValueError, TypeError):
                pass

        # Check sale price field
        sale_p = product.get("salePrice")
        if sale_p and sale_p != price:
            try:
                # If salePrice < price, then price is regular and salePrice is the deal
                sp = float(sale_p)
                if sp < sale_price:
                    regular_price = sale_price
                    sale_price = sp
            except (ValueError, TypeError):
                pass

        # Image URL
        image_url = product.get("image", "")

        # Category from section name or product name
        category = self._guess_category(name, section_name)

        return Deal(
            store="99ranch",
            item_name=name,
            category=category,
            sale_price=sale_price,
            regular_price=regular_price,
            image_url=image_url if image_url else None,
            source_url="https://www.99ranch.com/",
            source_type="scraper",
        )

    def _guess_category(self, name: str, section_name: str) -> str:
        """Guess product category from name."""
        name_lower = name.lower()
        keywords = {
            "produce": ["apple", "grape", "pear", "orange", "radish", "lettuce",
                       "cabbage", "onion", "mushroom", "pepper", "tomato", "banana",
                       "mango", "avocado", "potato", "spinach", "bok choy", "garlic"],
            "meat": ["beef", "pork", "chicken", "lamb", "steak", "rib", "ground",
                    "sausage", "bacon", "ham", "duck"],
            "seafood": ["shrimp", "salmon", "fish", "crab", "clam", "squid",
                       "octopus", "mussel", "oyster", "tuna", "cod", "lobster"],
            "dairy": ["milk", "cheese", "yogurt", "tofu", "egg", "butter", "cream"],
            "frozen": ["frozen", "dumpling", "ice cream", "mochi", "bao"],
            "beverages": ["tea", "coffee", "juice", "water", "soda", "drink"],
            "pantry": ["ramen", "noodle", "rice", "sauce", "oil", "vinegar",
                      "soup", "seasoning", "soy", "paste", "flour", "snack",
                      "chip", "cracker", "cookie"],
            "bakery": ["bread", "cake", "pastry", "bun"],
        }
        for cat, words in keywords.items():
            if any(w in name_lower for w in words):
                return cat
        if "beauty" in section_name.lower():
            return "household"
        if "clearance" in section_name.lower():
            return "other"
        return "pantry"
