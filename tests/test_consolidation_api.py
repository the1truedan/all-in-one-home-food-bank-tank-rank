"""Public package surface stays small (consolidation contract)."""

from __future__ import annotations

import home_food_tank_rank as h


def test_public_exports() -> None:
    for name in (
        "Inventory",
        "RecipeMatcher",
        "TankRank",
        "RestockPlanner",
        "StockItem",
        "FoodLocation",
        "lookup_barcode",
    ):
        assert hasattr(h, name)


def test_version() -> None:
    assert h.__version__ == "0.1.0"
