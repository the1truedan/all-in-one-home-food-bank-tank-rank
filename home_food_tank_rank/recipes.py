"""Recipe match against on-hand stock.

Folds:
  tools/shopping/meal_planner.py
  tools/caregiving/adaptive_meal_planner.py (planning half; ratings → tank_rank)
  tools/shopping/tandoor_api_client.search_recipes_by_ingredients
  tools/shopping/grocy_api_client recipe helpers
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Union

from home_food_tank_rank.models import RecipeCandidate, StockItem


def _norm(s: str) -> str:
    return " ".join(s.lower().strip().split())


def _ingredient_covered(ingredient: str, on_hand: Sequence[str]) -> bool:
    ing = _norm(ingredient)
    if not ing:
        return True
    for name in on_hand:
        n = _norm(name)
        if ing in n or n in ing:
            return True
        # token overlap (e.g. "onion" vs "yellow onion")
        ing_toks = set(ing.replace(",", " ").split())
        name_toks = set(n.replace(",", " ").split())
        if ing_toks and ing_toks <= name_toks:
            return True
        if name_toks and len(ing_toks & name_toks) >= max(1, len(ing_toks) - 1):
            if any(len(t) >= 4 for t in (ing_toks & name_toks)):
                return True
    return False


class RecipeMatcher:
    def __init__(self, recipes: Optional[List[dict]] = None) -> None:
        self._recipes: List[dict] = list(recipes or [])

    @classmethod
    def from_fixture(cls, path: Union[Path, str]) -> "RecipeMatcher":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(data, dict) and "recipes" in data:
            recipes = data["recipes"]
        else:
            recipes = data
        return cls(recipes=list(recipes))

    def add_recipe(
        self,
        recipe_id: str,
        title: str,
        ingredients: Sequence[str],
        *,
        source: str = "local",
        metadata: Optional[dict] = None,
    ) -> None:
        self._recipes.append(
            {
                "id": recipe_id,
                "title": title,
                "ingredients": list(ingredients),
                "source": source,
                "metadata": metadata or {},
            }
        )

    def extend_from_adapter(self, recipes: Iterable[dict]) -> int:
        n = 0
        for r in recipes:
            rid = str(r.get("id") or r.get("recipe_id") or r.get("pk") or "")
            title = str(r.get("title") or r.get("name") or rid)
            ings = r.get("ingredients") or r.get("ingredient_list") or []
            if isinstance(ings, str):
                ings = [x.strip() for x in ings.split(",") if x.strip()]
            if not rid or not title:
                continue
            self.add_recipe(
                rid,
                title,
                [str(i) for i in ings],
                source=str(r.get("source") or "adapter"),
                metadata=dict(r.get("metadata") or {}),
            )
            n += 1
        return n

    def match(
        self,
        stock: Sequence[StockItem] | Sequence[str],
        *,
        min_cover: float = 0.5,
        exclude_recipe_ids: Optional[Sequence[str]] = None,
        limit: int = 20,
    ) -> List[RecipeCandidate]:
        if stock and isinstance(stock[0], StockItem):
            on_hand = [i.name for i in stock if i.quantity > 0]  # type: ignore[union-attr]
        else:
            on_hand = [str(s) for s in stock]

        exclude = set(exclude_recipe_ids or [])
        out: List[RecipeCandidate] = []
        for r in self._recipes:
            rid = str(r.get("id") or "")
            if rid in exclude:
                continue
            ings = [str(x) for x in (r.get("ingredients") or [])]
            if not ings:
                continue
            matched = [i for i in ings if _ingredient_covered(i, on_hand)]
            missing = [i for i in ings if i not in matched]
            ratio = len(matched) / len(ings) if ings else 0.0
            if ratio < min_cover:
                continue
            out.append(
                RecipeCandidate(
                    recipe_id=rid,
                    title=str(r.get("title") or rid),
                    ingredients=ings,
                    source=str(r.get("source") or "fixture"),
                    matched=matched,
                    missing=missing,
                    cover_ratio=round(ratio, 3),
                    metadata=dict(r.get("metadata") or {}),
                )
            )
        out.sort(key=lambda c: (c.cover_ratio, -len(c.missing)), reverse=True)
        return out[:limit]
