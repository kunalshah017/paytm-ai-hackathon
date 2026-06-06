from fastapi import APIRouter, HTTPException

from app.services.barcode_lookup import lookup_barcode
from app.services.hsn_lookup import search_hsn, get_hsn_for_category
from app.api.inventory import router as inventory_router
from app.api.orders import router as orders_router
from app.api.transactions import router as transactions_router
from app.api.upload import router as upload_router

router = APIRouter()

router.include_router(inventory_router)
router.include_router(orders_router)
router.include_router(transactions_router)
router.include_router(upload_router)


@router.get("/")
async def root():
    return {"message": "Paytm AI Hackathon API"}


@router.get("/barcode/{barcode}")
async def get_barcode_info(barcode: str):
    if not barcode.isdigit() or len(barcode) not in (8, 12, 13, 14):
        raise HTTPException(status_code=400, detail="Invalid barcode format")

    product = await lookup_barcode(barcode)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@router.get("/hsn/search")
async def hsn_search(q: str, limit: int = 10):
    if not q or len(q) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
    results = search_hsn(q, limit=min(limit, 50))
    return {"results": results, "total": len(results)}
