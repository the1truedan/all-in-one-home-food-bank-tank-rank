"""CLI: inventory summary, match recipes, review meals, restock plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from home_food_tank_rank.inventory import Inventory
from home_food_tank_rank.recipes import RecipeMatcher
from home_food_tank_rank.restock import RestockPlanner
from home_food_tank_rank.tank_rank import TankRank


def _default_db(args: argparse.Namespace) -> Path:
    return Path(args.db)


def cmd_summary(args: argparse.Namespace) -> int:
    inv = Inventory(_default_db(args))
    print(json.dumps(inv.summary(), indent=2))
    return 0


def cmd_load_fixture(args: argparse.Namespace) -> int:
    inv = Inventory(_default_db(args))
    data = json.loads(Path(args.path).read_text(encoding="utf-8"))
    items = data["stock"] if isinstance(data, dict) and "stock" in data else data
    n = inv.load_fixture(items)
    print(json.dumps({"loaded": n, "db": str(_default_db(args))}))
    return 0


def cmd_match(args: argparse.Namespace) -> int:
    inv = Inventory(_default_db(args))
    matcher = RecipeMatcher.from_fixture(args.recipes)
    rank = TankRank(_default_db(args))
    candidates = matcher.match(inv.list(), min_cover=args.min_cover)
    ranked = rank.rank_candidates(candidates)
    print(json.dumps([c.to_dict() for c in ranked], indent=2))
    return 0


def cmd_live_match(args: argparse.Namespace) -> int:
    """Grocy stock × Tandoor recipes (env: GROCY_*, TANDOOR_*)."""
    from home_food_tank_rank.live_match import run_live_match

    report = run_live_match(
        db_path=str(_default_db(args)),
        recipe_limit=args.limit,
        min_cover=args.min_cover,
        top_n=args.top,
        persist_stock=not args.no_persist,
    )
    print(json.dumps(report, indent=2))
    # non-zero if adapters misconfigured
    g_ok = report.get("health", {}).get("grocy", {}).get("ok")
    t_ok = report.get("health", {}).get("tandoor", {}).get("ok")
    if not g_ok or not t_ok:
        return 2
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    from home_food_tank_rank.adapters.grocy import GrocyAdapter
    from home_food_tank_rank.adapters.tandoor import TandoorAdapter

    print(
        json.dumps(
            {"grocy": GrocyAdapter().health(), "tandoor": TandoorAdapter().health()},
            indent=2,
        )
    )
    return 0


def cmd_cook(args: argparse.Namespace) -> int:
    rank = TankRank(_default_db(args))
    attempt = rank.log_attempt(
        {"recipe_id": args.recipe_id, "title": args.title or args.recipe_id}
    )
    print(json.dumps(attempt.to_dict(), indent=2))
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    rank = TankRank(_default_db(args))
    rev = rank.review(
        args.attempt_id,
        args.recipe_id,
        score=args.score,
        mark_avoid=args.avoid,
        notes=args.notes or "",
    )
    print(json.dumps(rev.to_dict(), indent=2))
    return 0


def cmd_metrics(args: argparse.Namespace) -> int:
    rank = TankRank(_default_db(args))
    print(json.dumps(rank.metrics(), indent=2))
    return 0


def cmd_restock(args: argparse.Namespace) -> int:
    inv = Inventory(_default_db(args))
    fb = None
    if args.food_bank_config:
        fb = json.loads(Path(args.food_bank_config).read_text(encoding="utf-8"))
    planner = RestockPlanner(food_bank=fb)
    print(json.dumps(planner.full_report(inv.low_stock()), indent=2))
    return 0


def cmd_put(args: argparse.Namespace) -> int:
    inv = Inventory(_default_db(args))
    item = inv.put(
        args.name,
        args.quantity,
        location=args.location,
        unit=args.unit,
        barcode=args.barcode,
    )
    print(json.dumps(item.to_dict(), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="home-food",
        description="Home food bank + tank-rank (local-first)",
    )
    p.add_argument(
        "--db",
        default="data/home_food.db",
        help="SQLite path (default: data/home_food.db)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("summary", help="Stock summary by location")
    s.set_defaults(func=cmd_summary)

    s = sub.add_parser("put", help="Upsert stock item")
    s.add_argument("name")
    s.add_argument("quantity", type=float)
    s.add_argument("--location", default="pantry")
    s.add_argument("--unit", default="ea")
    s.add_argument("--barcode", default=None)
    s.set_defaults(func=cmd_put)

    s = sub.add_parser("load-fixture", help="Replace stock from JSON fixture")
    s.add_argument("path")
    s.set_defaults(func=cmd_load_fixture)

    s = sub.add_parser("match", help="Match recipes to on-hand stock")
    s.add_argument("--recipes", default="fixtures/recipes.json")
    s.add_argument("--min-cover", type=float, default=0.5)
    s.set_defaults(func=cmd_match)

    s = sub.add_parser(
        "live-match",
        help="Pull Grocy stock + Tandoor recipes and match (env GROCY_*/TANDOOR_*)",
    )
    s.add_argument("--limit", type=int, default=40, help="Max Tandoor recipes to hydrate")
    s.add_argument("--min-cover", type=float, default=0.0)
    s.add_argument("--top", type=int, default=15)
    s.add_argument(
        "--no-persist",
        action="store_true",
        help="Do not write Grocy stock into local SQLite",
    )
    s.set_defaults(func=cmd_live_match)

    s = sub.add_parser("health", help="Grocy + Tandoor adapter health (env keys)")
    s.set_defaults(func=cmd_health)

    s = sub.add_parser("cook", help="Log a meal attempt")
    s.add_argument("recipe_id")
    s.add_argument("--title", default=None)
    s.set_defaults(func=cmd_cook)

    s = sub.add_parser("review", help="Post-meal review (1-5) and optional avoid")
    s.add_argument("attempt_id")
    s.add_argument("recipe_id")
    s.add_argument("score", type=int)
    s.add_argument("--avoid", action="store_true")
    s.add_argument("--notes", default="")
    s.set_defaults(func=cmd_review)

    s = sub.add_parser("metrics", help="Tank-rank metrics")
    s.set_defaults(func=cmd_metrics)

    s = sub.add_parser("restock", help="Shopping list + food-bank HITL hint")
    s.add_argument("--food-bank-config", default=None)
    s.set_defaults(func=cmd_restock)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
