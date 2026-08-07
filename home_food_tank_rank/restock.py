"""Low stock → shopping list + optional food-bank HITL suggest.

Folds:
  tools/shopping/smart_grocery_list.py
  tools/shopping/shopping_list_optimizer.py
  tools/shopping/food_bank_manager.py
  (coupon circulars stay optional adapters — Flipp not required for core)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from home_food_tank_rank.models import StockItem


@dataclass
class RestockLine:
    item: str
    quantity_on_hand: float
    reason: str
    priority: str = "high"  # high | medium | low
    coupon_hint: str = "Check local circular / Flipp if available"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FoodBankHint:
    """Prepare-only: never auto-books appointments."""

    name: str
    notes: str = ""
    appointment_url: Optional[str] = None
    phone: Optional[str] = None
    low_stock_items: List[str] = field(default_factory=list)
    hitl_required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RestockPlanner:
    def __init__(
        self,
        *,
        food_bank: Optional[Dict[str, Any]] = None,
        low_stock_triggers_food_bank: int = 3,
    ) -> None:
        self.food_bank = food_bank or {}
        self.low_stock_triggers_food_bank = low_stock_triggers_food_bank

    def plan(
        self,
        low_items: Sequence[StockItem],
        *,
        recipe_gaps: Optional[Sequence[str]] = None,
        budget_cap: Optional[float] = None,
    ) -> List[RestockLine]:
        lines: List[RestockLine] = []
        for item in low_items:
            lines.append(
                RestockLine(
                    item=item.name,
                    quantity_on_hand=item.quantity,
                    reason="Low stock",
                    priority="high",
                    metadata={"location": item.location.value},
                )
            )
        for gap in recipe_gaps or []:
            if any(l.item.lower() == gap.lower() for l in lines):
                continue
            lines.append(
                RestockLine(
                    item=gap,
                    quantity_on_hand=0.0,
                    reason="Recipe gap",
                    priority="medium",
                )
            )
        # shopping_list_optimizer was a no-op reordering stub — keep stable priority sort
        order = {"high": 0, "medium": 1, "low": 2}
        lines.sort(key=lambda x: order.get(x.priority, 9))
        if budget_cap is not None:
            # Soft cap: mark lower priority lines; do not drop high
            for i, line in enumerate(lines):
                if i >= 15 and line.priority != "high":
                    line.priority = "low"
                    line.metadata["budget_cap"] = budget_cap
        return lines

    def food_bank_suggest(
        self, low_items: Sequence[StockItem]
    ) -> Optional[FoodBankHint]:
        if not self.food_bank:
            return None
        if len(list(low_items)) < self.low_stock_triggers_food_bank:
            return None
        return FoodBankHint(
            name=str(self.food_bank.get("name") or "Local food pantry"),
            notes=str(self.food_bank.get("notes") or ""),
            appointment_url=self.food_bank.get("appointment_url"),
            phone=self.food_bank.get("phone"),
            low_stock_items=[i.name for i in low_items][:12],
            hitl_required=True,
        )

    def full_report(
        self,
        low_items: Sequence[StockItem],
        *,
        recipe_gaps: Optional[Sequence[str]] = None,
    ) -> dict:
        plan = self.plan(low_items, recipe_gaps=recipe_gaps)
        hint = self.food_bank_suggest(low_items)
        return {
            "shopping_list": [p.to_dict() for p in plan],
            "food_bank": hint.to_dict() if hint else None,
            "prepare_only": True,
        }
