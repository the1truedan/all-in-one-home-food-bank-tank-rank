from __future__ import annotations

from pathlib import Path

from home_food_tank_rank.inventory import Inventory
from home_food_tank_rank.recipes import RecipeMatcher
from home_food_tank_rank.tank_rank import TankRank


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures"


def test_match_and_avoid_rerank(tmp_path: Path) -> None:
    inv = Inventory(tmp_path / "t.db")
    inv.load_fixture(
        (FIXTURE_ROOT / "stock.json").read_text(encoding="utf-8")
        and __import__("json").loads((FIXTURE_ROOT / "stock.json").read_text())["stock"]
    )
    matcher = RecipeMatcher.from_fixture(FIXTURE_ROOT / "recipes.json")
    candidates = matcher.match(inv.list(), min_cover=0.5)
    assert any(c.recipe_id == "r-pasta-simple" for c in candidates)
    assert all(c.recipe_id != "r-needs-many" for c in candidates)

    rank = TankRank(tmp_path / "t.db")
    # mark pasta avoid
    att = rank.log_attempt(next(c for c in candidates if c.recipe_id == "r-pasta-simple"))
    rank.review(att.attempt_id, "r-pasta-simple", score=1, mark_avoid=True)
    # beans get high score
    att2 = rank.log_attempt(next(c for c in candidates if c.recipe_id == "r-beans-rice"))
    rank.review(att2.attempt_id, "r-beans-rice", score=5, mark_avoid=False)

    ranked = rank.rank_candidates(candidates)
    ids = [c.recipe_id for c in ranked]
    assert "r-pasta-simple" not in ids
    assert ids[0] == "r-beans-rice"

    m = rank.metrics()
    assert m["avoid_count"] == 1
    assert m["mean_score"] == 5.0
