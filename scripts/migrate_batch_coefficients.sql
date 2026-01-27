-- Migration: Přidat Batch coefficient breakdown fields
-- Datum: 2026-01-27
-- Účel: ADR-016 - Support nové kalkulace s koeficienty (overhead, margin)
-- Důvod: Batch potřebuje rozpad nákladů: práce, režie, marže, materiál, kooperace

BEGIN TRANSACTION;

-- ========== KROK 1: Přidat coefficient breakdown fields do batches ==========

-- Režie (administrativní náklady na stroje)
ALTER TABLE batches ADD COLUMN overhead_cost REAL DEFAULT 0.0;

-- Marže (zisk na práci)
ALTER TABLE batches ADD COLUMN margin_cost REAL DEFAULT 0.0;

-- ========== KROK 2: Komentář k významu polí ==========
-- machining_cost = operační čas × sazba (BEZ režie/marže)
-- setup_cost = seřizovací čas × sazba (BEZ režie/marže)
-- overhead_cost = (machining + setup) × (overhead_coefficient - 1)
-- margin_cost = (machining + setup + overhead) × (margin_coefficient - 1)
-- material_cost = materiál × stock_coefficient (S koeficientem)
-- coop_cost = kooperace × coop_coefficient (S koeficientem)
-- unit_cost = machining + setup + overhead + margin + material + coop (celkem za kus)

-- ========== KROK 3: Ověření ==========
SELECT '=== Batches tabulka po migraci ===' as log;
SELECT
    b.id,
    b.part_id,
    b.quantity,
    b.machining_cost,
    b.setup_cost,
    b.overhead_cost,
    b.margin_cost,
    b.material_cost,
    b.coop_cost,
    b.unit_cost
FROM batches b
WHERE b.deleted_at IS NULL
LIMIT 5;

SELECT '=== Migrace dokončena. Spusť batch recalculation pro výpočet hodnot. ===' as log;

COMMIT;
