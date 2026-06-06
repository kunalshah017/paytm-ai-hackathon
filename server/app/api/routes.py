from fastapi import APIRouter, HTTPException

from app.services.barcode_lookup import lookup_barcode

router = APIRouter()


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
