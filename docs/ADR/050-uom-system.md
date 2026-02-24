# ADR-050: UOM System — (uom, conv_uom, conv_factor) pattern [ACCEPTED]
> Archive: docs/ADR/archive/050-uom-system.md — Claude může požádat o přečtení

## Rozhodnutí
Trojice `(uom, conv_uom, conv_factor)` na MaterialItem nahrazuje typovaná konverzní pole (`weight_per_meter`) a sjednocuje výpočet váhy s explicitní prioritou: katalog → objem.

## Pattern
- `app/models/enums.py` — `UnitOfMeasure` enum (ks/kg/m/mm)
- `app/services/unit_converter.py` — pure functions: `to_base_uom()`, `volume_to_weight()`
- `app/models/material.py` — MaterialItem: `uom` (default=kg), `conv_uom` (nullable), `conv_factor` (nullable)
- `app/models/part.py` — Part: `uom` (=ks), `unit_weight` (kg/ks pro Infor)
- `app/services/material_calculator.py` — `MaterialCalculation.weight_source` + katalogová priorita
- `app/services/price_calculator.py` — `MaterialCost.weight_source` + katalogová priorita
- `alembic/versions/c3d4e5f6g7h8_add_uom_fields.py` — data migrace: `weight_per_meter` → `conv_factor`
- `frontend/src/types/material-item.ts` — `uom`, `conv_uom`, `conv_factor`
- `frontend/src/types/material-input.ts` — `weight_source: 'catalog' | 'volume' | null`
- `TileWorkMaterials.vue` — badge "katalog" (zelená) / "objem" (šedá) dle `weight_source`

## Sémantika
`conv_factor` = kolik `uom` jednotek tvoří 1 `conv_uom` (číslo bez jednotky):
- D50 tyč: `uom='kg'`, `conv_uom='m'`, `conv_factor=15.41` → "1 m = 15.41 kg"
- Priorita výpočtu: **1. katalog** (conv_factor nastaven) → **2. objem** (hustota × geometrie)

## Nesmíš
- Přidávat nová typovaná konverzní pole (weight_per_X, density_per_Y) — vždy použij `conv_factor`
- Počítat váhu jinak než přes `unit_converter.py` (single source of truth)
- Odstraňovat `weight_per_meter` bez separátní migrace (backwards compat)
