"""Barcode → product identity (OpenFoodFacts). Camera/USB hardware stays optional.

Folds: tools/shopping/barcode_scanner.py (drop eBay/Amazon label side-paths).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from home_food_tank_rank.models import FoodLocation, StockItem

OFF_URL = "https://world.openfoodfacts.org/api/v2/product/{code}.json"


def lookup_barcode(
    code: str,
    *,
    timeout: float = 10.0,
    user_agent: str = "home-food-tank-rank/0.1 (local caregiver inventory)",
) -> Optional[Dict[str, Any]]:
    """Return product dict or None. No network when code is empty."""
    code = (code or "").strip()
    if not code.isdigit() or len(code) < 8:
        return None
    req = urllib.request.Request(
        OFF_URL.format(code=code),
        headers={"User-Agent": user_agent, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None
    if data.get("status") != 1:
        return None
    product = data.get("product") or {}
    name = (
        product.get("product_name")
        or product.get("product_name_en")
        or product.get("generic_name")
        or f"UPC {code}"
    )
    return {
        "barcode": code,
        "name": str(name).strip() or f"UPC {code}",
        "brands": product.get("brands"),
        "quantity_label": product.get("quantity"),
        "categories": product.get("categories"),
        "nutriments": product.get("nutriments") or {},
        "source": "openfoodfacts",
    }


def stock_from_barcode(
    code: str,
    *,
    quantity: float = 1.0,
    location: FoodLocation = FoodLocation.PANTRY,
    lookup: bool = True,
    offline_name: Optional[str] = None,
) -> StockItem:
    """Build a StockItem from a UPC; offline_name used if lookup fails/disabled."""
    meta: Dict[str, Any] = {}
    name = offline_name or f"UPC {code}"
    if lookup:
        hit = lookup_barcode(code)
        if hit:
            name = hit["name"]
            meta = {k: hit[k] for k in ("brands", "quantity_label", "categories") if hit.get(k)}
    return StockItem(
        name=name,
        quantity=quantity,
        location=location,
        barcode=code,
        source="barcode",
        metadata=meta,
    )
