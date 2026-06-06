import re

import httpx
from bs4 import BeautifulSoup

from app.schemas.barcode import ProductInfo

BARCODE_LOOKUP_URL = "https://www.barcodelookup.com"
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


async def _fetch_from_barcodelookup(barcode: str) -> dict | None:
    """Fetch images and attributes from barcodelookup.com (has Cloudflare)."""
    try:
        from curl_cffi import requests as cffi_requests

        # Try multiple browser impersonations to bypass Cloudflare
        impersonations = ["chrome", "chrome110", "chrome120", "safari", "safari15_5", "edge99"]
        response = None
        for browser in impersonations:
            try:
                response = cffi_requests.get(
                    f"{BARCODE_LOOKUP_URL}/{barcode}",
                    impersonate=browser,
                    timeout=15,
                    headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Cache-Control": "no-cache",
                        "Pragma": "no-cache",
                    },
                )
                if response.status_code == 200:
                    break
            except Exception:
                continue

        if not response or response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "lxml")

        # Product name from h4 (fallback)
        name_el = soup.select_one("h4")
        name = name_el.get_text(strip=True) if name_el else None

        # Barcode format
        barcode_format = ""
        for label in soup.select(".product-text-label"):
            text = label.get_text(strip=True)
            if "Barcode Formats:" in text:
                barcode_format = text.replace("Barcode Formats:", "").strip()
                break

        # Product images
        images: list[str] = []
        seen_srcs: set[str] = set()
        for img in soup.find_all("img"):
            src = img.get("src", "")
            alt = img.get("alt", "")
            if src and "images.barcodelookup.com" in src and src not in seen_srcs:
                if "thumbnail" not in alt:
                    images.append(src)
                    seen_srcs.add(src)
        if not images:
            for img in soup.find_all("img"):
                src = img.get("src", "")
                if src and "images.barcodelookup.com" in src and src not in seen_srcs:
                    images.append(src)
                    seen_srcs.add(src)

        # Attributes
        attributes: dict[str, str] = {}
        for li in soup.select("#product-attributes li"):
            text = li.get_text(strip=True)
            if ":" in text:
                key, value = text.split(":", 1)
                attributes[key.strip()] = value.strip()

        # Online stores
        stores: list[dict[str, str]] = []
        for link in soup.select("a[href*='amazon'], a[href*='walmart'], a[href*='ebay']"):
            store_text = link.get_text(strip=True)
            store_url = link.get("href", "")
            if store_text and store_url and not store_text.startswith("ADD"):
                if ":" in store_text and "$" in store_text:
                    parts = store_text.split(":", 1)
                    stores.append({"name": parts[0].strip(), "price": parts[1].strip(), "url": store_url})
                else:
                    stores.append({"name": store_text, "price": "", "url": store_url})

        return {
            "name": name,
            "barcode_format": barcode_format,
            "images": images,
            "attributes": attributes,
            "stores": stores,
        }
    except Exception:
        return None


async def lookup_barcode(barcode: str) -> ProductInfo | None:
    # Fetch from all sources
    sai_data = await _fetch_from_saisupermarket(barcode)
    off_data = await _fetch_from_openfoodfacts(barcode)
    barcode_data = await _fetch_from_barcodelookup(barcode)

    # Need at least one source to succeed
    if not sai_data and not barcode_data and not off_data:
        return None

    # Merge data: priority order for each field
    name = (
        (sai_data or {}).get("name")
        or (barcode_data or {}).get("name")
        or (off_data or {}).get("name")
        or "Unknown Product"
    )
    mrp = (sai_data or {}).get("mrp")
    barcode_format = (barcode_data or {}).get("barcode_format", "")

    # Images: prefer barcodelookup, fallback to openfoodfacts
    images = (barcode_data or {}).get("images", [])
    if not images:
        images = (off_data or {}).get("images", [])

    # Attributes: merge both sources
    attributes = (off_data or {}).get("attributes", {})
    attributes.update((barcode_data or {}).get("attributes", {}))

    stores = (barcode_data or {}).get("stores", [])

    return ProductInfo(
        barcode=barcode,
        name=name,
        barcode_format=barcode_format,
        mrp=mrp,
        images=images,
        attributes=attributes,
        stores=stores,
    )
