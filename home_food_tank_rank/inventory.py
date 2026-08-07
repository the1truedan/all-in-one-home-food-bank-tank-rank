"""Consolidated home inventory — fridge / freezer / cabinet / spice / pantry.

Folds monorepo ideas from:
  agents/marv/marv_inventory.py
  tools/shopping/grocery_inventory.py
  tools/shopping/inventory_manager.py
  tools/caregiving/photo_inventory.py (scan is a future adapter, not core)
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Union

from home_food_tank_rank.models import FoodLocation, StockItem
from home_food_tank_rank.store import Store


class Inventory:
    """Local stock SoR with optional remote adapter sync (read/merge)."""

    def __init__(self, db_path: Union[Path, str]) -> None:
        self.store = Store(db_path)

    def put(
        self,
        name: str,
        quantity: float,
        location: Union[str, FoodLocation] = FoodLocation.PANTRY,
        *,
        unit: str = "ea",
        barcode: Optional[str] = None,
        expires_on: Optional[str] = None,
        low_threshold: float = 1.0,
        source: str = "local",
        metadata: Optional[dict] = None,
    ) -> StockItem:
        loc = (
            location
            if isinstance(location, FoodLocation)
            else FoodLocation.coerce(str(location))
        )
        item = StockItem(
            name=name.strip(),
            quantity=float(quantity),
            unit=unit,
            location=loc,
            barcode=barcode,
            expires_on=expires_on,
            low_threshold=low_threshold,
            source=source,
            metadata=metadata or {},
        )
        self.store.upsert_stock(item)
        return item

    def put_item(self, item: StockItem) -> StockItem:
        self.store.upsert_stock(item)
        return item

    def list(
        self, location: Optional[Union[str, FoodLocation]] = None
    ) -> List[StockItem]:
        loc: Optional[FoodLocation] = None
        if location is not None:
            loc = (
                location
                if isinstance(location, FoodLocation)
                else FoodLocation.coerce(str(location))
            )
        return self.store.list_stock(loc)

    def by_location(self) -> Dict[str, List[StockItem]]:
        out: Dict[str, List[StockItem]] = {loc.value: [] for loc in FoodLocation}
        for item in self.list():
            out.setdefault(item.location.value, []).append(item)
        return out

    def low_stock(self, threshold: Optional[float] = None) -> List[StockItem]:
        return self.store.low_stock(threshold)

    def find(self, name: str) -> List[StockItem]:
        return self.store.find_by_name(name)

    def on_hand_names(self, min_qty: float = 0.01) -> List[str]:
        return [i.name for i in self.list() if i.quantity >= min_qty]

    def load_fixture(self, items: List[dict]) -> int:
        stock = [StockItem.from_dict(d) for d in items]
        return self.store.replace_all_stock(stock)

    def summary(self) -> dict:
        items = self.list()
        by_loc = {loc.value: 0 for loc in FoodLocation}
        for i in items:
            by_loc[i.location.value] = by_loc.get(i.location.value, 0) + 1
        low = self.low_stock()
        return {
            "total_items": len(items),
            "by_location": by_loc,
            "low_stock_count": len(low),
            "low_stock": [i.to_dict() for i in low],
        }
