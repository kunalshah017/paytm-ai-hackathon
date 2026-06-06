from fastapi import APIRouter, HTTPException, Request, Response

from app.services.barcode_lookup import lookup_barcode
from app.services.hsn_lookup import search_hsn, get_hsn_for_category
from app.services.llm import run_agent, save_history
from app.api.inventory import router as inventory_router
from app.api.orders import router as orders_router
from app.api.transactions import router as transactions_router
from app.api.upload import router as upload_router

router = APIRouter()

router.include_router(inventory_router)
router.include_router(orders_router)
router.include_router(transactions_router)
router.include_router(upload_router)


@router.post("/whatsapp")
async def twilio_webhook(request: Request):
    form_data = await request.form()
    incoming_msg = form_data.get("Body", "").strip()
    customer_mobile = form_data.get("From", "").replace("whatsapp:", "")

    if not incoming_msg:
        return Response(
            content=_twiml("Kuch poochiye! 😊"),
            media_type="application/xml"
        )

    try:
        reply = await run_agent(incoming_msg, customer_mobile)
        save_history(customer_mobile, incoming_msg, reply)

    except Exception as e:
        print(f"[Sarvam error] {e}")
        reply = (
            "Abhi ek technical issue aa rahi hai. "
            "Thodi der mein dobara try karein. 🙏"
        )

    return Response(content=_twiml(reply), media_type="application/xml")


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


def _twiml(message: str) -> str:
    safe = (
        message
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message>{safe}</Message></Response>"
    )
