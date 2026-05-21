from datetime import date
from typing import Optional

from pydantic import BaseModel, computed_field


class Deal(BaseModel):
    id: Optional[int] = None
    store: str
    item_name: str
    product_id: Optional[int] = None
    category: Optional[str] = None
    regular_price: Optional[float] = None
    sale_price: float
    unit: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    source_url: Optional[str] = None
    source_type: str
    confidence: Optional[float] = None
    score: Optional[float] = None
    image_url: Optional[str] = None

    @computed_field
    @property
    def discount_pct(self) -> float:
        if self.regular_price and self.regular_price > 0:
            return (self.regular_price - self.sale_price) / self.regular_price
        return 0.0


class Product(BaseModel):
    id: Optional[int] = None
    name: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    aliases: list[str] = []


class Purchase(BaseModel):
    id: Optional[int] = None
    product_id: Optional[int] = None
    store: str
    item_name: str
    price: float
    quantity: float = 1
    unit: Optional[str] = None
    purchase_date: date
    source: str = "manual"


class UserPreference(BaseModel):
    product_id: int
    avg_purchase_frequency_days: Optional[float] = None
    preferred_store: Optional[str] = None
    avg_price_paid: Optional[float] = None
    last_purchased: Optional[date] = None
    total_purchases: int = 0
