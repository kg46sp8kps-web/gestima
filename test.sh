#!/bin/bash
# GESTIMA - Spuštění testů

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Aktivuj venv
source venv/bin/activate

echo "🧪 Running tests..."
echo ""

# Spusť testy
pytest -v "$@"
