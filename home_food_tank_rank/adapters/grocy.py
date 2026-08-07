"""Optional Grocy HTTP adapter (rewrite — not the broken monorepo dump).

Requires GROCY_URL + GROCY_API_KEY env or constructor args.
Uses stdlib urllib when requests is unavailable.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from home_food_tank_rank.models import FoodLocation, StockItem


class GrocyAdapter:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        *,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = (base_url or os.environ.get("GROCY_URL") or "").rstrip("/")
        self.api_key = api_key or os.environ.get("GROCY_API_KEY") or ""
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def _get(self, path: str) -> Any:
        if not self.configured:
            return None
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(
            url,
            headers={
                "GROCY-API-KEY": self.api_key,
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
            return None

    def health(self) -> Dict[str, Any]:
        if not self.configured:
            return {"ok": False, "reason": "missing GROCY_URL or GROCY_API_KEY"}
        # systeminfo is common; fall back to products list
        data = self._get("/api/system/info")
        if data is not None:
            return {"ok": True, "endpoint": "system/info", "data_keys": list(data)[:8] if isinstance(data, dict) else type(data).__name__}
        data = self._get("/api/objects/products")
        if data is not None:
            return {"ok": True, "endpoint": "objects/products", "count": len(data) if isinstance(data, list) else None}
        return {"ok": False, "reason": "request_failed"}

    def fetch_stock(self) -> List[StockItem]:
        """Best-effort map of Grocy stock entries → StockItem."""
        raw = self._get("/api/stock")
        if not isinstance(raw, list):
            # older/simple: products only with amount 0 placeholder
            products = self._get("/api/objects/products")
            if not isinstance(products, list):
                return []
            out: List[StockItem] = []
            for p in products:
                name = str(p.get("name") or p.get("id") or "product")
                out.append(
                    StockItem(
                        name=name,
                        quantity=0.0,
                        location=FoodLocation.PANTRY,
                        barcode=str(p.get("barcode") or "") or None,
                        source="grocy",
                        metadata={"grocy_product_id": p.get("id")},
                    )
                )
            return out
        out = []
        for row in raw:
            product = row.get("product") or {}
            name = str(
                product.get("name")
                or row.get("product_name")
                or row.get("product_id")
                or "item"
            )
            qty = float(row.get("amount") or row.get("amount_aggregated") or 0)
            loc_name = None
            if isinstance(row.get("location"), dict):
                loc_name = row["location"].get("name")
            out.append(
                StockItem(
                    name=name,
                    quantity=qty,
                    location=FoodLocation.coerce(loc_name),
                    barcode=str(product.get("barcode") or "") or None,
                    expires_on=row.get("best_before_date"),
                    source="grocy",
                    metadata={"raw_keys": list(row.keys())[:12]},
                )
            )
        return out

    def fetch_recipes(self) -> List[dict]:
        raw = self._get("/api/objects/recipes")
        if not isinstance(raw, list):
            return []
        recipes = []
        for r in raw:
            rid = str(r.get("id") or "")
            title = str(r.get("name") or rid)
            recipes.append(
                {
                    "id": rid,
                    "title": title,
                    "ingredients": [],  # positions require second call; fill later if needed
                    "source": "grocy",
                    "metadata": {"grocy": True},
                }
            )
        return recipes
