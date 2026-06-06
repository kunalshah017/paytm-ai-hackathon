import csv
from pathlib import Path

_HSN_DATA: list[dict] = []
_LOADED = False

# Category keywords → HSN code mapping for common FMCG products
CATEGORY_HSN_MAP: dict[str, dict] = {
    # Dairy
    "milk": {"hsn": "04012000", "description": "Milk", "gst": 5},
    "butter": {"hsn": "04051000", "description": "Butter", "gst": 12},
    "ghee": {"hsn": "04059010", "description": "Butter oil / Ghee", "gst": 12},
    "cheese": {"hsn": "04061000", "description": "Fresh cheese (paneer)", "gst": 12},
    "paneer": {"hsn": "04061000", "description": "Fresh cheese (paneer)", "gst": 12},
    "yogurt": {"hsn": "04032000", "description": "Yogurt", "gst": 5},
    "curd": {"hsn": "04031000", "description": "Buttermilk/Yogurt", "gst": 5},
    "honey": {"hsn": "04090000", "description": "Natural honey", "gst": 5},
    # Tea & Coffee
    "tea": {"hsn": "09024020", "description": "Black tea", "gst": 5},
    "green tea": {"hsn": "09021010", "description": "Green tea", "gst": 5},
    "coffee": {"hsn": "09012100", "description": "Roasted coffee", "gst": 5},
    # Spices
    "turmeric": {"hsn": "09103010", "description": "Turmeric", "gst": 5},
    "pepper": {"hsn": "09041130", "description": "Black pepper", "gst": 5},
    "cumin": {"hsn": "09093111", "description": "Cumin seeds", "gst": 5},
    "spice": {"hsn": "09105000", "description": "Curry/spice mixes", "gst": 5},
    "masala": {"hsn": "09105000", "description": "Curry/spice mixes", "gst": 5},
    # Cereals & Flour
    "rice": {"hsn": "10063020", "description": "Rice", "gst": 5},
    "basmati": {"hsn": "10063020", "description": "Basmati rice", "gst": 5},
    "wheat": {"hsn": "10019020", "description": "Wheat", "gst": 5},
    "atta": {"hsn": "11010000", "description": "Wheat flour (Atta)", "gst": 5},
    "flour": {"hsn": "11010000", "description": "Wheat/Meslin flour", "gst": 5},
    "oats": {"hsn": "11041200", "description": "Rolled oats", "gst": 5},
    "maida": {"hsn": "11010000", "description": "Wheat flour", "gst": 5},
    # Edible Oils
    "sunflower oil": {"hsn": "15121110", "description": "Sunflower seed oil", "gst": 5},
    "mustard oil": {"hsn": "15149920", "description": "Mustard oil", "gst": 5},
    "coconut oil": {"hsn": "15131100", "description": "Coconut oil", "gst": 5},
    "groundnut oil": {"hsn": "15081000", "description": "Groundnut oil", "gst": 5},
    "olive oil": {"hsn": "15092000", "description": "Olive oil", "gst": 5},
    "palm oil": {"hsn": "15111000", "description": "Palm oil", "gst": 5},
    "soybean oil": {"hsn": "15071000", "description": "Soybean oil", "gst": 5},
    "edible oil": {"hsn": "15171000", "description": "Edible oil", "gst": 5},
    # Sugar
    "sugar": {"hsn": "17011410", "description": "Sugar", "gst": 5},
    "jaggery": {"hsn": "17011200", "description": "Jaggery", "gst": 5},
    # Noodles, Pasta, Bakery
    "noodle": {"hsn": "19021900", "description": "Noodles/Pasta", "gst": 12},
    "instant noodle": {"hsn": "19023010", "description": "Instant noodles", "gst": 18},
    "pasta": {"hsn": "19021900", "description": "Pasta", "gst": 12},
    "biscuit": {"hsn": "19059020", "description": "Biscuits", "gst": 18},
    "bread": {"hsn": "19054000", "description": "Rusks/toasted bread", "gst": 5},
    "cake": {"hsn": "19059010", "description": "Pastries and cakes", "gst": 18},
    "rusk": {"hsn": "19054000", "description": "Rusks", "gst": 5},
    # Pickles, Sauces
    "pickle": {"hsn": "20011000", "description": "Pickled vegetables", "gst": 12},
    "ketchup": {"hsn": "21032000", "description": "Tomato ketchup/sauce", "gst": 12},
    "sauce": {"hsn": "21032000", "description": "Sauce", "gst": 12},
    "jam": {"hsn": "20071000", "description": "Jams, jellies", "gst": 12},
    # Beverages
    "mineral water": {"hsn": "22011010", "description": "Mineral water", "gst": 18},
    "soft drink": {"hsn": "22021010", "description": "Aerated drinks", "gst": 28},
    "cola": {"hsn": "22021010", "description": "Aerated drinks", "gst": 28},
    "juice": {"hsn": "20098910", "description": "Fruit juice", "gst": 12},
    # Soap & Detergent
    "soap": {"hsn": "34011110", "description": "Soap bars (toilet)", "gst": 18},
    "detergent": {"hsn": "34022090", "description": "Detergent", "gst": 18},
    "shampoo": {"hsn": "33051020", "description": "Shampoo", "gst": 18},
    "toothpaste": {"hsn": "33061010", "description": "Toothpaste", "gst": 12},
    # Snacks
    "chips": {"hsn": "21069099", "description": "Food preparations (snacks)", "gst": 12},
    "snack": {"hsn": "21069099", "description": "Food preparations (snacks)", "gst": 12},
    "namkeen": {"hsn": "21069099", "description": "Namkeen/snacks", "gst": 12},
    # Chocolate
    "chocolate": {"hsn": "18069010", "description": "Chocolate products", "gst": 18},
    # Dals & Pulses
    "dal": {"hsn": "07139090", "description": "Pulses/Lentils", "gst": 5},
    "lentil": {"hsn": "07139090", "description": "Pulses/Lentils", "gst": 5},
    "pulse": {"hsn": "07139090", "description": "Pulses/Lentils", "gst": 5},
    "chana": {"hsn": "07132000", "description": "Chickpeas", "gst": 5},
    # Salt
    "salt": {"hsn": "25010010", "description": "Common salt", "gst": 5},
    # Personal Care
    "talc": {"hsn": "33049910", "description": "Talcum powder", "gst": 18},
    "talcum": {"hsn": "33049910", "description": "Talcum powder", "gst": 18},
    "powder": {"hsn": "33049910", "description": "Face/body powder", "gst": 18},
    "cream": {"hsn": "33049910", "description": "Face cream/skin care", "gst": 18},
    "lotion": {"hsn": "33049910", "description": "Body lotion", "gst": 18},
    "deodorant": {"hsn": "33072000", "description": "Deodorants", "gst": 18},
    "perfume": {"hsn": "33030010", "description": "Perfume/eau de toilette", "gst": 18},
    "hair oil": {"hsn": "33059010", "description": "Hair oil", "gst": 18},
    "face wash": {"hsn": "33049910", "description": "Face wash", "gst": 18},
    # Household
    "mosquito": {"hsn": "38089110", "description": "Insecticides (household)", "gst": 18},
    "agarbatti": {"hsn": "33074100", "description": "Agarbatti/incense", "gst": 5},
    "incense": {"hsn": "33074100", "description": "Agarbatti/incense", "gst": 5},
    "matchbox": {"hsn": "36050010", "description": "Matches", "gst": 12},
}


def _load_hsn_data():
    global _HSN_DATA, _LOADED
    if _LOADED:
        return

    csv_path = Path(__file__).parent.parent / "data" / "india-hsn-2026.csv"
    if not csv_path.exists():
        _LOADED = True
        return

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            _HSN_DATA.append({
                "hsn": row["hsn"],
                "description": row["description"],
                "gst": int(float(row["igst_pct"])) if row["igst_pct"] else 0,
            })
    _LOADED = True


def search_hsn(query: str, limit: int = 10) -> list[dict]:
    """Search HSN codes by keyword in description or by HSN code prefix."""
    _load_hsn_data()

    query_lower = query.lower().strip()

    # If query is numeric, search by HSN code prefix
    if query_lower.isdigit():
        results = [
            item for item in _HSN_DATA
            if item["hsn"].startswith(query_lower)
        ]
        return results[:limit]

    # Search by keywords in description
    keywords = query_lower.split()
    results = []
    for item in _HSN_DATA:
        desc_lower = item["description"].lower()
        if all(kw in desc_lower for kw in keywords):
            results.append(item)
            if len(results) >= limit:
                break

    return results


def get_hsn_for_category(category: str, product_name: str = "") -> dict | None:
    """Get HSN code from product category or name using the mapping."""
    search_text = f"{category} {product_name}".lower()

    # Try longer phrases first (more specific)
    sorted_keys = sorted(CATEGORY_HSN_MAP.keys(), key=len, reverse=True)
    for key in sorted_keys:
        if key in search_text:
            return CATEGORY_HSN_MAP[key]

    # Fallback: search the full database only if category has meaningful content
    if category and len(category) > 2:
        results = search_hsn(category, limit=1)
        if results:
            return results[0]

    return None
