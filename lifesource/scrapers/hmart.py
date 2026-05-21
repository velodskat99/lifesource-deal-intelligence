"""H Mart weekly sale scraper.

Scrapes structured JSON-LD product data from hmart.com/sale page.
Gets product images, prices, and names directly - no AI vision needed.
"""
import json
import logging

from bs4 import BeautifulSoup

from lifesource.models import Deal
from lifesource.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class HmartScraper(BaseScraper):
    store_name = "hmart"

    def get_url(self) -> str:
        return "https://www.hmart.com/sale?map=productClusterIds"

    def parse(self, html: str) -> list[Deal]:
        """Parse H Mart sale page JSON-LD structured data."""
        soup = BeautifulSoup(html, "html.parser")

        deals = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(data, dict) or data.get("@type") != "ItemList":
                continue

            list_name = data.get("name", "")
            for item in data.get("itemListElement", []):
                product = item.get("item", {})
                if product.get("@type") != "Product":
                    continue

                name = product.get("name", "")
                if not name:
                    continue

                offer = product.get("offers", {})
                price = offer.get("lowPrice") or offer.get("price")
                high_price = offer.get("highPrice")

                if price is None:
                    continue

                try:
                    sale_price = float(price)
                except (ValueError, TypeError):
                    continue

                regular_price = None
                if high_price and high_price != price:
                    try:
                        regular_price = float(high_price)
                    except (ValueError, TypeError):
                        pass

                # Get image URL
                image_url = product.get("image", "")
                if isinstance(image_url, list):
                    image_url = image_url[0] if image_url else ""

                # Guess category from list name or product name
                category = self._guess_category(name, list_name)

                deals.append(Deal(
                    store="hmart",
                    item_name=name,
                    category=category,
                    sale_price=sale_price,
                    regular_price=regular_price,
                    image_url=image_url if image_url else None,
                    source_url=f"https://www.hmart.com/sale",
                    source_type="scraper",
                ))

        logger.info(f"[hmart] Parsed {len(deals)} deals from JSON-LD")
        return deals

    def _guess_category(self, name: str, list_name: str) -> str:
        """Guess product category from name/context."""
        name_lower = name.lower()
        keywords = {
            "produce": ["apple", "grape", "pear", "orange", "radish", "lettuce",
                       "cabbage", "onion", "mushroom", "pepper", "tomato", "banana",
                       "mango", "avocado", "potato", "spinach", "celery", "garlic"],
            "meat": ["beef", "pork", "chicken", "lamb", "steak", "rib", "ground",
                    "sausage", "bacon", "ham"],
            "seafood": ["shrimp", "salmon", "fish", "crab", "clam", "squid",
                       "octopus", "mussel", "oyster", "tuna", "cod"],
            "dairy": ["milk", "cheese", "yogurt", "tofu", "egg", "butter", "cream"],
            "frozen": ["frozen", "dumpling", "ice cream", "mochi"],
            "beverages": ["tea", "coffee", "juice", "water", "soda", "drink"],
            "pantry": ["ramen", "noodle", "rice", "sauce", "oil", "vinegar",
                      "soup", "seasoning", "soy", "paste", "flour"],
            "bakery": ["bread", "cake", "pastry", "cookie", "bun"],
        }
        for cat, words in keywords.items():
            if any(w in name_lower for w in words):
                return cat
        return "other"
