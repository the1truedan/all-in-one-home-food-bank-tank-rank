"""Optional Tandoor Recipes HTTP adapter (clean rewrite)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


class TandoorAdapter:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        *,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = (base_url or os.environ.get("TANDOOR_URL") or "").rstrip("/")
        self.api_key = api_key or os.environ.get("TANDOOR_API_KEY") or ""
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    def _get(self, path: str) -> Any:
        if not self.configured:
            return None
        if path.startswith("http"):
            url = path
        else:
            url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
            return None

    def health(self) -> Dict[str, Any]:
        if not self.configured:
            return {"ok": False, "reason": "missing TANDOOR_URL or TANDOOR_API_KEY"}
        url = f"{self.base_url}/api/recipe/?page_size=1"
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, dict) and "count" in data:
                    return {
                        "ok": True,
                        "http_status": 200,
                        "recipe_count": data.get("count"),
                    }
                if isinstance(data, dict) and "results" in data:
                    return {"ok": True, "http_status": 200, "count": len(data.get("results") or [])}
                if isinstance(data, list):
                    return {"ok": True, "http_status": 200, "count": len(data)}
                return {"ok": True, "http_status": 200, "shape": type(data).__name__}
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                return {
                    "ok": True,
                    "http_status": e.code,
                    "auth": "rejected",
                    "note": "API reachable; check TANDOOR_API_KEY",
                }
            return {"ok": False, "reason": f"http_{e.code}"}
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            return {"ok": False, "reason": type(e).__name__}

    @staticmethod
    def _ingredients_from_recipe(payload: dict) -> List[str]:
        ings: List[str] = []
        seen = set()
        for step in payload.get("steps") or []:
            for ing in step.get("ingredients") or []:
                food = ing.get("food") or {}
                name = str(food.get("name") or food.get("full_name") or ing.get("note") or "").strip()
                if not name:
                    continue
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                ings.append(name)
        return ings

    def list_recipe_summaries(self, *, max_pages: int = 20, page_size: int = 50) -> List[dict]:
        """Paginate list endpoint (often without full ingredient steps)."""
        out: List[dict] = []
        path: Optional[str] = f"/api/recipe/?page_size={page_size}"
        pages = 0
        while path and pages < max_pages:
            pages += 1
            data = self._get(path)
            if data is None:
                break
            rows = data.get("results") if isinstance(data, dict) else data
            if not isinstance(rows, list):
                break
            out.extend(rows)
            nxt = data.get("next") if isinstance(data, dict) else None
            if not nxt:
                break
            if nxt.startswith("http"):
                # keep host; pass absolute to _get
                path = nxt
            else:
                path = nxt
        return out

    def fetch_recipe_detail(self, recipe_id: str | int) -> Optional[dict]:
        return self._get(f"/api/recipe/{recipe_id}/")

    def fetch_recipes(
        self,
        *,
        limit: int = 40,
        with_details: bool = True,
        max_list_pages: int = 5,
    ) -> List[dict]:
        """Fetch recipes; optionally hydrate ingredients via detail endpoint."""
        summaries = self.list_recipe_summaries(max_pages=max_list_pages)
        if limit > 0:
            summaries = summaries[:limit]
        out: List[dict] = []
        for r in summaries:
            rid = str(r.get("id") or "")
            title = str(r.get("name") or rid)
            ings: List[str] = []
            for step in r.get("steps") or []:
                for ing in step.get("ingredients") or []:
                    food = ing.get("food") or {}
                    name = food.get("name") or ing.get("note") or ""
                    if name:
                        ings.append(str(name))
            if with_details and not ings and rid:
                detail = self.fetch_recipe_detail(rid)
                if isinstance(detail, dict):
                    ings = self._ingredients_from_recipe(detail)
                    title = str(detail.get("name") or title)
            out.append(
                {
                    "id": rid,
                    "title": title,
                    "ingredients": ings,
                    "source": "tandoor",
                    "metadata": {
                        "tandoor": True,
                        "working_time": r.get("working_time"),
                        "rating": r.get("rating"),
                    },
                }
            )
        return out
