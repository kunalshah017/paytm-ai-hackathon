from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DBSession
from app.models.inventory_item import InventoryItem
from app.models.order import CustomerOrder, OrderItem
from app.schemas.order import OrderCreate, OrderResponse

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/", response_model=list[OrderResponse])
async def list_orders(db: DBSession, status: str | None = None):
    stmt = (
        select(CustomerOrder)
        .options(selectinload(CustomerOrder.items))
        .order_by(CustomerOrder.created_at.desc())
    )
    if status:
        stmt = stmt.where(CustomerOrder.status == status)
    result = await db.execute(stmt)
    orders = result.scalars().all()

    response = []
    for order in orders:
        order_dict = OrderResponse.model_validate(order).model_dump()
        # Enrich items with item name
        for i, oi in enumerate(order.items):
            inv_result = await db.execute(select(InventoryItem).where(InventoryItem.id == oi.inventory_item_id))
            inv = inv_result.scalar_one_or_none()
            order_dict["items"][i]["item_name"] = inv.name if inv else None
        response.append(order_dict)
    return response


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: UUID, db: DBSession):
    stmt = (
        select(CustomerOrder)
        .options(selectinload(CustomerOrder.items))
        .where(CustomerOrder.id == order_id)
    )
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(payload: OrderCreate, db: DBSession):
    total = 0.0
    order_items = []

    for item_req in payload.items:
        result = await db.execute(select(InventoryItem).where(InventoryItem.id == item_req.inventory_item_id))
        inv_item = result.scalar_one_or_none()
        if not inv_item:
            raise HTTPException(status_code=400, detail=f"Inventory item {item_req.inventory_item_id} not found")

        # Check stock for products
        if inv_item.type == "product":
            if inv_item.quantity is not None and inv_item.quantity < item_req.quantity:
                raise HTTPException(status_code=400, detail=f"Insufficient stock for {inv_item.name}")
            # Decrement stock
            if inv_item.quantity is not None:
                inv_item.quantity -= item_req.quantity

        line_total = float(inv_item.price) * item_req.quantity
        total += line_total

        order_items.append(OrderItem(
            inventory_item_id=item_req.inventory_item_id,
            quantity=item_req.quantity,
            price_at_purchase=float(inv_item.price),
        ))

    order = CustomerOrder(
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        total_price=total,
        status="placed",
        items=order_items,
    )
    db.add(order)
    await db.flush()
    await db.refresh(order, attribute_names=["items"])
    return order


@router.patch("/{order_id}/status")
async def update_order_status(order_id: UUID, status: str, db: DBSession):
    if status not in ("draft", "placed"):
        raise HTTPException(status_code=400, detail="Invalid status")
    result = await db.execute(select(CustomerOrder).where(CustomerOrder.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = status
    await db.flush()
    return {"status": order.status}
