from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DBSession
from app.models.inventory_item import InventoryItem
from app.schemas.inventory import InventoryItemCreate, InventoryItemUpdate, InventoryItemResponse

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/", response_model=list[InventoryItemResponse])
async def list_items(db: DBSession, type: str | None = None):
    stmt = select(InventoryItem).order_by(InventoryItem.created_at.desc())
    if type:
        stmt = stmt.where(InventoryItem.type == type)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{item_id}", response_model=InventoryItemResponse)
async def get_item(item_id: UUID, db: DBSession):
    result = await db.execute(select(InventoryItem).where(InventoryItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.post("/", response_model=InventoryItemResponse, status_code=201)
async def create_item(payload: InventoryItemCreate, db: DBSession):
    item = InventoryItem(**payload.model_dump())
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=InventoryItemResponse)
async def update_item(item_id: UUID, payload: InventoryItemUpdate, db: DBSession):
    result = await db.execute(select(InventoryItem).where(InventoryItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await db.flush()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_item(item_id: UUID, db: DBSession):
    result = await db.execute(select(InventoryItem).where(InventoryItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
