#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-auto}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

run_be() {
  echo "[quality-gate] Backend tests"
  python3 -m pytest tests/ -x -q --tb=short
}

run_fe() {
  echo "[quality-gate] Frontend lint"
  npm run lint -C frontend
  echo "[quality-gate] Frontend build"
  npm run build -C frontend
}

run_static_checks() {
  echo "[quality-gate] Static grep checks"

  if [[ -f scripts/ai/docs-guard.sh ]]; then
    echo "[quality-gate] Docs governance"
    bash scripts/ai/docs-guard.sh
  fi

  local hard_delete
  if command -v rg >/dev/null 2>&1; then
    hard_delete=$(rg -n 'await db\.delete\(' app/routers --glob '*.py' || true)
  else
    hard_delete=$(grep -RIn --include='*.py' 'await db\.delete(' app/routers 2>/dev/null || true)
  fi
  if [[ -n "$hard_delete" ]]; then
    echo "ERROR: hard delete detected (use soft_delete):"
    echo "$hard_delete"
    return 1
  fi

  local ts_any
  if command -v rg >/dev/null 2>&1; then
    ts_any=$(rg -n ': any\b|as any\b|<any>' frontend/src --glob '*.{ts,vue}' || true)
  else
    ts_any=$(grep -RInE ': any\b|as any\b|<any>' frontend/src --include='*.ts' --include='*.vue' 2>/dev/null || true)
  fi
  if [[ -n "$ts_any" ]]; then
    echo "ERROR: TypeScript any detected:"
    echo "$ts_any"
    return 1
  fi
}

run_auto() {
  local changed
  changed=$(git diff --name-only -- . ':(exclude)claude_bak/**' || true)

  local need_be=0
  local need_fe=0

  if [[ -z "$changed" ]]; then
    need_be=1
    need_fe=1
  else
    if echo "$changed" | grep -Eq '^(app/|tests/|alembic/)'; then need_be=1; fi
    if echo "$changed" | grep -Eq '^frontend/'; then need_fe=1; fi
  fi

  run_static_checks
  if [[ "$need_be" -eq 1 ]]; then run_be; fi
  if [[ "$need_fe" -eq 1 ]]; then run_fe; fi
}

case "$MODE" in
  be)
    run_static_checks
    run_be
    ;;
  fe)
    run_static_checks
    run_fe
    ;;
  full)
    run_static_checks
    run_be
    run_fe
    ;;
  auto)
    run_auto
    ;;
  *)
    echo "Usage: $0 [auto|be|fe|full]"
    exit 2
    ;;
esac

echo "[quality-gate] PASS ($MODE)"
