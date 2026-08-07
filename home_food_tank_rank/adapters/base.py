"""Adapter protocols — Grocy/Tandoor implement these; core never depends on HTTP."""

from __future__ import annotations

from typing import List, Optional, Protocol, runtime_checkable

from home_food_tank_rank.models import StockItem


@runtime_checkable
class StockSource(Protocol):
    def fetch_stock(self) -> List[StockItem]:
        ...


@runtime_checkable
class RecipeSource(Protocol):
    def fetch_recipes(self) -> List[dict]:
        ...
