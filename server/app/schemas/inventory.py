from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class InventoryItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    type: str = Field(default="product", pattern="^(product|service)$")
    ean: str | None = None
    hsn: str | None = None
    price: float = Field(..., gt=0)
    quantity: int | None = None
    unit: str = Field(default="piece", max_length=20)
    images: list[str] = []


class InventoryItemUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    type: str | None = Field(None, pattern="^(product|service)$")
    ean: str | None = None
    hsn: str | None = None
    price: float | None = Field(None, gt=0)
    quantity: int | None = None
    unit: str | None = Field(None, max_length=20)
    images: list[str] | None = None


class InventoryItemResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    name: str
    description: str | None
    type: str
    ean: str | None
    hsn: str | None
    price: float
    quantity: int | None
    unit: str
    images: list[str]

    model_config = {"from_attributes": True}
