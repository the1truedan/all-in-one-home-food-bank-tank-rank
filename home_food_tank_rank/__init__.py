"""Home food bank + tank-rank — consolidated local-first inventory and meals.

Public surface is intentionally small. Tangential monorepo vibecode modules
(grocery_inventory, inventory_manager, meal_planner, adaptive_meal_planner,
smart_grocery_list, food_bank_manager, barcode_scanner, dual Grocy/Tandoor dumps)
fold into the modules below — see docs/CONSOLIDATION.md.
"""

from __future__ import annotations

from home_food_tank_rank.barcode import lookup_barcode
from home_food_tank_rank.inventory import Inventory
from home_food_tank_rank.models import (
    FoodLocation,
    MealAttempt,
    MealReview,
    RecipeCandidate,
    StockItem,
)
from home_food_tank_rank.recipes import RecipeMatcher
from home_food_tank_rank.restock import RestockPlanner
from home_food_tank_rank.tank_rank import TankRank

__version__ = "0.1.0"

__all__ = [
    "FoodLocation",
    "Inventory",
    "MealAttempt",
    "MealReview",
    "RecipeCandidate",
    "RecipeMatcher",
    "RestockPlanner",
    "StockItem",
    "TankRank",
    "lookup_barcode",
    "__version__",
]
