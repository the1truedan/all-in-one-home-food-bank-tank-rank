# Consolidation map (monorepo → this package)

**Policy:** one idea → one module. Tangential vibecode dumps that covered the same job
are **not** re-imported; behavior is reimplemented behind a small public API.

## Fold table

| Idea | Monorepo sources (do not copy broken dumps) | Here |
|------|-----------------------------------------------|------|
| Stock by home location | `marv_inventory.py`, `grocery_inventory.py`, `inventory_manager.py`, photo inventory stub | `inventory.py` + `store.py` + `FoodLocation` |
| Barcode → product | `barcode_scanner.py` (drop eBay/Amazon label side-quests) | `barcode.py` (`lookup_barcode`, `stock_from_barcode`) |
| Recipes from on-hand | `meal_planner.py`, Tandoor/Grocy search helpers | `recipes.py` + `adapters/tandoor.py` / `grocy.py` |
| Post-meal ratings / avoid | `adaptive_meal_planner.get_recipe_ratings` | `tank_rank.py` |
| Low stock shopping list | `smart_grocery_list.py`, `shopping_list_optimizer.py` | `restock.py` (`plan`) |
| Food bank on scarcity | `food_bank_manager.py` | `restock.py` (`food_bank_suggest`, **HITL only**) |
| Coupons / circulars | `flipp_tracker.py`, `coupon_module.py`, store scrapers | **out of core v0** — optional later adapter; coupon_hint string only |
| M.A.R.L.A. hated foods | `marla_food_preferences_and_meal_planning` | pass avoid list into `RecipeMatcher.match(exclude=…)` / `TankRank` — prefs stay in monorepo |
| Spoilage sensors | `harpies_food_safety.py` | **phase 2** — not in v0 package surface |

## Why not re-export monorepo modules

Most shopping/food files under `grokcode/tools/shopping/` are `# promoted:` transcript
dumps with **SyntaxError**. Porting them as-is fails import. Clean rewrite behind
`Inventory` / `RecipeMatcher` / `TankRank` / `RestockPlanner` is simpler and testable.

## API surface (keep thin)

```text
Inventory          — put / list / low_stock / by_location
RecipeMatcher      — match(stock) → candidates with cover_ratio
TankRank           — log_attempt / review / metrics / rank_candidates
RestockPlanner     — plan + food_bank_suggest (prepare-only)
lookup_barcode     — OpenFoodFacts (optional network)
adapters.Grocy / Tandoor — optional HTTP, env-configured
```

No Tkinter dashboard tabs, no Google Calendar auto-booking, no thrift/auction code here
(that stays under M.A.R.V. procurement).
