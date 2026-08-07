# Agents working in this repo

1. Read `docs/PRIVACY_BOUNDARY.md` and `docs/CONSOLIDATION.md` first.
2. Prefer extending the thin public API (`Inventory`, `RecipeMatcher`, `TankRank`, `RestockPlanner`) over adding parallel modules.
3. Do not copy broken `# promoted:` dumps from `grokcode/tools/shopping/` — rewrite against tests.
4. Do not commit real inventory, API keys, or pantry PII.
5. Coupons/Flipp and H.A.R.P.I.E.S. sensors are out of core v0 unless explicitly scoped.
6. Public flip is **human-gated**.
