"""SQLite store for local inventory + tank-rank (single DB, no monorepo split)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from home_food_tank_rank.models import FoodLocation, MealAttempt, MealReview, StockItem


class Store:
    """One SQLite file: stock + meal attempts + reviews."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS stock (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    quantity REAL NOT NULL DEFAULT 0,
                    unit TEXT DEFAULT 'ea',
                    location TEXT NOT NULL DEFAULT 'pantry',
                    barcode TEXT,
                    expires_on TEXT,
                    low_threshold REAL DEFAULT 1.0,
                    source TEXT DEFAULT 'local',
                    metadata_json TEXT,
                    UNIQUE(name, location)
                );
                CREATE INDEX IF NOT EXISTS idx_stock_location ON stock(location);
                CREATE INDEX IF NOT EXISTS idx_stock_qty ON stock(quantity);

                CREATE TABLE IF NOT EXISTS meal_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    recipe_id TEXT NOT NULL,
                    recipe_title TEXT NOT NULL,
                    cooked_at TEXT NOT NULL,
                    locations_used_json TEXT,
                    missing_items_json TEXT
                );

                CREATE TABLE IF NOT EXISTS meal_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id TEXT NOT NULL,
                    recipe_id TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    mark_avoid INTEGER NOT NULL DEFAULT 0,
                    tags_json TEXT,
                    notes TEXT,
                    reviewed_at TEXT NOT NULL,
                    UNIQUE(attempt_id)
                );
                CREATE INDEX IF NOT EXISTS idx_reviews_recipe ON meal_reviews(recipe_id);
                """
            )

    # --- stock ---

    def upsert_stock(self, item: StockItem) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO stock (
                    name, quantity, unit, location, barcode, expires_on,
                    low_threshold, source, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name, location) DO UPDATE SET
                    quantity=excluded.quantity,
                    unit=COALESCE(excluded.unit, stock.unit),
                    barcode=COALESCE(excluded.barcode, stock.barcode),
                    expires_on=COALESCE(excluded.expires_on, stock.expires_on),
                    low_threshold=excluded.low_threshold,
                    source=excluded.source,
                    metadata_json=COALESCE(excluded.metadata_json, stock.metadata_json)
                """,
                (
                    item.name,
                    item.quantity,
                    item.unit,
                    item.location.value,
                    item.barcode,
                    item.expires_on,
                    item.low_threshold,
                    item.source,
                    json.dumps(item.metadata) if item.metadata else None,
                ),
            )

    def list_stock(
        self, location: Optional[FoodLocation] = None
    ) -> List[StockItem]:
        with self._connect() as conn:
            if location:
                rows = conn.execute(
                    "SELECT * FROM stock WHERE location = ? ORDER BY name",
                    (location.value,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM stock ORDER BY location, name"
                ).fetchall()
        return [self._row_to_stock(r) for r in rows]

    def low_stock(self, threshold: Optional[float] = None) -> List[StockItem]:
        items = self.list_stock()
        if threshold is None:
            return [i for i in items if i.is_low()]
        return [i for i in items if i.quantity < threshold]

    def find_by_name(self, name: str) -> List[StockItem]:
        q = f"%{name.lower()}%"
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM stock WHERE LOWER(name) LIKE ? ORDER BY name",
                (q,),
            ).fetchall()
        return [self._row_to_stock(r) for r in rows]

    def replace_all_stock(self, items: Iterable[StockItem]) -> int:
        """Load fixture-style bulk (dev/demo). Clears local stock first."""
        with self._connect() as conn:
            conn.execute("DELETE FROM stock")
        n = 0
        for item in items:
            self.upsert_stock(item)
            n += 1
        return n

    @staticmethod
    def _row_to_stock(row: sqlite3.Row) -> StockItem:
        meta_raw = row["metadata_json"]
        meta: Dict[str, Any] = json.loads(meta_raw) if meta_raw else {}
        return StockItem(
            name=row["name"],
            quantity=float(row["quantity"] or 0),
            unit=row["unit"] or "ea",
            location=FoodLocation.coerce(row["location"]),
            barcode=row["barcode"],
            expires_on=row["expires_on"],
            low_threshold=float(row["low_threshold"] if row["low_threshold"] is not None else 1.0),
            source=row["source"] or "local",
            metadata=meta,
        )

    # --- meals ---

    def save_attempt(self, attempt: MealAttempt) -> None:
        if not attempt.attempt_id:
            raise ValueError("attempt_id required")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO meal_attempts (
                    attempt_id, recipe_id, recipe_title, cooked_at,
                    locations_used_json, missing_items_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt.attempt_id,
                    attempt.recipe_id,
                    attempt.recipe_title,
                    attempt.cooked_at,
                    json.dumps(attempt.locations_used),
                    json.dumps(attempt.missing_items),
                ),
            )

    def save_review(self, review: MealReview) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO meal_reviews (
                    attempt_id, recipe_id, score, mark_avoid,
                    tags_json, notes, reviewed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(attempt_id) DO UPDATE SET
                    score=excluded.score,
                    mark_avoid=excluded.mark_avoid,
                    tags_json=excluded.tags_json,
                    notes=excluded.notes,
                    reviewed_at=excluded.reviewed_at
                """,
                (
                    review.attempt_id,
                    review.recipe_id,
                    review.score,
                    1 if review.mark_avoid else 0,
                    json.dumps(review.tags),
                    review.notes,
                    review.reviewed_at,
                ),
            )

    def list_reviews(self) -> List[MealReview]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM meal_reviews ORDER BY reviewed_at DESC"
            ).fetchall()
        out: List[MealReview] = []
        for r in rows:
            out.append(
                MealReview(
                    attempt_id=r["attempt_id"],
                    recipe_id=r["recipe_id"],
                    score=int(r["score"]),
                    mark_avoid=bool(r["mark_avoid"]),
                    tags=json.loads(r["tags_json"] or "[]"),
                    notes=r["notes"] or "",
                    reviewed_at=r["reviewed_at"],
                )
            )
        return out

    def list_attempts(self) -> List[MealAttempt]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM meal_attempts ORDER BY cooked_at DESC"
            ).fetchall()
        out: List[MealAttempt] = []
        for r in rows:
            out.append(
                MealAttempt(
                    attempt_id=r["attempt_id"],
                    recipe_id=r["recipe_id"],
                    recipe_title=r["recipe_title"],
                    cooked_at=r["cooked_at"],
                    locations_used=json.loads(r["locations_used_json"] or "[]"),
                    missing_items=json.loads(r["missing_items_json"] or "[]"),
                )
            )
        return out
