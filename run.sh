#!/bin/bash
# GESTIMA - Spuštění aplikace

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Aktivuj venv
source venv/bin/activate

echo "🚀 GESTIMA 1.0 - Starting..."
echo "📍 URL: http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"
echo ""
echo "Press CTRL+C to stop"
echo ""

# Spusť aplikaci
uvicorn app.gestima_app:app --reload --host 0.0.0.0 --port 8000
