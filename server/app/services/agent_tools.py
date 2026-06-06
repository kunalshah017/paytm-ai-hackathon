import json
import uuid
from datetime import datetime

import httpx
from paytmchecksum import PaytmChecksum
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database.database import AsyncSessionLocal
from app.models.inventory_item import InventoryItem
from app.models.order import CustomerOrder, OrderItem
from app.models.transaction import Transaction


async def query_inventory(query: str) -> str:
    """Search inventory items by name. Returns available products and services."""
    async with AsyncSessionLocal() as session:
        stmt = select(InventoryItem).where(
            InventoryItem.name.ilike(f"%{query}%")
        ).limit(10)
        result = await session.execute(stmt)
        items = result.scalars().all()

        if not items:
            return f"No items found matching '{query}'. Try a different search term."

        lines = []
        for item in items:
            stock = f"Stock: {item.quantity}" if item.type == "product" and item.quantity is not None else "Available"
            lines.append(
                f"- {item.name} | ₹{item.price}/{item.unit} | {stock} | ID: {item.id}"
            )
        return "\n".join(lines)


async def list_all_inventory() -> str:
    """List all available inventory items."""
    async with AsyncSessionLocal() as session:
        stmt = select(InventoryItem).order_by(InventoryItem.name).limit(50)
        result = await session.execute(stmt)
        items = result.scalars().all()

        if not items:
            return "The inventory is empty. No products or services available."

        lines = []
        for item in items:
            stock = f"Stock: {item.quantity}" if item.type == "product" and item.quantity is not None else "Available"
            lines.append(
                f"- {item.name} | ₹{item.price}/{item.unit} | {stock}"
            )
        return "\n".join(lines)


async def create_order(customer_phone: str, items_json: str, customer_name: str = "") -> str:
    """Create an order. items_json is a JSON array like [{"name": "...", "quantity": 1}]."""
    try:
        requested_items = json.loads(items_json)
    except json.JSONDecodeError:
        return "Error: Invalid items format. Provide a JSON array."

    async with AsyncSessionLocal() as session:
        total = 0.0
        order_items = []

        for req in requested_items:
            name = req.get("name", "")
            qty = req.get("quantity", 1)

            stmt = select(InventoryItem).where(InventoryItem.name.ilike(f"%{name}%")).limit(1)
            result = await session.execute(stmt)
            inv_item = result.scalar_one_or_none()

            if not inv_item:
                return f"Error: Item '{name}' not found in inventory."

            if inv_item.type == "product" and inv_item.quantity is not None:
                if inv_item.quantity < qty:
                    return f"Error: Insufficient stock for '{inv_item.name}'. Available: {inv_item.quantity}"
                inv_item.quantity -= qty

            line_total = float(inv_item.price) * qty
            total += line_total

            order_items.append(OrderItem(
                inventory_item_id=inv_item.id,
                quantity=qty,
                price_at_purchase=float(inv_item.price),
            ))

        order = CustomerOrder(
            customer_name=customer_name or None,
            customer_phone=customer_phone or None,
            total_price=total,
            status="placed",
            items=order_items,
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)

        return (
            f"Order created successfully!\n"
            f"Order ID: {order.id}\n"
            f"Total: ₹{total:.2f}\n"
            f"Items: {len(order_items)}"
        )


async def generate_payment_link(order_id: str, amount: float) -> str:
    """Generate a Paytm payment link for an order."""
    mid = settings.paytm_merchant_id
    mkey = settings.paytm_merchant_key

    if not mid or not mkey:
        return "Error: Paytm credentials not configured."

    link_name = f"Order-{order_id[:8]}"
    link_id = f"LINK_{uuid.uuid4().hex[:12]}"

    base_url = (
        "https://securestage.paytmpayments.com"
        if settings.paytm_environment == "staging"
        else "https://secure.paytmpayments.com"
    )

    body = {
        "mid": mid,
        "linkType": "FIXED",
        "linkDescription": f"Payment for order {order_id[:8]}",
        "linkName": link_name,
        "amount": str(amount),
        "merchantRequestId": link_id,
        "customerContact": {},
    }

    body_json = json.dumps(body)
    signature = PaytmChecksum.generateSignature(body_json, mkey)

    payload = {
        "head": {
            "tokenType": "AES",
            "signature": signature,
        },
        "body": body,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{base_url}/link/create",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

    if resp.status_code != 200:
        return f"Error: Payment gateway returned status {resp.status_code}"

    data = resp.json()
    result_body = data.get("body", {})

    if result_body.get("resultInfo", {}).get("resultCode") == "200":
        short_url = result_body.get("shortUrl", "")
        long_url = result_body.get("longUrl", "")
        payment_url = short_url or long_url

        # Save transaction to DB
        async with AsyncSessionLocal() as session:
            txn = Transaction(
                order_id=uuid.UUID(order_id),
                amount=amount,
                payment_link=payment_url,
                status="pending",
                payment_method="paytm",
            )
            session.add(txn)
            await session.commit()

        return f"Payment link generated: {payment_url}\nAmount: ₹{amount:.2f}"
    else:
        error_msg = result_body.get("resultInfo", {}).get("resultMsg", "Unknown error")
        return f"Error creating payment link: {error_msg}"


async def get_order_status(order_id: str) -> str:
    """Check the status of an order."""
    async with AsyncSessionLocal() as session:
        stmt = (
            select(CustomerOrder)
            .options(selectinload(CustomerOrder.items))
            .where(CustomerOrder.id == uuid.UUID(order_id))
        )
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            return f"Order {order_id} not found."

        # Check for transaction
        txn_stmt = select(Transaction).where(Transaction.order_id == order.id)
        txn_result = await session.execute(txn_stmt)
        txn = txn_result.scalar_one_or_none()

        payment_status = txn.status if txn else "no payment initiated"

        return (
            f"Order: {order.id}\n"
            f"Status: {order.status}\n"
            f"Total: ₹{order.total_price}\n"
            f"Items: {len(order.items)}\n"
            f"Payment: {payment_status}"
        )


# Tool definitions for LangChain
TOOL_DEFINITIONS = [
    {
        "name": "query_inventory",
        "description": "Search inventory items by name keyword. Use this when customer asks about a product or service availability.",
        "func": query_inventory,
        "params": {"query": "str - search keyword for product/service name"},
    },
    {
        "name": "list_all_inventory",
        "description": "List all available products and services in the shop inventory.",
        "func": list_all_inventory,
        "params": {},
    },
    {
        "name": "create_order",
        "description": "Create a new order for a customer. Only call this after confirming items with the customer.",
        "func": create_order,
        "params": {
            "customer_phone": "str - customer WhatsApp number",
            "items_json": 'str - JSON array like [{"name": "Parle-G", "quantity": 2}]',
            "customer_name": "str - optional customer name",
        },
    },
    {
        "name": "generate_payment_link",
        "description": "Generate a Paytm payment link for an order. Call after order is created.",
        "func": generate_payment_link,
        "params": {
            "order_id": "str - UUID of the order",
            "amount": "float - total amount to charge",
        },
    },
    {
        "name": "get_order_status",
        "description": "Check the current status of an order and its payment.",
        "func": get_order_status,
        "params": {"order_id": "str - UUID of the order"},
    },
]
