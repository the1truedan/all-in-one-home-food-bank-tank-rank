"""Post-meal reviews: rank high / mark avoid (the 'tank-rank' loop).

Folds ratings half of tools/caregiving/adaptive_meal_planner.py
(get_recipe_ratings / suggest_optimal_meals sorting).
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union

from home_food_tank_rank.models import (
    MealAttempt,
    MealReview,
    RecipeCandidate,
    utc_now_iso,
)
from home_food_tank_rank.store import Store


class TankRank:
    def __init__(self, db_path: Union[Path, str]) -> None:
        self.store = Store(db_path)

    def log_attempt(
        self,
        recipe: RecipeCandidate | dict,
        *,
        locations_used: Optional[Sequence[str]] = None,
        missing_items: Optional[Sequence[str]] = None,
        cooked_at: Optional[str] = None,
    ) -> MealAttempt:
        if isinstance(recipe, RecipeCandidate):
            rid = recipe.recipe_id
            title = recipe.title
            missing = list(missing_items if missing_items is not None else recipe.missing)
        else:
            rid = str(recipe["recipe_id"])
            title = str(recipe.get("title") or rid)
            missing = list(missing_items or recipe.get("missing") or [])
        attempt = MealAttempt(
            attempt_id=uuid.uuid4().hex[:12],
            recipe_id=rid,
            recipe_title=title,
            cooked_at=cooked_at or utc_now_iso(),
            locations_used=list(locations_used or []),
            missing_items=missing,
        )
        self.store.save_attempt(attempt)
        return attempt

    def review(
        self,
        attempt_id: str,
        recipe_id: str,
        score: int,
        *,
        mark_avoid: bool = False,
        tags: Optional[Sequence[str]] = None,
        notes: str = "",
    ) -> MealReview:
        rev = MealReview(
            attempt_id=attempt_id,
            recipe_id=recipe_id,
            score=score,
            mark_avoid=mark_avoid,
            tags=list(tags or []),
            notes=notes,
        )
        self.store.save_review(rev)
        return rev

    def recipe_ratings(self) -> Dict[str, float]:
        """Mean score per recipe_id (only non-avoid reviews count for mean)."""
        scores: Dict[str, List[int]] = defaultdict(list)
        for r in self.store.list_reviews():
            if r.mark_avoid:
                continue
            scores[r.recipe_id].append(r.score)
        return {
            rid: round(sum(vals) / len(vals), 3)
            for rid, vals in scores.items()
            if vals
        }

    def avoid_recipe_ids(self) -> List[str]:
        avoided = set()
        for r in self.store.list_reviews():
            if r.mark_avoid:
                avoided.add(r.recipe_id)
        return sorted(avoided)

    def top_recipes(self, limit: int = 10) -> List[dict]:
        ratings = self.recipe_ratings()
        ranked = sorted(ratings.items(), key=lambda kv: kv[1], reverse=True)
        return [{"recipe_id": rid, "mean_score": sc} for rid, sc in ranked[:limit]]

    def metrics(self) -> dict:
        attempts = self.store.list_attempts()
        reviews = self.store.list_reviews()
        avoids = [r for r in reviews if r.mark_avoid]
        scores = [r.score for r in reviews if not r.mark_avoid]
        return {
            "attempts": len(attempts),
            "reviews": len(reviews),
            "avoid_count": len(avoids),
            "avoid_recipe_ids": self.avoid_recipe_ids(),
            "mean_score": round(sum(scores) / len(scores), 3) if scores else None,
            "top_recipes": self.top_recipes(5),
            "recipe_ratings": self.recipe_ratings(),
        }

    def rank_candidates(
        self, candidates: Sequence[RecipeCandidate]
    ) -> List[RecipeCandidate]:
        """Re-order recipe matches: drop avoid, boost high historical scores."""
        avoid = set(self.avoid_recipe_ids())
        ratings = self.recipe_ratings()
        kept = [c for c in candidates if c.recipe_id not in avoid]
        kept.sort(
            key=lambda c: (ratings.get(c.recipe_id, 0.0), c.cover_ratio),
            reverse=True,
        )
        return kept
