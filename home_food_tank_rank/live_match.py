"""Live Grocy stock × Tandoor recipes match (prepare-only report)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from home_food_tank_rank.adapters.grocy import GrocyAdapter
from home_food_tank_rank.adapters.tandoor import TandoorAdapter
from home_food_tank_rank.inventory import Inventory
from home_food_tank_rank.models import StockItem
from home_food_tank_rank.recipes import RecipeMatcher
from home_food_tank_rank.restock import RestockPlanner
from home_food_tank_rank.tank_rank import TankRank


def run_live_match(
    *,
    db_path: str,
    recipe_limit: int = 40,
    min_cover: float = 0.0,
    top_n: int = 15,
    persist_stock: bool = True,
) -> Dict[str, Any]:
    """Pull live data, match, return scrub-safe report (no secrets)."""
    grocy = GrocyAdapter()
    tandoor = TandoorAdapter()

    g_health = grocy.health()
    t_health = tandoor.health()

    stock: List[StockItem] = grocy.fetch_stock() if grocy.configured else []
    recipes = (
        tandoor.fetch_recipes(limit=recipe_limit, with_details=True)
        if tandoor.configured
        else []
    )

    inv = Inventory(db_path)
    if persist_stock and stock:
        inv.store.replace_all_stock(stock)
    elif persist_stock and not stock:
        # keep prior local stock; report empty pull
        pass

    # Prefer live Grocy stock for match; fall back to local DB if Grocy empty but local has data
    match_stock = stock if stock else inv.list()
    stock_source = "grocy" if stock else ("local_db" if match_stock else "empty")

    matcher = RecipeMatcher()
    matcher.extend_from_adapter(recipes)
    rank = TankRank(db_path)
    candidates = matcher.match(match_stock, min_cover=min_cover, limit=max(top_n * 3, 30))
    ranked = rank.rank_candidates(candidates)[:top_n]

    # Ingredient gap frequency across pulled recipes (shopping foresight)
    gap_counts: Dict[str, int] = {}
    for r in recipes:
        for ing in r.get("ingredients") or []:
            # only count if not covered by stock
            on_hand = [s.name for s in match_stock if s.quantity > 0]
            from home_food_tank_rank.recipes import _ingredient_covered

            if not _ingredient_covered(ing, on_hand):
                gap_counts[ing.lower()] = gap_counts.get(ing.lower(), 0) + 1
    top_gaps = sorted(gap_counts.items(), key=lambda kv: kv[1], reverse=True)[:20]

    planner = RestockPlanner()
    restock = planner.full_report(
        [s for s in match_stock if s.is_low()] if match_stock else [],
        recipe_gaps=[g[0] for g in top_gaps[:10]],
    )

    return {
        "prepare_only": True,
        "health": {"grocy": g_health, "tandoor": t_health},
        "stock": {
            "source": stock_source,
            "count": len(match_stock),
            "with_qty_gt_0": sum(1 for s in match_stock if s.quantity > 0),
            "items": [s.to_dict() for s in match_stock[:50]],
            "locations_in_grocy": grocy.locations() if grocy.configured else [],
        },
        "recipes": {
            "pulled": len(recipes),
            "with_ingredients": sum(1 for r in recipes if r.get("ingredients")),
            "limit": recipe_limit,
        },
        "match": {
            "min_cover": min_cover,
            "candidates": [c.to_dict() for c in ranked],
            "note": (
                "Empty stock yields empty or zero-cover matches; "
                "add Grocy products/stock or local put to enable cookable lists."
                if stock_source == "empty"
                else None
            ),
        },
        "top_ingredient_gaps": [{"ingredient": k, "recipe_hits": v} for k, v in top_gaps],
        "restock": restock,
    }
