#!/bin/bash
# GESTIMA - Setup script (vytvoření venv + instalace dependencies)

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📦 GESTIMA Setup"
echo ""

# Zkontroluj Python
echo "✓ Checking Python..."
python3 --version

# Vytvoř venv pokud neexistuje
if [ ! -d "venv" ]; then
    echo "✓ Creating virtual environment..."
    python3 -m venv venv
else
    echo "✓ Virtual environment already exists"
fi

# Aktivuj venv
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "✓ Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Instaluj dependencies
echo "✓ Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Run: ./run.sh"
echo "  2. Open: http://localhost:8000"
echo ""
