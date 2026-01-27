-- Migration: Přidat Batch material snapshot fields
-- Datum: 2026-01-27
-- Účel: ADR-017 - Hybrid material snapshot (fast lookup + audit trail)
-- Důvod: Modal potřebuje zobrazit "13500 Kč (90 Kč/kg)", batch potřebuje frozen prices

BEGIN TRANSACTION;

-- ========== KROK 1: Přidat material snapshot fields do batches ==========
ALTER TABLE batches ADD COLUMN material_weight_kg REAL;
ALTER TABLE batches ADD COLUMN material_price_per_kg REAL;

-- ========== KROK 2: Ověření ==========
SELECT '=== Batches tabulka po migraci ===' as log;
SELECT
    b.id,
    b.part_id,
    b.quantity,
    b.material_cost,
    b.material_weight_kg,
    b.material_price_per_kg
FROM batches b
WHERE b.deleted_at IS NULL
LIMIT 5;

SELECT '=== Migrace dokončena. Spusť batch recalculation pro naplnění hodnot. ===' as log;

COMMIT;
