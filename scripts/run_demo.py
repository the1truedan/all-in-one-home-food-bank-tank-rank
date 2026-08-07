#!/usr/bin/env python3
"""Offline demo: fixture stock → match → cook → review → restock."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from home_food_tank_rank.inventory import Inventory
from home_food_tank_rank.recipes import RecipeMatcher
from home_food_tank_rank.restock import RestockPlanner
from home_food_tank_rank.tank_rank import TankRank


def main() -> int:
    fixtures = ROOT / "fixtures"
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "demo.db"
        inv = Inventory(db)
        stock = json.loads((fixtures / "stock.json").read_text())["stock"]
        inv.load_fixture(stock)
        matcher = RecipeMatcher.from_fixture(fixtures / "recipes.json")
        rank = TankRank(db)
        candidates = rank.rank_candidates(matcher.match(inv.list(), min_cover=0.5))
        print("=== match ===")
        for c in candidates[:5]:
            print(f"  {c.cover_ratio:.0%} {c.title} missing={c.missing}")
        if not candidates:
            print("no candidates", file=sys.stderr)
            return 1
        best = candidates[0]
        attempt = rank.log_attempt(best)
        rank.review(attempt.attempt_id, best.recipe_id, score=4, notes="demo")
        print("=== metrics ===")
        print(json.dumps(rank.metrics(), indent=2))
        planner = RestockPlanner(
            food_bank=json.loads((fixtures / "food_bank.example.json").read_text())
        )
        print("=== restock ===")
        print(json.dumps(planner.full_report(inv.low_stock()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
