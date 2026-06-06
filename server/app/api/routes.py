from fastapi import APIRouter, HTTPException, Request, Response

from app.services.barcode_lookup import lookup_barcode
from app.services.hsn_lookup import search_hsn, get_hsn_for_category
from app.services.llm import chain, get_history, save_history, build_input, extract_image_text

router = APIRouter()


@router.post("/whatsapp")
async def twilio_webhook(request: Request):
    form_data = await request.form()
    incoming_msg = form_data.get("Body", "").strip()
    customer_mobile = form_data.get("From", "").replace("whatsapp:", "")

    # Handle image messages — guard int() cast against malformed Twilio input
    try:
        num_media = int(form_data.get("NumMedia", 0))
    except (ValueError, TypeError):
        num_media = 0

    if num_media > 0:
        media_url  = form_data.get("MediaUrl0", "")
        media_type = form_data.get("MediaContentType0", "image/jpeg")
        try:
            extracted = await extract_image_text(media_url, media_type)
            incoming_msg = (
                f"[Customer sent an image. Sarvam Vision extracted:]\n"
                f"{extracted}\n\n"
                f"[Customer's text (if any):] {incoming_msg or 'None'}"
            )
        except Exception as e:
            print(f"[Vision error] {e}")
            incoming_msg = "[Customer sent an image but it could not be processed.]"

    if not incoming_msg:
        return Response(
            content=_twiml("Aapka message blank tha. Kuch poochiye! 😊"),
            media_type="application/xml"
        )

    try:
        tagged_input = await build_input(incoming_msg)
        history = get_history(customer_mobile)
        ai_response = await chain.ainvoke({
            "user_input": tagged_input,
            "chat_history": history,
        })
        reply = ai_response.content
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
