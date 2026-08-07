# Privacy boundary

| Allowed in git | Never in git |
|----------------|--------------|
| Synthetic fixtures | Real household inventory dumps |
| Example food-bank JSON with fake names | Real pantry phone numbers / member names |
| Scrubbed smoke metrics (counts only) | API keys, LAN URLs with credentials |
| Code + tests | Clinical diet plans / PHI meal notes |

Prepare-only: restock and food-bank hints require a human. Do not auto-book appointments.

Operator secrets: use `.env` (gitignored) with `GROCY_*` / `TANDOOR_*`.
