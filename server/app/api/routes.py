from fastapi import APIRouter, HTTPException, Request, Response, BackgroundTasks
import logging

from app.services.barcode_lookup import lookup_barcode
from app.services.hsn_lookup import search_hsn, get_hsn_for_category
from app.services.llm import run_agent, save_history, build_input, extract_image_text
from app.api.inventory import router as inventory_router
from app.api.orders import router as orders_router
from app.api.transactions import router as transactions_router
from app.api.upload import router as upload_router
from app.api.payments import router as payments_router

logger = logging.getLogger(__name__)

router = APIRouter()

router.include_router(inventory_router)
router.include_router(orders_router)
router.include_router(transactions_router)
router.include_router(upload_router)
router.include_router(payments_router)


@router.post("/whatsapp")
async def twilio_webhook(request: Request, background_tasks: BackgroundTasks):
    form_data = await request.form()
    incoming_msg = form_data.get("Body", "").strip()
    customer_mobile = form_data.get("From", "").replace("whatsapp:", "")

    logger.info(f"[WhatsApp] From: {customer_mobile} | Body: {incoming_msg[:100]!r}")

    # Handle image messages
    try:
        num_media = int(form_data.get("NumMedia", 0))
    except (ValueError, TypeError):
        num_media = 0

    logger.info(f"[WhatsApp] NumMedia: {num_media}")

    if num_media > 0:
        media_url = form_data.get("MediaUrl0", "")
        media_type = form_data.get("MediaContentType0", "image/jpeg")
        logger.info(f"[WhatsApp] Image received — URL: {media_url} | Type: {media_type}")
        # Image processing takes too long for Twilio's 15s webhook timeout.
        # Respond immediately with empty TwiML and process in background.
        background_tasks.add_task(
            _process_image_message, media_url, media_type, incoming_msg, customer_mobile
        )
        return Response(content=_twiml_empty(), media_type="application/xml")

    if not incoming_msg:
        logger.info("[WhatsApp] Empty message, sending default reply")
        return Response(
            content=_twiml("Kuch poochiye! 😊"),
            media_type="application/xml"
        )

    try:
        logger.info(f"[WhatsApp] Calling run_agent with input ({len(incoming_msg)} chars)")
        reply = await run_agent(incoming_msg, customer_mobile)
        logger.info(f"[WhatsApp] Agent reply ({len(reply)} chars): {reply[:200]!r}")
        save_history(customer_mobile, incoming_msg, reply)

    except Exception as e:
        logger.error(f"[Agent error] {e}", exc_info=True)
        reply = (
            "Abhi ek technical issue aa rahi hai. "
            "Thodi der mein dobara try karein. 🙏"
        )

    twiml_response = _twiml(reply)
    logger.info(f"[WhatsApp] Sending TwiML response ({len(twiml_response)} chars)")
    return Response(content=twiml_response, media_type="application/xml")


async def _process_image_message(media_url: str, media_type: str, text: str, customer_mobile: str):
    """Background task: extract image text, run agent, send reply via Twilio API."""
    from twilio.rest import Client as TwilioClient
    from app.config import settings

    try:
        extracted = await extract_image_text(media_url, media_type)
        logger.info(f"[BG] Vision extracted ({len(extracted)} chars): {extracted[:200]!r}")
        incoming_msg = (
            f"[Customer sent an image. Sarvam Vision extracted:]\n"
            f"{extracted}\n\n"
            f"[Customer's text (if any):] {text or 'None'}"
        )
    except Exception as e:
        logger.error(f"[BG Vision error] {e}", exc_info=True)
        incoming_msg = text or "[Customer sent an image but it could not be processed.]"

    try:
        logger.info(f"[BG] Calling run_agent for {customer_mobile}")
        reply = await run_agent(incoming_msg, customer_mobile)
        logger.info(f"[BG] Agent reply ({len(reply)} chars): {reply[:200]!r}")
        save_history(customer_mobile, incoming_msg, reply)
    except Exception as e:
        logger.error(f"[BG Agent error] {e}", exc_info=True)
        reply = "Abhi ek technical issue aa rahi hai. Thodi der mein dobara try karein. 🙏"

    # Send reply via Twilio REST API
    try:
        twilio_client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
        twilio_client.messages.create(
            from_=settings.twilio_whatsapp_number,
            to=f"whatsapp:{customer_mobile}",
            body=reply,
        )
        logger.info(f"[BG] Sent reply to {customer_mobile} via Twilio API")
    except Exception as e:
        logger.error(f"[BG Twilio send error] {e}", exc_info=True)


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


def _twiml_empty() -> str:
    """Empty TwiML response — acknowledges the webhook without sending a message."""
    return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
