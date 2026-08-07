#!/usr/bin/env bash
# Fail closed on likely committed secrets (heuristic). Placeholders allowed.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Real-looking secrets (not empty, not placeholders)
if grep -RInE --exclude-dir=.git --exclude-dir=.venv --exclude-dir=scripts \
  --exclude='*.db' --exclude='verify_no_phi_grep.sh' \
  'GROCY_API_KEY=["'"'"']?[A-Za-z0-9_-]{16,}' . 2>/dev/null; then
  echo "FAIL: GROCY_API_KEY looks real" >&2
  exit 1
fi
if grep -RInE --exclude-dir=.git --exclude-dir=.venv --exclude-dir=scripts \
  --exclude='*.db' \
  'TANDOOR_API_KEY=["'"'"']?[A-Za-z0-9_-]{16,}' . 2>/dev/null; then
  echo "FAIL: TANDOOR_API_KEY looks real" >&2
  exit 1
fi
if grep -RInE --exclude-dir=.git --exclude-dir=.venv \
  --exclude='*.db' --exclude='verify_no_phi_grep.sh' \
  'BEGIN (RSA |OPENSSH )?PRIVATE KEY' . 2>/dev/null; then
  echo "FAIL: private key material" >&2
  exit 1
fi
if grep -RInE --exclude-dir=.git --exclude-dir=.venv \
  --exclude='*.db' \
  'sk-[a-zA-Z0-9]{20,}' . 2>/dev/null; then
  echo "FAIL: sk- token" >&2
  exit 1
fi

echo "verify_no_phi_grep: ok"
