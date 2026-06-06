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


async def _fetch_images_from_bing(query: str) -> list[str]:
    """Search Bing Images for product photos (fallback)."""
    try:
        from urllib.parse import unquote

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://www.bing.com/images/async",
                params={
                    "q": query,
                    "first": "0",
                    "count": "5",
                    "scenario": "ImageBasicHover",
                    "datsrc": "I",
                    "layout": "RowBased",
                },
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                },
            )
        if resp.status_code != 200:
            return []

        murls = re.findall(r'murl&quot;:&quot;(https?://[^&]+)&quot;', resp.text)
        return [unquote(url) for url in murls[:5]]
    except Exception:
        return []


async def _fetch_images_from_atozmart(product_name: str, full_name: str = "", barcode: str = "") -> list[str]:
    """Fetch product images from atozmart.co — by barcode (302 redirect) or name search."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            # Try barcode search first — redirects directly to product page
            if barcode:
                resp = await client.get(
                    "https://www.atozmart.co/",
                    params={"s": barcode, "post_type": "product", "dgwt_wcas": "1"},
                    headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
                )
                if resp.status_code == 200 and "/product/" in str(resp.url):
                    soup = BeautifulSoup(resp.text, "lxml")
                    images: list[str] = []
                    for img in soup.select(".woocommerce-product-gallery img, .wp-post-image"):
                        src = img.get("data-large_image") or img.get("data-src") or img.get("src", "")
                        if src and "atozmart.co" in src:
                            full_url = re.sub(r"-\d+x\d+(\.\w+)$", r"\1", src)
                            if full_url not in images:
                                images.append(full_url)
                    if images:
                        return images

            # Fallback: name-based AJAX search
            resp = await client.get(
                "https://www.atozmart.co/",
                params={"wc-ajax": "dgwt_wcas_ajax_search", "s": product_name},
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": "https://www.atozmart.co/",
                },
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            suggestions = [s for s in data.get("suggestions", []) if s.get("type") == "product"]
            if not suggestions:
                return []

            # Pick best match by weight
            best = suggestions[0]
            if full_name and len(suggestions) > 1:
                weight_match = re.search(r"(\d+)\s*(gm|g|kg|ml|l)", full_name, re.IGNORECASE)
                if weight_match:
                    weight = weight_match.group(1)
                    for s in suggestions:
                        if weight in s.get("value", ""):
                            best = s
                            break

            thumb_html = best.get("thumb_html", "")
            src_match = re.search(r'src="([^"]+)"', thumb_html)
            if src_match:
                thumb_url = src_match.group(1)
                full_url = re.sub(r"-\d+x\d+(\.\w+)$", r"\1", thumb_url)
                return [full_url]

        return []
    except Exception:
        return []


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
    attributes = (off_data or {}).get("attributes", {})

    # Get images: atozmart + Bing for product photos, plus Open Food Facts
    # Strip weight/quantity from name for better search
    search_name = re.sub(r"\d+\s*(gm|g|kg|ml|l|ltr)\b", "", name, flags=re.IGNORECASE).strip()
    images = await _fetch_images_from_atozmart(search_name, full_name=name, barcode=barcode)
    # Append Open Food Facts images if available
    off_images = (off_data or {}).get("images", [])
    for img in off_images:
        if img not in images:
            images.append(img)

    # HSN code lookup from category/product name
    from app.services.hsn_lookup import get_hsn_for_category
    from app.schemas.barcode import HsnInfo

    category = attributes.get("Category", "")
    hsn_data = get_hsn_for_category(category, name)
    hsn_info = HsnInfo(**hsn_data) if hsn_data else None

    return ProductInfo(
        barcode=barcode,
        name=name,
        barcode_format="",
        mrp=mrp,
        hsn=hsn_info,
        images=images,
        attributes=attributes,
    )
