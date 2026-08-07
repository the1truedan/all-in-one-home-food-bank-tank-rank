"""Optional Tandoor Recipes HTTP adapter (clean rewrite)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


class TandoorAdapter:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        *,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = (base_url or os.environ.get("TANDOOR_URL") or "").rstrip("/")
        self.api_key = api_key or os.environ.get("TANDOOR_API_KEY") or ""
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
                "Authorization": f"Bearer {self.api_key}",
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
            return {"ok": False, "reason": "missing TANDOOR_URL or TANDOOR_API_KEY"}
        data = self._get("/api/recipe/")
        if data is None:
            return {"ok": False, "reason": "request_failed"}
        if isinstance(data, dict) and "results" in data:
            return {"ok": True, "count": len(data.get("results") or [])}
        if isinstance(data, list):
            return {"ok": True, "count": len(data)}
        return {"ok": True, "shape": type(data).__name__}

    def fetch_recipes(self) -> List[dict]:
        data = self._get("/api/recipe/")
        if data is None:
            return []
        rows = data.get("results") if isinstance(data, dict) else data
        if not isinstance(rows, list):
            return []
        out: List[dict] = []
        for r in rows:
            rid = str(r.get("id") or "")
            title = str(r.get("name") or rid)
            ings: List[str] = []
            # Tandoor often nests steps → ingredients; detail fetch optional
            for step in r.get("steps") or []:
                for ing in step.get("ingredients") or []:
                    food = ing.get("food") or {}
                    name = food.get("name") or ing.get("note") or ""
                    if name:
                        ings.append(str(name))
            out.append(
                {
                    "id": rid,
                    "title": title,
                    "ingredients": ings,
                    "source": "tandoor",
                    "metadata": {"tandoor": True},
                }
            )
        return out
