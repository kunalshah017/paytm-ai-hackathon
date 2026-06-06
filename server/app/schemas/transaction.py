from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class TransactionCreate(BaseModel):
    order_id: UUID
    amount: float = Field(..., gt=0)
    payment_method: str | None = None
    payment_link: str | None = None


class TransactionUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|cancelled|paid)$")
    payment_link: str | None = None
    payment_method: str | None = None


class TransactionResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    order_id: UUID
    payment_link: str | None
    amount: float
    payment_method: str | None
    status: str

    model_config = {"from_attributes": True}
