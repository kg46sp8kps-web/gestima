# ADR-019: Material Catalog Smart Upward Lookup [PLANNED]
> Archive: docs/ADR/archive/019-material-catalog-smart-lookup.md — Claude může požádat o přečtení

## Rozhodnutí
Smart Upward Lookup — při zadání rozměru najde nejbližší VĚTŠÍ rozměr v katalogu (fyzicky nelze použít menší polotovar než díl).

## Note
Import materiálů z Excelu byl nahrazen Infor importem (ADR-032). Part.material_item_id odstraněn (ADR-024) — materiál nyní přes MaterialInput.

## Pattern
- MaterialItem lookup (planned): `WHERE diameter >= target AND MIN(diameter - target)` per shape type

## Nesmíš
- Vybrat menší rozměr než zadaný
- Ignorovat shape-specific pravidla vyhledávání
