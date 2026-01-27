-- Migration: Zjednodušení MaterialGroup (13 → 6 základních typů)
-- Datum: 2026-01-26
-- Účel: Redukovat MaterialGroup na základní typy materiálů

BEGIN TRANSACTION;

-- ========== KROK 1: Vytvoření nových MaterialGroup (6 záznamů) ==========
INSERT INTO material_groups (code, name, density, created_at, updated_at, created_by, updated_by, version)
VALUES
    ('OCEL', 'Ocel konstrukční a legovaná', 7.85, datetime('now'), datetime('now'), 'migration', 'migration', 1),
    ('NEREZ', 'Nerezová ocel (austenit.)', 7.95, datetime('now'), datetime('now'), 'migration', 'migration', 1),
    ('HLINIK', 'Hliníkové slitiny', 2.70, datetime('now'), datetime('now'), 'migration', 'migration', 1),
    ('MOSAZ', 'Mosaz a bronz', 8.45, datetime('now'), datetime('now'), 'migration', 'migration', 1),
    ('PLASTY', 'Technické plasty (PA, POM)', 1.30, datetime('now'), datetime('now'), 'migration', 'migration', 1),
    ('OCEL-NASTROJOVA', 'Ocel nástrojová', 7.85, datetime('now'), datetime('now'), 'migration', 'migration', 1);

-- Zobrazit nové IDs
SELECT '=== Nové MaterialGroup ===' as log;
SELECT id, code, name, density FROM material_groups WHERE created_by = 'migration';

-- ========== KROK 2: Přidat material_group_id do MaterialPriceCategory ==========
ALTER TABLE material_price_categories ADD COLUMN material_group_id INTEGER REFERENCES material_groups(id);

-- ========== KROK 3: Update MaterialPriceCategory s novými group IDs ==========
UPDATE material_price_categories
SET material_group_id = (SELECT id FROM material_groups WHERE code = 'OCEL' AND created_by = 'migration'),
    updated_at = datetime('now'),
    updated_by = 'migration',
    version = version + 1
WHERE code IN ('OCEL-KRUHOVA', 'OCEL-PLOCHA', 'OCEL-DESKY', 'OCEL-TRUBKA');

UPDATE material_price_categories
SET material_group_id = (SELECT id FROM material_groups WHERE code = 'NEREZ' AND created_by = 'migration'),
    updated_at = datetime('now'),
    updated_by = 'migration',
    version = version + 1
WHERE code IN ('NEREZ-KRUHOVA', 'NEREZ-PLOCHA');

UPDATE material_price_categories
SET material_group_id = (SELECT id FROM material_groups WHERE code = 'HLINIK' AND created_by = 'migration'),
    updated_at = datetime('now'),
    updated_by = 'migration',
    version = version + 1
WHERE code IN ('HLINIK-KRUHOVA', 'HLINIK-PLOCHA', 'HLINIK-DESKY');

UPDATE material_price_categories
SET material_group_id = (SELECT id FROM material_groups WHERE code = 'MOSAZ' AND created_by = 'migration'),
    updated_at = datetime('now'),
    updated_by = 'migration',
    version = version + 1
WHERE code = 'MOSAZ-BRONZ';

UPDATE material_price_categories
SET material_group_id = (SELECT id FROM material_groups WHERE code = 'PLASTY' AND created_by = 'migration'),
    updated_at = datetime('now'),
    updated_by = 'migration',
    version = version + 1
WHERE code IN ('PLASTY-TYCE', 'PLASTY-DESKY');

UPDATE material_price_categories
SET material_group_id = (SELECT id FROM material_groups WHERE code = 'OCEL-NASTROJOVA' AND created_by = 'migration'),
    updated_at = datetime('now'),
    updated_by = 'migration',
    version = version + 1
WHERE code = 'OCEL-NASTROJOVA';

-- ========== KROK 4: Update MaterialNorm (11xxx, C45, S235, 42CrMo4, 16MnCr5 → OCEL) ==========
UPDATE material_norms
SET material_group_id = (SELECT id FROM material_groups WHERE code = 'OCEL' AND created_by = 'migration'),
    updated_at = datetime('now'),
    updated_by = 'migration',
    version = version + 1
WHERE material_group_id IN (
    SELECT id FROM material_groups WHERE code IN ('11xxx', 'C45', 'S235', '42CrMo4', '16MnCr5') AND created_by != 'migration'
);

UPDATE material_norms
SET material_group_id = (SELECT id FROM material_groups WHERE code = 'NEREZ' AND created_by = 'migration'),
    updated_at = datetime('now'),
    updated_by = 'migration',
    version = version + 1
WHERE material_group_id IN (
    SELECT id FROM material_groups WHERE code IN ('X5CrNi18-10', 'X2CrNiMo17-12-2') AND created_by != 'migration'
);

UPDATE material_norms
SET material_group_id = (SELECT id FROM material_groups WHERE code = 'HLINIK' AND created_by = 'migration'),
    updated_at = datetime('now'),
    updated_by = 'migration',
    version = version + 1
WHERE material_group_id IN (
    SELECT id FROM material_groups WHERE code IN ('6060', '7075') AND created_by != 'migration'
);

UPDATE material_norms
SET material_group_id = (SELECT id FROM material_groups WHERE code = 'MOSAZ' AND created_by = 'migration'),
    updated_at = datetime('now'),
    updated_by = 'migration',
    version = version + 1
WHERE material_group_id IN (
    SELECT id FROM material_groups WHERE code IN ('CuZn37', 'CuZn39Pb3') AND created_by != 'migration'
);

UPDATE material_norms
SET material_group_id = (SELECT id FROM material_groups WHERE code = 'PLASTY' AND created_by = 'migration'),
    updated_at = datetime('now'),
    updated_by = 'migration',
    version = version + 1
WHERE material_group_id IN (
    SELECT id FROM material_groups WHERE code IN ('PA6', 'POM') AND created_by != 'migration'
);

-- ========== KROK 5: Update MaterialItem ==========
UPDATE material_items
SET material_group_id = (SELECT id FROM material_groups WHERE code = 'OCEL' AND created_by = 'migration'),
    updated_at = datetime('now'),
    updated_by = 'migration',
    version = version + 1
WHERE material_group_id IN (
    SELECT id FROM material_groups WHERE code IN ('11xxx', 'C45', 'S235', '42CrMo4', '16MnCr5') AND created_by != 'migration'
);

UPDATE material_items
SET material_group_id = (SELECT id FROM material_groups WHERE code = 'NEREZ' AND created_by = 'migration'),
    updated_at = datetime('now'),
    updated_by = 'migration',
    version = version + 1
WHERE material_group_id IN (
    SELECT id FROM material_groups WHERE code IN ('X5CrNi18-10', 'X2CrNiMo17-12-2') AND created_by != 'migration'
);

UPDATE material_items
SET material_group_id = (SELECT id FROM material_groups WHERE code = 'HLINIK' AND created_by = 'migration'),
    updated_at = datetime('now'),
    updated_by = 'migration',
    version = version + 1
WHERE material_group_id IN (
    SELECT id FROM material_groups WHERE code IN ('6060', '7075') AND created_by != 'migration'
);

UPDATE material_items
SET material_group_id = (SELECT id FROM material_groups WHERE code = 'MOSAZ' AND created_by = 'migration'),
    updated_at = datetime('now'),
    updated_by = 'migration',
    version = version + 1
WHERE material_group_id IN (
    SELECT id FROM material_groups WHERE code IN ('CuZn37', 'CuZn39Pb3') AND created_by != 'migration'
);

UPDATE material_items
SET material_group_id = (SELECT id FROM material_groups WHERE code = 'PLASTY' AND created_by = 'migration'),
    updated_at = datetime('now'),
    updated_by = 'migration',
    version = version + 1
WHERE material_group_id IN (
    SELECT id FROM material_groups WHERE code IN ('PA6', 'POM') AND created_by != 'migration'
);

-- ========== KROK 6: Soft delete starých MaterialGroup ==========
UPDATE material_groups
SET deleted_at = datetime('now'),
    deleted_by = 'migration'
WHERE code IN ('11xxx', 'C45', 'S235', '42CrMo4', '16MnCr5', 'X5CrNi18-10', 'X2CrNiMo17-12-2', '6060', '7075', 'CuZn37', 'CuZn39Pb3', 'PA6', 'POM')
  AND created_by != 'migration';

-- ========== Ověření ==========
SELECT '=== MaterialGroup (po migraci) ===' as log;
SELECT id, code, name, density FROM material_groups WHERE deleted_at IS NULL ORDER BY code;

SELECT '=== MaterialPriceCategory (s material_group_id) ===' as log;
SELECT mpc.id, mpc.code, mg.code as group_code
FROM material_price_categories mpc
JOIN material_groups mg ON mpc.material_group_id = mg.id
WHERE mpc.deleted_at IS NULL
ORDER BY mpc.code;

SELECT '=== Počet záznamů ===' as log;
SELECT
    (SELECT COUNT(*) FROM material_groups WHERE deleted_at IS NULL) as groups_count,
    (SELECT COUNT(*) FROM material_norms WHERE deleted_at IS NULL) as norms_count,
    (SELECT COUNT(*) FROM material_items WHERE deleted_at IS NULL) as items_count;

COMMIT;
