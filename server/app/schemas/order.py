from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class OrderItemCreate(BaseModel):
    inventory_item_id: UUID
    quantity: int = Field(..., gt=0)


class OrderItemResponse(BaseModel):
    id: UUID
    inventory_item_id: UUID
    quantity: int
    price_at_purchase: float
    item_name: str | None = None

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    customer_name: str | None = None
    customer_phone: str | None = None
    items: list[OrderItemCreate] = Field(..., min_length=1)


class OrderResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    customer_name: str | None
    customer_phone: str | None
    total_price: float
    status: str
    items: list[OrderItemResponse] = []

    model_config = {"from_attributes": True}
