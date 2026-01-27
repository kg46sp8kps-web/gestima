-- Migration: Přidat Part.stock_shape field
-- Datum: 2026-01-26
-- Účel: Part potřebuje vědět jaký typ polotovaru má (pro price_calculator.py)

BEGIN TRANSACTION;

-- ========== KROK 1: Přidat stock_shape do parts ==========
ALTER TABLE parts ADD COLUMN stock_shape TEXT;

-- ========== KROK 2: Migrovat data z material_item.shape ==========
-- Pro existující parts: zkopírovat shape z material_item
UPDATE parts
SET stock_shape = (
    SELECT mi.shape
    FROM material_items mi
    WHERE mi.id = parts.material_item_id
),
    updated_at = datetime('now'),
    updated_by = 'migration',
    version = version + 1
WHERE material_item_id IS NOT NULL;

-- ========== KROK 3: Ověření ==========
SELECT '=== Parts s stock_shape ===' as log;
SELECT
    p.id,
    p.part_number,
    p.stock_shape,
    mi.shape as material_item_shape
FROM parts p
LEFT JOIN material_items mi ON p.material_item_id = mi.id
WHERE p.deleted_at IS NULL
LIMIT 10;

COMMIT;
