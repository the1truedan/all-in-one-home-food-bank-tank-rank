"""Optional remote backends — same StockItem / recipe dict shapes."""

from home_food_tank_rank.adapters.base import RecipeSource, StockSource
from home_food_tank_rank.adapters.local_sqlite import LocalStockSource

__all__ = ["LocalStockSource", "RecipeSource", "StockSource"]
