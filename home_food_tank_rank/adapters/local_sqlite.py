"""Local SQLite as StockSource (default)."""

from __future__ import annotations

from pathlib import Path
from typing import List, Union

from home_food_tank_rank.inventory import Inventory
from home_food_tank_rank.models import StockItem


class LocalStockSource:
    def __init__(self, db_path: Union[Path, str]) -> None:
        self.inventory = Inventory(db_path)

    def fetch_stock(self) -> List[StockItem]:
        return self.inventory.list()
