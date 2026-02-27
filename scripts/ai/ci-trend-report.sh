#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

AI_DOCS=(
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

echo "== CI TREND REPORT =="

docs_total=0
for file in "${AI_DOCS[@]}"; do
  if [[ -f "$file" ]]; then
    count="$(wc -l < "$file" | tr -d ' ')"
    docs_total=$((docs_total + count))
  fi
done
echo "AI docs total lines: $docs_total"

if [[ -d frontend/node_modules ]]; then
  echo "Collecting ESLint warning trend for e2e..."
  pushd frontend >/dev/null
  npx eslint "e2e/**/*.{test,spec}.{js,ts,jsx,tsx}" -f json -o .eslint-e2e-report.json >/dev/null || true
  warn_count="$(
    node -e "
      const fs = require('fs');
      const path = '.eslint-e2e-report.json';
      if (!fs.existsSync(path)) { console.log('0'); process.exit(0); }
      const report = JSON.parse(fs.readFileSync(path, 'utf8'));
      const warnings = report.reduce((sum, item) => sum + (item.warningCount || 0), 0);
      console.log(String(warnings));
    "
  )"
  rm -f .eslint-e2e-report.json
  popd >/dev/null
  echo "E2E ESLint warnings: $warn_count"
else
  echo "E2E ESLint warnings: skipped (frontend/node_modules missing)"
fi

echo "== END TREND REPORT =="
