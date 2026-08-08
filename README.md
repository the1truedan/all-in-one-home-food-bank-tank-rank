# all-in-one-home-food-bank-tank-rank

Local-first **home food bank**: know what is in the fridge, freezer, cabinets, and spice rack;
match recipes to on-hand stock; log meal attempts; **tank-rank** after eating (repeat vs mark avoid);
build a restock list and optional **HITL** food-pantry hint.

| | |
|--|--|
| Package | `home_food_tank_rank` |
| Version | **0.1.0** (public alpha) |
| Python | 3.10+ · **stdlib only** for core |
| Related | M.A.R.V. resource loop inside private M.A.N.A.G.E.R. monorepo |

**Not** a certified nutrition system, not auto-booking for food banks, not a multi-store coupon scraper.
Prepare-only suggestions; humans sign off.

---

## Why consolidate

Earlier vibecode left the same ideas in many monorepo files (`grocery_inventory`, `inventory_manager`,
`meal_planner`, `adaptive_meal_planner`, `smart_grocery_list`, `food_bank_manager`, broken
`grocy_api_client` / `tandoor_api_client`). Most of those dumps **do not parse**.

This repo folds them into **four** modules + optional adapters — see [`docs/CONSOLIDATION.md`](docs/CONSOLIDATION.md).

```text
barcode / put stock  →  Inventory (locations)
                         ↓
                   RecipeMatcher (on-hand cover)
                         ↓
                   cook attempt → TankRank review
                         ↓
                   RestockPlanner (list + food bank HITL)
```

---

## Quick start (fixtures, offline)

```bash
cd ~/all-in-one-home-food-bank-tank-rank
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

python3 -m home_food_tank_rank.cli --db /tmp/home_food.db load-fixture fixtures/stock.json
python3 -m home_food_tank_rank.cli --db /tmp/home_food.db summary
python3 -m home_food_tank_rank.cli --db /tmp/home_food.db match --recipes fixtures/recipes.json
python3 -m home_food_tank_rank.cli --db /tmp/home_food.db restock --food-bank-config fixtures/food_bank.example.json

pytest -q
bash scripts/verify_no_phi_grep.sh
```

### Post-meal tank-rank loop

```bash
# after match, pick a recipe_id:
python3 -m home_food_tank_rank.cli --db /tmp/home_food.db cook r-beans-rice --title "Black beans and rice"
# use attempt_id from output:
python3 -m home_food_tank_rank.cli --db /tmp/home_food.db review <attempt_id> r-beans-rice 5
python3 -m home_food_tank_rank.cli --db /tmp/home_food.db metrics
```

---

## Optional: Grocy + Tandoor (self-hosted)

```bash
export GROCY_URL="http://your-host:port"
export GROCY_API_KEY="..."
export TANDOOR_URL="http://your-host:port"
export TANDOOR_API_KEY="..."

python3 -m home_food_tank_rank.cli health
# Grocy stock × Tandoor recipes (prepare-only JSON)
python3 -m home_food_tank_rank.cli live-match --limit 30 --top 12
```

```python
from home_food_tank_rank.adapters.grocy import GrocyAdapter
from home_food_tank_rank.adapters.tandoor import TandoorAdapter

print(GrocyAdapter().health())
print(TandoorAdapter().health())
```

Keys never belong in git. See [`.env.example`](.env.example).

M.A.N.A.G.E.R. mesh framing (private): `manager-module-home-food-tank-rank` — backstory + M.A.R.V. bridge.

---

## Docs

| Doc | Purpose |
|-----|---------|
| [`docs/CONSOLIDATION.md`](docs/CONSOLIDATION.md) | What monorepo functions folded where |
| [`docs/PRIVACY_BOUNDARY.md`](docs/PRIVACY_BOUNDARY.md) | What never enters this tree |
| [`docs/MANAGER_CONNECTIVITY.md`](docs/MANAGER_CONNECTIVITY.md) | M.A.N.A.G.E.R. mesh placement |

---

## Public status

Public alpha (2026-08-07). Scrub: synthetic fixtures only, no API keys, no household inventory.
Live Grocy/Tandoor stay on your LAN — never commit keys. Further features remain HITL.
