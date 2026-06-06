from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DBSession
from app.models.transaction import Transaction
from app.models.order import CustomerOrder
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/", response_model=list[TransactionResponse])
async def list_transactions(db: DBSession, status: str | None = None):
    stmt = select(Transaction).order_by(Transaction.created_at.desc())
    if status:
        stmt = stmt.where(Transaction.status == status)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{txn_id}", response_model=TransactionResponse)
async def get_transaction(txn_id: UUID, db: DBSession):
    result = await db.execute(select(Transaction).where(Transaction.id == txn_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn


@router.post("/", response_model=TransactionResponse, status_code=201)
async def create_transaction(payload: TransactionCreate, db: DBSession):
    # Verify order exists
    result = await db.execute(select(CustomerOrder).where(CustomerOrder.id == payload.order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=400, detail="Order not found")

    txn = Transaction(**payload.model_dump())
    db.add(txn)
    await db.flush()
    await db.refresh(txn)
    return txn


@router.patch("/{txn_id}", response_model=TransactionResponse)
async def update_transaction(txn_id: UUID, payload: TransactionUpdate, db: DBSession):
    result = await db.execute(select(Transaction).where(Transaction.id == txn_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(txn, field, value)

    await db.flush()
    await db.refresh(txn)
    return txn
