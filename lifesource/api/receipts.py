"""Receipt scanning API using Claude Vision."""
import base64
import json
import logging

import httpx
from fastapi import APIRouter, UploadFile, File

from lifesource.db import get_db

logger = logging.getLogger(__name__)

RECEIPT_PROMPT = """You are extracting purchase data from a grocery store receipt image.

Extract:
- store_name: The store name (e.g., "H-E-B", "Costco", "99 Ranch", "H Mart")
- items: Array of items, each with:
  - item_name: Product name
  - price: Price paid (number, no $)
  - quantity: Quantity if shown, default 1

Return JSON only:
{"store_name": "H-E-B", "items": [{"item_name": "Eggs", "price": 2.49, "quantity": 1}]}
"""

STORE_NORMALIZE = {
    "h-e-b": "heb", "heb": "heb", "h.e.b": "heb",
    "costco": "costco",
    "99 ranch": "99ranch", "99ranch": "99ranch",
    "h mart": "hmart", "hmart": "hmart", "h-mart": "hmart",
}


def create_receipts_router(db_path: str) -> APIRouter:
    router = APIRouter()

    @router.post("/purchases/receipt")
    async def scan_receipt(file: UploadFile = File(...)):
        """Upload a receipt image for OCR parsing via Claude Vision."""
        from lifesource.config import get_settings
        settings = get_settings()

        image_data = await file.read()
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        media_type = "image/jpeg"
        if file.content_type:
            media_type = file.content_type

        # Call Claude API
        client = httpx.Client(timeout=60.0)
        try:
            response = client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 2048,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {
                                "type": "base64", "media_type": media_type, "data": image_b64,
                            }},
                            {"type": "text", "text": RECEIPT_PROMPT},
                        ],
                    }],
                },
            )
            response.raise_for_status()
            result = response.json()

            text = ""
            for block in result.get("content", []):
                if block.get("type") == "text":
                    text += block["text"]

            # Parse response
            start = text.index("{")
            end = text.rindex("}") + 1
            parsed = json.loads(text[start:end])

            # Normalize store name
            store_raw = parsed.get("store_name", "").lower().strip()
            store = STORE_NORMALIZE.get(store_raw, store_raw)

            # Store purchases in DB
            items = parsed.get("items", [])
            from datetime import date
            today = date.today().isoformat()

            with get_db(db_path) as conn:
                for item in items:
                    conn.execute(
                        """INSERT INTO purchase_history (store, item_name, price, quantity,
                           purchase_date, source) VALUES (?, ?, ?, ?, ?, ?)""",
                        (store, item["item_name"], item["price"],
                         item.get("quantity", 1), today, "receipt"),
                    )
                conn.commit()

            return {
                "status": "success",
                "store": store,
                "items_parsed": len(items),
                "items": items,
            }

        except Exception as e:
            logger.error(f"Receipt scan failed: {e}")
            return {"status": "error", "message": str(e)}

    return router
