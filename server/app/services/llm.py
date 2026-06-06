from dotenv import find_dotenv
from dotenv import load_dotenv
import os
import httpx
from collections import defaultdict
# pyrefly: ignore [missing-import]
from sarvamai import SarvamAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
import asyncio
import tempfile
import zipfile


load_dotenv(find_dotenv())


# ── Sarvam clients ────────────────────────────────────────────────────────────
llm = ChatOpenAI(
    model="sarvam-105b",
    api_key=os.getenv("SARVAM_API_KEY"),
    base_url="https://api.sarvam.ai/v1",
    temperature=0.3,
)

sarvam_client = SarvamAI(
    api_subscription_key=os.getenv("SARVAM_API_KEY")
)

# ── Language code → human readable name ──────────────────────────────────────
LANG_NAMES = {
    "hi-IN":  "Hindi (Devanagari script)",
    "bn-IN":  "Bengali (Bengali script)",
    "gu-IN":  "Gujarati (Gujarati script)",
    "kn-IN":  "Kannada (Kannada script)",
    "ml-IN":  "Malayalam (Malayalam script)",
    "mr-IN":  "Marathi (Devanagari script)",
    "od-IN":  "Odia (Odia script)",
    "pa-IN":  "Punjabi (Gurmukhi script)",
    "ta-IN":  "Tamil (Tamil script)",
    "te-IN":  "Telugu (Telugu script)",
    "en-IN":  "English (Latin script)",
    # ur-IN not supported by /text-lid
}


# ── Step 1: Detect language using Sarvam LID API ─────────────────────────────
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
                    "api-subscription-key": os.getenv("SARVAM_API_KEY"),
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


# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a smart shopping assistant for a local Indian shop, \
operating over WhatsApp on behalf of the shopkeeper.

─── LANGUAGE — CRITICAL RULE ───
The customer's language has been detected and is injected at the top of every message as:
[DETECTED LANGUAGE: <name>]

You MUST reply ONLY in that exact language and script — no exceptions.
Do NOT mix languages. Do NOT reply in English unless the detected language is English.
Do NOT transliterate — always use the native script of the detected language.

─── WHATSAPP FORMATTING ───
- Maximum 2 sentences per paragraph. Add a blank line between paragraphs.
- Use *bold* for product names and prices.
- Use _italics_ for important notes or warnings.
- Never use markdown headers (#, ##). Never use HTML.
- For item lists use plain dashes: - Item ₹price

─── BEHAVIOUR ───
- Be warm but brief. No filler phrases like "I'd be happy to help".
- Always confirm the customer's order back to them before asking for payment.
- If a product is out of stock, suggest the nearest alternative from inventory.
- Never make up prices or products.
- If you cannot help, say so in one sentence and offer to connect to the shopkeeper.

─── WHEN CUSTOMER SENDS AN IMAGE ───
- You will receive extracted text from Sarvam Vision at the top of the message.
- If it's a product label → identify the product and check inventory.
- If it's a handwritten list → read each item and check inventory for each one.
- If it's an invoice or bill → extract the items and help re-order them.
- Always confirm what you read from the image before acting on it.

─── COMMERCE FLOW ───
1. Customer asks about products  → query inventory, reply with names + prices
2. Customer wants to buy         → confirm items + total price
3. Customer confirms             → generate payment link
4. Share the payment link clearly with the amount
5. After payment                 → confirm order status
"""

# ── Prompt template ───────────────────────────────────────────────────────────
prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder("chat_history", optional=True),
    ("human", "{user_input}"),
])

chain = prompt | llm

# ── Conversation history ──────────────────────────────────────────────────────
_history: dict[str, list] = defaultdict(list)

def get_history(mobile: str) -> list:
    return _history[mobile][-10:]

def save_history(mobile: str, human: str, ai: str):
    _history[mobile].extend([
        HumanMessage(content=human),
        AIMessage(content=ai),
    ])
    if len(_history[mobile]) > 40:
        _history[mobile] = _history[mobile][-40:]


# ── Step 2: Build message with language tag injected ─────────────────────────
async def build_input(text: str) -> str:
    """
    Detects the language of the message and prepends it as a tag so the LLM
    knows exactly which language and script to reply in.
    """
    lang_code, lang_name = await detect_language(text)
    return f"[DETECTED LANGUAGE: {lang_name}]\n\n{text}"


# ── Sarvam Vision ─────────────────────────────────────────────────────────────
async def extract_image_text(media_url: str, media_type: str) -> str:
    twilio_sid   = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")

    # 1. Download image from Twilio
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            media_url,
            auth=(twilio_sid, twilio_token),
            follow_redirects=True,
            timeout=15.0,
        )
        resp.raise_for_status()
        image_bytes = resp.content

    # 2. Derive correct file extension from MIME type
    ext_map = {
        "image/jpeg":      ".jpg",
        "image/jpg":       ".jpg",
        "image/png":       ".png",
        "image/webp":      ".jpg",
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
                language="hi-IN",
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