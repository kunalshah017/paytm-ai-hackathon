import os
import asyncio
import tempfile
import zipfile

import httpx
from sarvamai import SarvamAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from collections import defaultdict

from app.config import settings
from app.services.agent_tools import (
    query_inventory,
    list_all_inventory,
    create_order,
    generate_payment_link,
    get_order_status,
)

# ── Conversation history (in-memory) ──────────────────────────────────────────
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
    model="sarvam-105b",
    api_key=settings.sarvam_api_key,
    base_url="https://api.sarvam.ai/v1",
    temperature=0.3,
)

# ── Sarvam Vision client ──────────────────────────────────────────────────────
sarvam_client = SarvamAI(api_subscription_key=settings.sarvam_api_key)

# ── Language detection ────────────────────────────────────────────────────────
LANG_NAMES = {
    "hi-IN": "Hindi (Devanagari script)",
    "bn-IN": "Bengali (Bengali script)",
    "gu-IN": "Gujarati (Gujarati script)",
    "kn-IN": "Kannada (Kannada script)",
    "ml-IN": "Malayalam (Malayalam script)",
    "mr-IN": "Marathi (Devanagari script)",
    "od-IN": "Odia (Odia script)",
    "pa-IN": "Punjabi (Gurmukhi script)",
    "ta-IN": "Tamil (Tamil script)",
    "te-IN": "Telugu (Telugu script)",
    "en-IN": "English (Latin script)",
}


async def detect_language(text: str) -> tuple[str, str]:
    """
    Returns (language_code, language_name) e.g. ("hi-IN", "Hindi (Devanagari script)")
    Falls back to English if detection fails.
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.sarvam.ai/text-lid",
                headers={
                    "api-subscription-key": settings.sarvam_api_key,
                    "Content-Type": "application/json",
                },
                json={"input": text[:1000]},
                timeout=5.0,
            )
            resp.raise_for_status()
            data = resp.json()
            code = data.get("language_code", "en-IN")
            name = LANG_NAMES.get(code, f"language {code}")
            return code, name
    except Exception as e:
        print(f"[LID error] {e}")
        return "en-IN", "English (Latin script)"


async def build_input(text: str) -> str:
    """
    Detects the language of the message and prepends it as a tag so the LLM
    knows exactly which language and script to reply in.
    """
    lang_code, lang_name = await detect_language(text)
    return f"[DETECTED LANGUAGE: {lang_name}]\n\n{text}"


# ── Sarvam Vision — image text extraction ────────────────────────────────────
async def extract_image_text(media_url: str, media_type: str) -> str:
    """Download an image from Twilio and extract text using Sarvam Document Intelligence."""
    # 1. Download image from Twilio
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            media_url,
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            follow_redirects=True,
            timeout=15.0,
        )
        resp.raise_for_status()
        image_bytes = resp.content

    # 2. Derive correct file extension from MIME type
    ext_map = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".jpg",
        "application/pdf": ".pdf",
    }
    suffix = ext_map.get(media_type.lower(), ".jpg")

    # 3. Save image to temp file with correct extension
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    output_zip_path = tmp_path + "_output.zip"

    def run_sarvam_job() -> str:
        """
        All Sarvam SDK calls are synchronous (time.sleep polling internally).
        Run this entire block in a thread so we don't block the async event loop.
        """
        try:
            job = sarvam_client.document_intelligence.create_job(
                language="en-IN",
                output_format="md",
            )
            job.upload_file(tmp_path)
            job.start()
            status = job.wait_until_complete(timeout=120.0)

            if status.job_state == "Failed":
                return ""

            job.download_output(output_zip_path)

            with zipfile.ZipFile(output_zip_path) as zf:
                md_files = [f for f in zf.namelist() if f.endswith(".md")]
                if not md_files:
                    return ""
                return zf.read(md_files[0]).decode("utf-8").strip()

        finally:
            for path in (tmp_path, output_zip_path):
                try:
                    if os.path.exists(path):
                        os.unlink(path)
                except Exception as cleanup_err:
                    print(f"[Vision cleanup warning] {cleanup_err}")

    # 4. Run blocking SDK in a thread — keeps FastAPI's event loop healthy
    extracted = await asyncio.to_thread(run_sarvam_job)
    return extracted or "Image received but no readable text was found."

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

─── WHEN CUSTOMER SENDS AN IMAGE ───
- You will receive extracted text from Sarvam Vision at the top of the message.
- If it's a product label → identify the product and check inventory.
- If it's a handwritten list → read each item and check inventory for each one.
- If it's an invoice or bill → extract the items and help re-order them.
- Always confirm what you read from the image before acting on it.

─── COMMERCE FLOW ───
1. Customer asks about products → use search_inventory or show_all_items tool
2. Customer wants to buy → confirm items + total, then use place_order tool
3. After order is placed → use create_payment_link tool with the order_id and amount
4. Share the payment link with the customer (always share whatever link the tool returns)
5. Never say you cannot generate a link — always try the tool and share the result
6. If customer asks about order status → use check_order_status tool

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


# ── LangChain tools ──────────────────────────────────────────────────────────
@tool
async def search_inventory(query: str) -> str:
    """Search for products or services in the shop inventory by name keyword."""
    return await query_inventory(query)


@tool
async def show_all_items() -> str:
    """List all available products and services in the shop."""
    return await list_all_inventory()


@tool
async def place_order(customer_phone: str, items_json: str, customer_name: str = "") -> str:
    """Create an order for the customer. items_json must be a JSON array like [{"name": "Parle-G", "quantity": 2}]. Only call after customer confirms."""
    return await create_order(customer_phone, items_json, customer_name)


@tool
async def create_payment_link(order_id: str, amount: float) -> str:
    """Generate a Paytm payment link for a confirmed order. Returns the payment URL."""
    return await generate_payment_link(order_id, amount)


@tool
async def check_order_status(order_id: str) -> str:
    """Check the current status of an order and its payment status."""
    return await get_order_status(order_id)


tools = [search_inventory, show_all_items, place_order, create_payment_link, check_order_status]

# ── Agent chain with tools ────────────────────────────────────────────────────
llm_with_tools = llm.bind_tools(tools)

chain = prompt | llm_with_tools


async def run_agent(user_input: str, customer_mobile: str) -> str:
    """Run the agent with tool calling support."""
    from langchain_core.messages import ToolMessage

    history = get_history(customer_mobile)

    # Detect language and inject tag + customer phone context
    tagged_input = await build_input(user_input)
    augmented_input = (
        f"{tagged_input}\n\n"
        f"[SYSTEM NOTE: Customer's WhatsApp number is {customer_mobile}. "
        f"Use this for place_order. Never ask the customer for their phone number.]"
    )

    messages = prompt.format_messages(
        user_input=augmented_input,
        chat_history=history,
    )

    # Loop until we get a final text response (handle tool calls)
    max_iterations = 5
    for _ in range(max_iterations):
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        if not response.tool_calls:
            # Final response with no tool calls
            return response.content

        # Execute tool calls
        for tc in response.tool_calls:
            tool_fn = {t.name: t for t in tools}.get(tc["name"])
            if tool_fn:
                tool_result = await tool_fn.ainvoke(tc["args"])
                messages.append(ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tc["id"],
                ))

    # Fallback if max iterations reached
    return response.content if response.content else "Processing your request..."
