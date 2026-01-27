#!/bin/bash
# GESTIMA - Reset a seed material catalog
# Smaže staré kategorie a vytvoří nové podle importní struktury

set -e  # Exit on error

echo "=========================================="
echo "GESTIMA - Material Catalog Reset & Seed"
echo "=========================================="
echo ""
echo "⚠️  VAROVÁNÍ: Toto smaže všechny MaterialGroups, Categories a Tiers!"
echo ""
read -p "Opravdu chceš pokračovat? (yes/no): " -r
echo

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Zrušeno."
    exit 0
fi

echo "[1/3] Mazání existujících dat..."
sqlite3 gestima.db <<EOF
DELETE FROM material_price_tiers WHERE 1=1;
DELETE FROM material_price_categories WHERE 1=1;
DELETE FROM material_groups WHERE 1=1;
EOF

echo "  ✅ Smazáno"
echo ""

echo "[2/3] Spouštím seed script..."
python3 scripts/seed_material_catalog.py

echo ""
echo "[3/3] Importuji material norms..."
python3 scripts/generate_material_norms.py

# Check if SQL file was generated
if [ -f "temp/material_norms_seed.sql" ]; then
    sqlite3 gestima.db < temp/material_norms_seed.sql
    echo "  ✅ Material norms importovány"
else
    echo "  ⚠️  Material norms SQL nenalezen, přeskakuji"
fi

echo ""
echo "=========================================="
echo "✅ HOTOVO!"
echo "=========================================="
echo ""
echo "Nová struktura:"
echo "  - 12 MaterialGroups (OCEL-KONS, OCEL-AUTO, NEREZ, HLINIK, ...)"
echo "  - ~38 MaterialPriceCategories (detailní kombinace materiál+tvar)"
echo "  - ~120 MaterialPriceTiers (3 tiers na kategorii)"
echo "  - 83 MaterialNorms (W.Nr. s kompletními normami)"
echo ""
echo "💡 Zkontroluj v admin UI: http://localhost:8000/admin/material-catalog"
echo ""
