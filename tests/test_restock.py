from __future__ import annotations

from home_food_tank_rank.models import FoodLocation, StockItem
from home_food_tank_rank.restock import RestockPlanner


def test_restock_and_food_bank_hitl() -> None:
    low = [
        StockItem(name="milk", quantity=0.2, location=FoodLocation.FRIDGE),
        StockItem(name="paprika", quantity=0, location=FoodLocation.SPICE),
        StockItem(name="bread", quantity=0, location=FoodLocation.PANTRY),
    ]
    planner = RestockPlanner(
        food_bank={"name": "Example Pantry", "appointment_url": "https://example.org"},
        low_stock_triggers_food_bank=3,
    )
    report = planner.full_report(low, recipe_gaps=["cheese"])
    assert len(report["shopping_list"]) >= 4
    assert report["food_bank"]["hitl_required"] is True
    assert report["prepare_only"] is True
    assert "cheese" in [x["item"] for x in report["shopping_list"]]
