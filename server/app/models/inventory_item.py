import uuid
from datetime import datetime

from sqlalchemy import String, Text, Numeric, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="product")  # "product" or "service"
    ean: Mapped[str | None] = mapped_column(String(14), nullable=True, unique=True)
    hsn: Mapped[str | None] = mapped_column(String(10), nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)  # null for services
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="piece")
    images: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
