import json
import uuid
import time

import httpx
from fastapi import APIRouter, HTTPException
from paytmchecksum import PaytmChecksum
from sqlalchemy import select

from app.config import settings
from app.api.deps import DBSession
from app.models.order import CustomerOrder
from app.models.transaction import Transaction

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/initiate/{order_id}")
async def initiate_payment(order_id: str, db: DBSession):
    """Initiate a payment for an order. Returns txnToken + config for JS Checkout."""
    # Strip any trailing special characters from URL (LLM may add formatting)
    order_id = order_id.strip("_* ")

    # Validate order
    result = await db.execute(
        select(CustomerOrder).where(CustomerOrder.id == uuid.UUID(order_id))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    mid = settings.paytm_merchant_id
    mkey = settings.paytm_merchant_key
    paytm_order_id = f"PTMORD_{uuid.uuid4().hex[:12].upper()}"
    amount = f"{float(order.total_price):.2f}"

    base_url = (
        "https://securegw-stage.paytm.in"
        if settings.paytm_environment == "staging"
        else "https://securegw.paytm.in"
    )

    body = {
        "requestType": "Payment",
        "mid": mid,
        "websiteName": "WEBSTAGING" if settings.paytm_environment == "staging" else "DEFAULT",
        "orderId": paytm_order_id,
        "txnAmount": {
            "value": amount,
            "currency": "INR",
        },
        "userInfo": {
            "custId": str(order.id)[:20],
        },
        "callbackUrl": f"{base_url}/theia/paytmCallback?ORDER_ID={paytm_order_id}",
    }

    checksum = PaytmChecksum.generateSignature(json.dumps(body), mkey)
    payload = {"head": {"signature": checksum}, "body": body}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{base_url}/theia/api/v1/initiateTransaction?mid={mid}&orderId={paytm_order_id}",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

    data = resp.json()
    result_info = data.get("body", {}).get("resultInfo", {})

    if result_info.get("resultStatus") == "S":
        txn_token = data["body"]["txnToken"]

        # Save transaction
        txn = Transaction(
            order_id=order.id,
            amount=float(order.total_price),
            payment_link=f"{base_url}/theia/api/v1/showPaymentPage?mid={mid}&orderId={paytm_order_id}&txnToken={txn_token}",
            status="pending",
            payment_method="paytm",
        )
        db.add(txn)
        await db.flush()

        return {
            "success": True,
            "txnToken": txn_token,
            "orderId": paytm_order_id,
            "mid": mid,
            "amount": amount,
            "baseUrl": base_url,
        }
    else:
        # Paytm failed — return order details for UPI fallback
        return {
            "success": False,
            "error": result_info.get("resultMsg", "Payment gateway unavailable"),
            "orderId": str(order.id),
            "amount": amount,
            "fallback": "upi",
        }


@router.get("/status/{order_id}")
async def payment_status(order_id: str, db: DBSession):
    """Check payment status for an order."""
    result = await db.execute(
        select(Transaction).where(Transaction.order_id == uuid.UUID(order_id))
    )
    txn = result.scalar_one_or_none()
    if not txn:
        return {"status": "not_initiated", "order_id": order_id}

    return {
        "status": txn.status,
        "amount": float(txn.amount),
        "payment_method": txn.payment_method,
        "payment_link": txn.payment_link,
    }


@router.post("/confirm/{order_id}")
async def confirm_payment(order_id: str, db: DBSession):
    """Mark payment as confirmed (called after successful payment)."""
    order_uuid = uuid.UUID(order_id.strip("_* "))

    result = await db.execute(
        select(Transaction).where(Transaction.order_id == order_uuid)
    )
    txn = result.scalar_one_or_none()

    if not txn:
        # No transaction yet (PG initiation may have failed) — create one
        order_result = await db.execute(
            select(CustomerOrder).where(CustomerOrder.id == order_uuid)
        )
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        txn = Transaction(
            order_id=order.id,
            amount=float(order.total_price),
            status="paid",
            payment_method="paytm",
        )
        db.add(txn)
    else:
        txn.status = "paid"

    await db.flush()

    # Update order status
    order_result = await db.execute(
        select(CustomerOrder).where(CustomerOrder.id == order_uuid)
    )
    order = order_result.scalar_one_or_none()
    if order:
        order.status = "placed"

    return {"status": "paid", "order_id": order_id}
