"""AI vision-based flyer parser using Claude API.

Used for stores that publish deals as images (99 Ranch, H Mart, Costco coupon book).
Downloads flyer images and sends them to Claude's vision model to extract deal data.
"""
import hashlib
import json
import logging
from pathlib import Path

import httpx

from lifesource.models import Deal

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent.parent / ".flyer_cache"

EXTRACTION_PROMPT = """You are extracting grocery deal data from a store flyer image.

For each deal/item visible in the image, extract:
- item_name: The product name
- sale_price: The sale/deal price (number only, no $)
- regular_price: The regular/original price if shown (number only, no $), or null
- unit: The unit (each, lb, oz, pack, etc.), or null
- category: Best guess category (produce, meat, seafood, dairy, pantry, bakery, beverages, frozen, household, other)

Return a JSON array of objects. Example:
[
  {"item_name": "Fresh Salmon Fillet", "sale_price": 6.99, "regular_price": 9.99, "unit": "lb", "category": "seafood"},
  {"item_name": "Bok Choy", "sale_price": 0.79, "regular_price": 1.29, "unit": "lb", "category": "produce"}
]

Rules:
- Extract ALL visible deals, not just a few
- If a price says something like "2 for $5", calculate the per-unit price (2.50)
- If you can't read a price clearly, skip that item
- Return ONLY the JSON array, no other text
"""


def get_cache_path(url: str) -> Path:
    """Get cache file path for a flyer URL."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    return CACHE_DIR / f"{url_hash}.json"


def is_cached(url: str) -> bool:
    """Check if a flyer URL has already been parsed."""
    return get_cache_path(url).exists()


def get_cached(url: str) -> list[dict] | None:
    """Get cached parsed results for a flyer URL."""
    cache_path = get_cache_path(url)
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text())
        except json.JSONDecodeError:
            return None
    return None


def save_cache(url: str, items: list[dict]) -> None:
    """Cache parsed results for a flyer URL."""
    cache_path = get_cache_path(url)
    cache_path.write_text(json.dumps(items, indent=2))


def download_image(url: str) -> bytes:
    """Download an image from a URL."""
    client = httpx.Client(timeout=30.0, follow_redirects=True)
    response = client.get(url)
    response.raise_for_status()
    return response.content


def parse_flyer_image(image_data: bytes, api_key: str) -> list[dict]:
    """Send a flyer image to Claude API for deal extraction.

    Returns a list of dicts with item_name, sale_price, regular_price, unit, category.
    """
    import base64

    image_b64 = base64.b64encode(image_data).decode("utf-8")

    # Determine media type (assume JPEG for most flyers)
    media_type = "image/jpeg"
    if image_data[:4] == b"\x89PNG":
        media_type = "image/png"
    elif image_data[:4] == b"%PDF":
        # PDF not directly supported via base64 image; would need different handling
        logger.warning("PDF format detected -- skipping (not supported for vision)")
        return []

    client = httpx.Client(timeout=60.0)
    response = client.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": EXTRACTION_PROMPT,
                        },
                    ],
                }
            ],
        },
    )
    response.raise_for_status()
    result = response.json()

    # Extract the text content from Claude's response
    text = ""
    for block in result.get("content", []):
        if block.get("type") == "text":
            text += block["text"]

    # Parse JSON from response
    try:
        # Find JSON array in response (Claude might include extra text)
        start = text.index("[")
        end = text.rindex("]") + 1
        items = json.loads(text[start:end])
        return items
    except (ValueError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to parse Claude vision response: {e}")
        logger.debug(f"Raw response: {text[:500]}")
        return []


def parse_flyer_to_deals(
    image_urls: list[str],
    store: str,
    api_key: str,
) -> list[Deal]:
    """Download and parse flyer images into Deal objects.

    Uses caching to avoid re-parsing the same flyer images.
    """
    all_deals = []

    for url in image_urls:
        # Check cache first
        cached = get_cached(url)
        if cached is not None:
            logger.info(f"[{store}] Using cached results for {url}")
            items = cached
        else:
            logger.info(f"[{store}] Downloading and parsing flyer: {url}")
            try:
                image_data = download_image(url)
                items = parse_flyer_image(image_data, api_key)
                save_cache(url, items)
                logger.info(f"[{store}] Extracted {len(items)} items from flyer")
            except Exception as e:
                logger.warning(f"[{store}] Failed to process flyer {url}: {e}")
                continue

        # Convert to Deal objects
        for item in items:
            try:
                deal = Deal(
                    store=store,
                    item_name=item["item_name"],
                    sale_price=float(item["sale_price"]),
                    regular_price=(
                        float(item["regular_price"])
                        if item.get("regular_price")
                        else None
                    ),
                    unit=item.get("unit"),
                    category=item.get("category"),
                    source_url=url,
                    source_type="ai_vision",
                    confidence=0.8,  # Default confidence for AI-parsed items
                )
                all_deals.append(deal)
            except (KeyError, ValueError, TypeError) as e:
                logger.debug(f"[{store}] Skipping malformed item: {e}")

    return all_deals
