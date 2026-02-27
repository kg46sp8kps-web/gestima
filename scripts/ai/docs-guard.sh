#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

ERRORS=0

ALLOWED_DOCS=(
  "AGENTS.md"
  "app/AGENTS.md"
  "frontend/AGENTS.md"
  "ai/workflow.md"
  "ai/agents/orchestrator.md"
  "ai/agents/backend.md"
  "ai/agents/frontend.md"
  "ai/agents/qa.md"
  "ai/agents/auditor.md"
  "docs/ai/context-ledger.md"
)

is_allowed_doc() {
  local target="$1"
  local allowed
  for allowed in "${ALLOWED_DOCS[@]}"; do
    if [[ "$allowed" == "$target" ]]; then
      return 0
    fi
  done
  return 1
}

check_exists() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "[docs-guard] ERROR missing required file: $file"
    ERRORS=$((ERRORS + 1))
  fi
}

check_max_lines() {
  local file="$1"
  local max_lines="$2"
  if [[ ! -f "$file" ]]; then
    return
  fi
  local count
  count="$(wc -l < "$file" | tr -d ' ')"
  if [[ "$count" -gt "$max_lines" ]]; then
    echo "[docs-guard] ERROR $file has $count lines (limit: $max_lines)"
    ERRORS=$((ERRORS + 1))
  fi
}

echo "[docs-guard] Validating required active docs..."
for file in "${ALLOWED_DOCS[@]}"; do
  check_exists "$file"
done

echo "[docs-guard] Validating no extra active AI docs were added..."
if [[ -d ai ]]; then
  while IFS= read -r file; do
    rel="${file#./}"
    if ! is_allowed_doc "$rel"; then
      echo "[docs-guard] ERROR unauthorized AI doc in active tree: $rel"
      ERRORS=$((ERRORS + 1))
    fi
  done < <(find ai -type f -name '*.md' | sort)
fi

if [[ -d docs/ai ]]; then
  while IFS= read -r file; do
    rel="${file#./}"
    if ! is_allowed_doc "$rel"; then
      echo "[docs-guard] ERROR unauthorized AI doc in active tree: $rel"
      ERRORS=$((ERRORS + 1))
    fi
  done < <(find docs/ai -type f -name '*.md' | sort)
fi

echo "[docs-guard] Validating AGENTS file surface..."
while IFS= read -r file; do
  rel="${file#./}"
  case "$rel" in
    AGENTS.md|app/AGENTS.md|frontend/AGENTS.md)
      ;;
    *)
      echo "[docs-guard] ERROR unexpected AGENTS file: $rel"
      ERRORS=$((ERRORS + 1))
      ;;
  esac
done < <(find . -type f -name '*AGENTS*.md' \
  -not -path './.git/*' \
  -not -path './claude_bak/*' \
  -not -path './docs/archive/*' \
  -not -path './docs/ADR/archive/*' | sort)

echo "[docs-guard] Validating file size budgets..."
check_max_lines "AGENTS.md" 220
check_max_lines "app/AGENTS.md" 140
check_max_lines "frontend/AGENTS.md" 140
check_max_lines "ai/workflow.md" 120
check_max_lines "ai/agents/orchestrator.md" 120
check_max_lines "ai/agents/backend.md" 100
check_max_lines "ai/agents/frontend.md" 100
check_max_lines "ai/agents/qa.md" 100
check_max_lines "ai/agents/auditor.md" 100
check_max_lines "docs/ai/context-ledger.md" 300

total_lines=0
for file in "${ALLOWED_DOCS[@]}"; do
  if [[ -f "$file" ]]; then
    count="$(wc -l < "$file" | tr -d ' ')"
    total_lines=$((total_lines + count))
  fi
done
if [[ "$total_lines" -gt 800 ]]; then
  echo "[docs-guard] ERROR total active AI docs have $total_lines lines (limit: 800)"
  ERRORS=$((ERRORS + 1))
fi

echo "[docs-guard] Validating no active references to archived Claude setup..."
if command -v rg >/dev/null 2>&1; then
  legacy_refs="$(rg -n 'CLAUDE\.md|\.claude/' \
    --hidden \
    --glob '!.git/**' \
    --glob '!claude_bak/**' \
    --glob '!docs/archive/**' \
    --glob '!docs/ADR/archive/**' \
    --glob '!scripts/ai/docs-guard.sh' || true)"
else
  legacy_refs="$(grep -RInE 'CLAUDE\.md|\.claude/' . \
    --exclude-dir=.git \
    --exclude-dir=claude_bak \
    --exclude-dir=archive \
    --exclude='docs-guard.sh' || true)"
fi
legacy_refs="$(echo "$legacy_refs" | grep -Ev '^\.gitignore:.*claude_bak/\.claude/' || true)"
if [[ -n "$legacy_refs" ]]; then
  echo "[docs-guard] ERROR legacy Claude references found in active docs/code:"
  echo "$legacy_refs"
  ERRORS=$((ERRORS + 1))
fi

if [[ "$ERRORS" -gt 0 ]]; then
  echo "[docs-guard] FAIL ($ERRORS issue(s))"
  exit 1
fi

echo "[docs-guard] PASS"
