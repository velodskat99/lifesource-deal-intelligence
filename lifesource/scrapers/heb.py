"""H-E-B weekly ad scraper.

Research findings (2026-04-08):
- H-E-B weekly ad is a Next.js app at https://www.heb.com/weekly-ad/deals
- Product data is embedded in the page as JSON inside a <script> tag
- The JSON contains a `props.pageProps.products` array with ~180 items
- Each product has: displayName, productCategory.name, SKUs[].contextPrices[]
- Prices have listPrice (regular) and salePrice (deal) with amounts
- The page also has __APOLLO_STATE__ but the products array is more reliable
"""
import json
import logging
import re

from bs4 import BeautifulSoup

from lifesource.models import Deal
from lifesource.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class HebScraper(BaseScraper):
    store_name = "heb"

    def get_url(self) -> str:
        return "https://www.heb.com/weekly-ad/deals"

    def scrape(self) -> list[Deal]:
        """Override scrape to use Playwright for JS-rendered content."""
        url = self.get_url()
        logger.info(f"[{self.store_name}] Scraping {url} with Playwright")
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(5000)
                html = page.content()
                browser.close()

            deals = self.parse(html)
            logger.info(f"[{self.store_name}] Found {len(deals)} deals")
            return deals
        except ImportError:
            logger.warning("[heb] Playwright not installed, falling back to httpx")
            return super().scrape()

    def parse(self, html: str) -> list[Deal]:
        """Parse H-E-B weekly ad page into Deal objects.

        Extracts product data from the embedded Next.js JSON (props.pageProps.products)
        or falls back to __NEXT_DATA__ script tag.
        """
        products_data = self._extract_products(html)
        if not products_data:
            logger.warning("[heb] No product data found in page")
            return []

        deals = []
        for product in products_data:
            deal = self._parse_product(product)
            if deal:
                deals.append(deal)

        logger.info(f"[heb] Parsed {len(deals)} deals from {len(products_data)} products")
        return deals

    def _extract_products(self, html: str) -> list[dict]:
        """Extract the products array from embedded JSON in the page."""
        soup = BeautifulSoup(html, "html.parser")

        # Strategy 1: Look for __NEXT_DATA__ script tag (standard Next.js pattern)
        next_data_tag = soup.find("script", id="__NEXT_DATA__")
        if next_data_tag and next_data_tag.string:
            try:
                data = json.loads(next_data_tag.string)
                products = (
                    data.get("props", {})
                    .get("pageProps", {})
                    .get("products", [])
                )
                if products:
                    logger.info(f"[heb] Found {len(products)} products in __NEXT_DATA__")
                    return products
            except json.JSONDecodeError:
                logger.warning("[heb] Failed to parse __NEXT_DATA__")

        # Strategy 2: Search all script tags for pageProps with products
        for script in soup.find_all("script"):
            if not script.string:
                continue
            text = script.string.strip()

            # Look for JSON objects containing pageProps.products
            if '"pageProps"' in text and '"products"' in text:
                # Try to parse the whole script content as JSON
                try:
                    data = json.loads(text)
                    products = self._find_products_in_dict(data)
                    if products:
                        logger.info(
                            f"[heb] Found {len(products)} products in embedded JSON"
                        )
                        return products
                except json.JSONDecodeError:
                    pass

                # Try to extract JSON from assignment like: self.__next_f.push([...])
                json_matches = re.findall(r'\{["\']props["\'].*?\}(?=\s*$)', text, re.DOTALL)
                for match in json_matches:
                    try:
                        data = json.loads(match)
                        products = self._find_products_in_dict(data)
                        if products:
                            return products
                    except json.JSONDecodeError:
                        continue

        # Strategy 3: Brute-force search for products array pattern in all scripts
        for script in soup.find_all("script"):
            if not script.string:
                continue
            text = script.string

            # Look for "displayName" which is the product name field
            if '"displayName"' not in text:
                continue

            # Try to find JSON arrays containing product objects
            # Match patterns like [{"id":"...","displayName":"..."}]
            array_pattern = re.findall(
                r'\[(?:\s*\{[^}]*"displayName"[^}]*\}[,\s]*)+\]',
                text,
            )
            for match in array_pattern:
                try:
                    products = json.loads(match)
                    if isinstance(products, list) and len(products) > 0:
                        logger.info(
                            f"[heb] Found {len(products)} products via regex extraction"
                        )
                        return products
                except json.JSONDecodeError:
                    continue

        return []

    def _find_products_in_dict(self, data: dict) -> list[dict]:
        """Recursively search a dict for a 'products' array."""
        if isinstance(data, dict):
            if "products" in data and isinstance(data["products"], list):
                return data["products"]
            for value in data.values():
                result = self._find_products_in_dict(value)
                if result:
                    return result
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    result = self._find_products_in_dict(item)
                    if result:
                        return result
        return []

    def _parse_product(self, product: dict) -> Deal | None:
        """Parse a single product dict into a Deal object."""
        try:
            name = product.get("displayName", "")
            if not name:
                return None

            # Extract category
            category = None
            cat_data = product.get("productCategory")
            if isinstance(cat_data, dict):
                category = cat_data.get("name")

            # Extract prices from SKUs
            sale_price = None
            regular_price = None
            unit = None

            skus = product.get("SKUs", [])
            if not skus:
                # Try alternate field names
                skus = product.get("skus", [])

            for sku in skus:
                context_prices = sku.get("contextPrices", [])
                for cp in context_prices:
                    # Prefer ONLINE context
                    sp = cp.get("salePrice", {})
                    lp = cp.get("listPrice", {})

                    if sp and sp.get("amount") is not None:
                        sale_price = float(sp["amount"])
                    if lp and lp.get("amount") is not None:
                        regular_price = float(lp["amount"])

                    unit_price = cp.get("unitSalePrice", {})
                    if unit_price and unit_price.get("unit"):
                        unit = unit_price["unit"]

                    if sale_price is not None:
                        break
                if sale_price is not None:
                    break

            # If no sale price found, try direct price fields
            if sale_price is None:
                sale_price = product.get("salePrice") or product.get("price")

            if sale_price is None:
                logger.debug(f"[heb] Skipping product with no price: {name}")
                return None

            # Extract image URL
            image_url = None
            image_urls = product.get("productImageUrls", [])
            if image_urls:
                # Prefer medium size
                for img in image_urls:
                    if isinstance(img, dict) and "medium" in str(img.get("url", "")).lower():
                        image_url = img["url"]
                        break
                if not image_url and image_urls:
                    img = image_urls[0]
                    image_url = img["url"] if isinstance(img, dict) else str(img)

            return Deal(
                store="heb",
                item_name=name,
                category=category,
                regular_price=regular_price,
                sale_price=sale_price,
                unit=unit,
                source_url=f"https://www.heb.com/product-detail/{product.get('id', '')}",
                source_type="scraper",
                image_url=image_url,
            )

        except Exception as e:
            logger.warning(f"[heb] Failed to parse product: {e}")
            return None
