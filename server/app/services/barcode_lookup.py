import re

import httpx
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

from app.schemas.barcode import ProductInfo

BARCODE_LOOKUP_URL = "https://www.barcodelookup.com"
SAI_SUPERMARKET_URL = "https://www.saisupermarket.in/product-detail.php"


async def _fetch_mrp(barcode: str) -> str | None:
    """Fetch MRP from saisupermarket.in."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(SAI_SUPERMARKET_URL, params={"mid": barcode})
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "lxml")
        for p in soup.find_all("p"):
            text = p.get_text()
            if "MRP" in text:
                mrp_match = re.search(r"MRP\s*:\s*([\d.]+)", text)
                return mrp_match.group(1) if mrp_match else None
    except Exception:
        pass
    return None


async def lookup_barcode(barcode: str) -> ProductInfo | None:
    response = cffi_requests.get(
        f"{BARCODE_LOOKUP_URL}/{barcode}",
        impersonate="chrome",
        timeout=15,
    )
    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, "lxml")

    # Product name from h4
    name_el = soup.select_one("h4")
    name = name_el.get_text(strip=True) if name_el else "Unknown Product"

    # Barcode format from product-text-label
    barcode_format = ""
    for label in soup.select(".product-text-label"):
        text = label.get_text(strip=True)
        if "Barcode Formats:" in text:
            barcode_format = text.replace("Barcode Formats:", "").strip()
            break

    # Product images - get unique srcs from imgs with product name in alt
    images: list[str] = []
    seen_srcs: set[str] = set()
    for img in soup.find_all("img"):
        src = img.get("src", "")
        alt = img.get("alt", "")
        if src and "images.barcodelookup.com" in src and src not in seen_srcs:
            if "thumbnail" not in alt:
                images.append(src)
                seen_srcs.add(src)
    # Add thumbnails if no main images found
    if not images:
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src and "images.barcodelookup.com" in src and src not in seen_srcs:
                images.append(src)
                seen_srcs.add(src)

    # Attributes from #product-attributes list
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
            # Split store name and price (format: "Amazon.com:$40.00")
            if ":" in store_text and "$" in store_text:
                parts = store_text.split(":", 1)
                stores.append({"name": parts[0].strip(), "price": parts[1].strip(), "url": store_url})
            else:
                stores.append({"name": store_text, "price": "", "url": store_url})

    # Fetch MRP from saisupermarket.in
    mrp = await _fetch_mrp(barcode)

    return ProductInfo(
        barcode=barcode,
        name=name,
        barcode_format=barcode_format,
        mrp=mrp,
        images=images,
        attributes=attributes,
        stores=stores,
    )
