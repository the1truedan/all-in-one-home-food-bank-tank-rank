"""Shared domain models for stock, recipes, and post-meal tank-rank."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class FoodLocation(str, Enum):
    """Canonical home storage locations (replaces free-text location sprawl)."""

    FRIDGE = "fridge"
    FREEZER = "freezer"
    CABINET = "cabinet"
    SPICE = "spice"
    PANTRY = "pantry"
    OTHER = "other"

    @classmethod
    def coerce(cls, value: Optional[str]) -> "FoodLocation":
        if not value:
            return cls.OTHER
        key = value.strip().lower().replace(" ", "_")
        aliases = {
            "refrigerator": cls.FRIDGE,
            "fridge": cls.FRIDGE,
            "freezer": cls.FREEZER,
            "cabinet": cls.CABINET,
            "cupboard": cls.CABINET,
            "spice": cls.SPICE,
            "spices": cls.SPICE,
            "pantry": cls.PANTRY,
            "foodbank": cls.PANTRY,
            "food_bank": cls.PANTRY,
        }
        if key in aliases:
            return aliases[key]
        try:
            return cls(key)
        except ValueError:
            return cls.OTHER


@dataclass
class StockItem:
    name: str
    quantity: float = 0.0
    unit: str = "ea"
    location: FoodLocation = FoodLocation.PANTRY
    barcode: Optional[str] = None
    expires_on: Optional[str] = None  # ISO date YYYY-MM-DD
    low_threshold: float = 1.0
    source: str = "local"  # local | grocy | barcode | receipt
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_low(self) -> bool:
        # Match M.A.R.V. restock semantics: alert only when strictly below threshold.
        return self.quantity < self.low_threshold

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["location"] = self.location.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StockItem":
        loc = data.get("location", FoodLocation.PANTRY)
        if not isinstance(loc, FoodLocation):
            loc = FoodLocation.coerce(str(loc) if loc is not None else None)
        return cls(
            name=str(data["name"]),
            quantity=float(data.get("quantity", 0) or 0),
            unit=str(data.get("unit") or "ea"),
            location=loc,
            barcode=data.get("barcode"),
            expires_on=data.get("expires_on"),
            low_threshold=float(data.get("low_threshold", 1.0) or 1.0),
            source=str(data.get("source") or "local"),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class RecipeCandidate:
    recipe_id: str
    title: str
    ingredients: List[str]
    source: str = "fixture"  # fixture | tandoor | grocy
    matched: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    cover_ratio: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MealAttempt:
    recipe_id: str
    recipe_title: str
    cooked_at: str  # ISO datetime
    locations_used: List[str] = field(default_factory=list)
    missing_items: List[str] = field(default_factory=list)
    attempt_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MealReview:
    attempt_id: str
    recipe_id: str
    score: int  # 1–5
    mark_avoid: bool = False
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    reviewed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        if self.score < 1 or self.score > 5:
            raise ValueError("score must be 1–5")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
