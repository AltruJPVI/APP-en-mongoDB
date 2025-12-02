from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from .users import Location

# Enum for payment method
class PaymentMethod(str, Enum):
    card = "card"
    paypal = "paypal"
    transfer = "transfer"

# Schema for order item
class OrderItem(BaseModel):
    product_id: str
    name: str  # We save historical name
    price: float = Field(..., gt=0)  # Price at time of purchase
    quantity: int = Field(..., gt=0)
    size: Optional[str] = None
    image: Optional[str] = None

# Schema to CREATE order
class OrderCreate(BaseModel):
    user_id: str  # ID of the user making the purchase
    items: List[OrderItem] = Field(..., min_length=1)  # At least 1 item
    total: float = Field(..., gt=0)
    shipping_address: Location  # Reused from user
    payment_method: PaymentMethod

class OrderResponse(BaseModel):
    id: str = Field(..., alias="_id")
    order_number: str  # Automatically generated (e.g.: ORD-2025-001)
    user_id: str
    order_date: datetime
    items: List[OrderItem]
    total: float
    shipping_address: Location
    payment_method: PaymentMethod
    
    class Config:
        populate_by_name = True
