from dotenv import find_dotenv
from dotenv import load_dotenv
import os 

from fastapi import APIRouter, Request, Response
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from collections import defaultdict
load_dotenv(find_dotenv())

router = APIRouter()

# ── Conversation history (in-memory, replace with Redis for production) ──────
_history: dict[str, list] = defaultdict(list)

def get_history(mobile: str) -> list:
    return _history[mobile][-10:]  # last 5 turns (10 messages)

def save_history(mobile: str, human: str, ai: str):
    _history[mobile].extend([
        HumanMessage(content=human),
        AIMessage(content=ai)
    ])
    if len(_history[mobile]) > 40:
        _history[mobile] = _history[mobile][-40:]

# ── Sarvam LLM ────────────────────────────────────────────────────────────────
llm = ChatOpenAI(
    model="sarvam-30b",            #  use sarvam-30b (fast) or sarvam-105b (reasoning)
    api_key=os.getenv("SARVAM_API_KEY"),
    base_url="https://api.sarvam.ai/v1",
    temperature=0.3,               # lower = more consistent for commerce tasks
)

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a smart shopping assistant for a local Indian shop, \
operating over WhatsApp on behalf of the shopkeeper.

─── LANGUAGE ───
Detect the language of every message and reply in that EXACT language and script.
Never switch languages unless the customer switches first.
Never transliterate — always use the native script.

Supported languages and their scripts:
- Hindi        → Devanagari script    (हिन्दी)
- Bengali      → Bengali script       (বাংলা)
- Gujarati     → Gujarati script      (ગુજરાતી)
- Kannada      → Kannada script       (ಕನ್ನಡ)
- Malayalam    → Malayalam script     (മലയാളം)
- Marathi      → Devanagari script    (मराठी)
- Odia         → Odia script          (ଓଡ଼ିଆ)
- Punjabi      → Gurmukhi script      (ਪੰਜਾਬੀ)
- Tamil        → Tamil script         (தமிழ்)
- Telugu       → Telugu script        (తెలుగు)
- English      → Latin script         (English)
- Hinglish     → Latin + Devanagari mixed → reply in Hinglish

─── WHATSAPP FORMATTING ───
- Maximum 2 sentences per paragraph. Add a blank line between paragraphs.
- Use *bold* for product names and prices.
- Use _italics_ for important notes or warnings.
- Never use markdown headers (#, ##). Never use HTML.
- For item lists use plain dashes: - Item ₹price

─── BEHAVIOUR ───
- Be warm but brief. No filler phrases like "I'd be happy to help" or "Great question!".
- Always confirm the customer's order back to them before asking for payment.
- If a product is out of stock, suggest the nearest alternative from inventory.
- Never make up prices or products. Only use what is in the inventory tools.
- If you cannot help, say so in one sentence and offer to connect the customer to the shopkeeper.

─── COMMERCE FLOW ───
1. Customer asks about products → call query_inventory tool
2. Customer wants to buy → call create_draft_order tool, confirm items + total
3. Customer confirms → call place_order tool, then generate_payment_link tool
4. Share the payment link clearly with the amount
5. After payment → confirm with get_order_status tool

─── EXAMPLES ───
Good reply:
"*Basmati Rice (5kg)* - ₹320 available hai. \
Kya aap isko cart mein add karein?"

Bad reply:
"I would be happy to assist you today! Let me check our inventory database for you..."
"""

# ── Prompt template ───────────────────────────────────────────────────────────
prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder("chat_history", optional=True),
    ("human", "{user_input}"),
])

chain = prompt | llm

# ── Webhook ───────────────────────────────────────────────────────────────────
@router.post("/whatsapp")
async def twilio_webhook(request: Request):
    form_data = await request.form()
    incoming_msg = form_data.get("Body", "").strip()
    customer_mobile = form_data.get("From", "").replace("whatsapp:", "")

    if not incoming_msg:
        return Response(
            content=_twiml("Aapka message blank tha. Kuch poochiye! 😊"),
            media_type="application/xml"
        )

    try:
        history = get_history(customer_mobile)
        ai_response = await chain.ainvoke({
            "user_input": incoming_msg,
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


def _twiml(message: str) -> str:
    """Wrap a message string in Twilio TwiML XML."""
    # Escape XML special characters
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