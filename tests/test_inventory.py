from __future__ import annotations

from pathlib import Path

from home_food_tank_rank.inventory import Inventory
from home_food_tank_rank.models import FoodLocation


def test_put_and_location_summary(tmp_path: Path) -> None:
    inv = Inventory(tmp_path / "t.db")
    inv.put("eggs", 6, "fridge")
    inv.put("rice", 2, "pantry")
    inv.put("cumin", 1, FoodLocation.SPICE)
    s = inv.summary()
    assert s["total_items"] == 3
    assert s["by_location"]["fridge"] == 1
    assert s["by_location"]["pantry"] == 1
    assert s["by_location"]["spice"] == 1


def test_low_stock(tmp_path: Path) -> None:
    inv = Inventory(tmp_path / "t.db")
    inv.put("milk", 0.5, "fridge", low_threshold=1.0)
    inv.put("rice", 5, "pantry", low_threshold=1.0)
    low = inv.low_stock()
    assert len(low) == 1
    assert low[0].name == "milk"


def test_fixture_load(tmp_path: Path) -> None:
    inv = Inventory(tmp_path / "t.db")
    n = inv.load_fixture(
        [
            {"name": "a", "quantity": 1, "location": "cabinet"},
            {"name": "b", "quantity": 0, "location": "freezer", "low_threshold": 1},
        ]
    )
    assert n == 2
    assert inv.summary()["low_stock_count"] == 1
