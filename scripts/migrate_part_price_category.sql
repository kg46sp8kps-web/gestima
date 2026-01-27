-- Migration: Přidat Part.price_category_id FK
-- Datum: 2026-01-26
-- Účel: Part přímo odkazuje na MaterialPriceCategory (místo MaterialItem)

BEGIN TRANSACTION;

-- ========== KROK 1: Přidat price_category_id do parts ==========
ALTER TABLE parts ADD COLUMN price_category_id INTEGER REFERENCES material_price_categories(id);

-- ========== KROK 2: Migrovat data z material_item_id ==========
-- Pro existující parts: najít price_category_id z material_item
UPDATE parts
SET price_category_id = (
    SELECT mi.price_category_id
    FROM material_items mi
    WHERE mi.id = parts.material_item_id
),
    updated_at = datetime('now'),
    updated_by = 'migration',
    version = version + 1
WHERE material_item_id IS NOT NULL;

-- ========== KROK 3: Ověření ==========
SELECT '=== Parts s price_category_id ===' as log;
SELECT
    p.id,
    p.part_number,
    p.material_item_id as old_item_id,
    p.price_category_id as new_category_id,
    mpc.code as category_code
FROM parts p
LEFT JOIN material_price_categories mpc ON p.price_category_id = mpc.id
WHERE p.deleted_at IS NULL
LIMIT 10;

SELECT '=== Statistika ===' as log;
SELECT
    COUNT(*) as total_parts,
    COUNT(price_category_id) as with_category,
    COUNT(material_item_id) as with_old_item
FROM parts
WHERE deleted_at IS NULL;

COMMIT;
