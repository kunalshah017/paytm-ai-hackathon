import logging
import re

import httpx
from bs4 import BeautifulSoup

from app.schemas.barcode import ProductInfo

logger = logging.getLogger(__name__)

SAI_SUPERMARKET_URL = "https://www.saisupermarket.in/product-detail.php"
OPEN_FOOD_FACTS_URL = "https://world.openfoodfacts.org/api/v2/product"


async def _fetch_from_openfoodfacts(barcode: str) -> dict | None:
    """Fetch product data from Open Food Facts API (free, no auth, no Cloudflare)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{OPEN_FOOD_FACTS_URL}/{barcode}.json")
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("status") != 1:
            return None

        product = data.get("product", {})
        name = product.get("product_name") or product.get("product_name_en") or None

        # Images
        images: list[str] = []
        if product.get("image_url"):
            images.append(product["image_url"])
        if product.get("image_front_url"):
            front = product["image_front_url"]
            if front not in images:
                images.append(front)

        # Attributes
        attributes: dict[str, str] = {}
        if product.get("brands"):
            attributes["Brand"] = product["brands"]
        if product.get("quantity"):
            attributes["Quantity"] = product["quantity"]
        if product.get("categories"):
            attributes["Category"] = product["categories"]
        if product.get("generic_name"):
            attributes["Type"] = product["generic_name"]

        return {"name": name, "images": images, "attributes": attributes}
    except Exception:
        return None


async def _fetch_from_saisupermarket(barcode: str) -> dict | None:
    """Fetch product name and MRP from saisupermarket.in (no bot protection)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(SAI_SUPERMARKET_URL, params={"mid": barcode})
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "lxml")

        # Product name from h2
        h2 = soup.select_one("h2")
        name = h2.get_text(strip=True) if h2 else None
        if not name:
            return None

        # MRP
        mrp = None
        for p in soup.find_all("p"):
            text = p.get_text()
            if "MRP" in text:
                mrp_match = re.search(r"MRP\s*:\s*([\d.]+)", text)
                mrp = mrp_match.group(1) if mrp_match else None
                break

        return {"name": name, "mrp": mrp}
    except Exception:
        return None


async def lookup_barcode(barcode: str) -> ProductInfo | None:
    # Fetch from both sources
    sai_data = await _fetch_from_saisupermarket(barcode)
    off_data = await _fetch_from_openfoodfacts(barcode)

    # Need at least one source to succeed
    if not sai_data and not off_data:
        return None

    # Merge data
    name = (
        (sai_data or {}).get("name")
        or (off_data or {}).get("name")
        or "Unknown Product"
    )
    mrp = (sai_data or {}).get("mrp")
    images = (off_data or {}).get("images", [])
    attributes = (off_data or {}).get("attributes", {})

    return ProductInfo(
        barcode=barcode,
        name=name,
        barcode_format="",
        mrp=mrp,
        images=images,
        attributes=attributes,
        stores=[],
    )
