"""Trader Joe's scraper.

Uses Trader Joe's GraphQL API (traderjoes.com/api/graphql) to get the full
product catalog with prices, images, and categories.

TJ doesn't do traditional sales — all items are everyday low price.
Products are imported with sale_price = retail price and no regular_price,
so they won't show "% off" badges but will appear in cross-store comparisons.

Requires curl_cffi for TLS fingerprint impersonation (Akamai bot protection).
"""
import logging

from curl_cffi import requests as cffi_requests

from lifesource.models import Deal
from lifesource.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://www.traderjoes.com/api/graphql"

SEARCH_QUERY = """
query SearchProducts($categoryId: String, $currentPage: Int, $pageSize: Int,
                      $published: String) {
  products(
    filter: {
      category_id: { eq: $categoryId }
      published: { eq: $published }
    }
    currentPage: $currentPage
    pageSize: $pageSize
  ) {
    items {
      sku
      item_title
      category_hierarchy {
        name
      }
      price_range {
        minimum_price {
          final_price {
            value
            currency
          }
        }
      }
      retail_price
      sales_size
      sales_uom_description
      primary_image
      primary_image_meta {
        url
      }
    }
    total_count
    page_info {
      current_page
      total_pages
    }
  }
}
"""

# Category ID 2 = all food products (~2700 items)
FOOD_CATEGORY_ID = "2"

MAX_PAGES = 30
PAGE_SIZE = 100

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://www.traderjoes.com",
    "Referer": "https://www.traderjoes.com/home/products",
}


class TraderJoesScraper(BaseScraper):
    store_name = "traderjoes"

    def get_url(self) -> str:
        return GRAPHQL_URL

    def scrape(self) -> list[Deal]:
        """Override to use GraphQL API with curl_cffi for Akamai bypass."""
        logger.info(f"[{self.store_name}] Fetching from GraphQL API")
        all_deals = []
        page = 1

        while page <= MAX_PAGES:
            variables = {
                "categoryId": FOOD_CATEGORY_ID,
                "currentPage": page,
                "pageSize": PAGE_SIZE,
                "published": "1",
            }

            try:
                response = cffi_requests.post(
                    GRAPHQL_URL,
                    json={"query": SEARCH_QUERY, "variables": variables},
                    headers=HEADERS,
                    impersonate="chrome",
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                logger.error(f"[{self.store_name}] GraphQL request failed (page {page}): {e}")
                break

            if "errors" in data:
                logger.error(f"[{self.store_name}] GraphQL errors: {data['errors']}")
                break

            products_data = data.get("data", {}).get("products", {})
            items = products_data.get("items", [])

            if not items:
                break

            for item in items:
                deal = self._parse_product(item)
                if deal:
                    all_deals.append(deal)

            page_info = products_data.get("page_info", {})
            total_pages = page_info.get("total_pages", 1)

            logger.info(
                f"[{self.store_name}] Page {page}/{total_pages} "
                f"({len(items)} items, {len(all_deals)} deals so far)"
            )

            if page >= total_pages:
                break
            page += 1

        # Deduplicate by SKU
        seen = set()
        unique = []
        for d in all_deals:
            if d.item_name not in seen:
                seen.add(d.item_name)
                unique.append(d)

        logger.info(f"[{self.store_name}] Total: {len(unique)} unique products")
        return unique

    def parse(self, html: str) -> list[Deal]:
        """Not used — we query GraphQL directly."""
        return []

    def _parse_product(self, item: dict) -> Deal | None:
        """Parse a single TJ product into a Deal."""
        name = item.get("item_title", "").strip()
        if not name:
            return None

        # Price — try retail_price first, then price_range
        price_val = item.get("retail_price")
        if price_val is None:
            price_range = item.get("price_range", {})
            min_price = price_range.get("minimum_price", {})
            final = min_price.get("final_price", {})
            price_val = final.get("value")

        if price_val is None:
            return None

        try:
            sale_price = float(price_val)
        except (ValueError, TypeError):
            return None

        if sale_price <= 0:
            return None

        # Unit
        unit = item.get("sales_uom_description", "")
        sales_size = item.get("sales_size", "")
        if sales_size and unit:
            unit = f"{sales_size} {unit}"
        elif not unit:
            unit = None

        # Image
        image_url = None
        image_meta = item.get("primary_image_meta") or {}
        if image_meta.get("url"):
            image_url = image_meta["url"]

        # Category
        category = self._guess_category(name, item)

        return Deal(
            store="traderjoes",
            item_name=name,
            category=category,
            sale_price=sale_price,
            regular_price=None,  # TJ = everyday low price
            unit=unit,
            image_url=image_url,
            source_url="https://www.traderjoes.com/home/products",
            source_type="scraper",
        )

    def _guess_category(self, name: str, item: dict) -> str:
        """Guess category from TJ category hierarchy, falling back to name keywords."""
        hierarchy = item.get("category_hierarchy") or []
        cat_names = [c.get("name", "").lower() for c in hierarchy]
        cat_str = " ".join(cat_names)

        if any(k in cat_str for k in ["produce", "fruit", "vegetable"]):
            return "produce"
        if any(k in cat_str for k in ["meat", "poultry"]):
            return "meat"
        if any(k in cat_str for k in ["seafood", "fish"]):
            return "seafood"
        if any(k in cat_str for k in ["dairy", "egg", "cheese"]):
            return "dairy"
        if "frozen" in cat_str:
            return "frozen"
        if any(k in cat_str for k in ["beverage", "drink", "coffee", "tea", "juice"]):
            return "beverages"
        if any(k in cat_str for k in ["bakery", "bread"]):
            return "bakery"
        if any(k in cat_str for k in ["snack", "cookie", "chip", "cracker"]):
            return "pantry"

        # Fallback: keyword matching on product name
        name_lower = name.lower()
        keywords = {
            "produce": ["apple", "grape", "pear", "orange", "lettuce", "spinach",
                        "tomato", "banana", "mango", "avocado", "potato", "onion",
                        "pepper", "mushroom", "garlic", "berry", "berries", "kale"],
            "meat": ["beef", "pork", "chicken", "turkey", "lamb", "steak",
                     "sausage", "bacon", "ground"],
            "seafood": ["shrimp", "salmon", "fish", "crab", "tuna", "cod"],
            "dairy": ["milk", "cheese", "yogurt", "tofu", "egg", "butter", "cream"],
            "frozen": ["frozen", "ice cream"],
            "beverages": ["tea", "coffee", "juice", "water", "soda",
                          "sparkling", "lemonade", "kombucha"],
            "bakery": ["bread", "bagel", "croissant", "muffin", "tortilla"],
            "pantry": ["ramen", "noodle", "rice", "sauce", "oil", "pasta",
                       "soup", "seasoning", "flour", "cereal", "granola"],
        }
        for cat, words in keywords.items():
            if any(w in name_lower for w in words):
                return cat

        return "other"
