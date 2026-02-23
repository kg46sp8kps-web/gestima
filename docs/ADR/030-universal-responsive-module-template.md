# ADR-030: Universal Responsive Module Template [ACCEPTED]
> Archive: docs/ADR/archive/030-universal-responsive-module-template.md — Claude může požádat o přečtení

## Rozhodnutí
Všechny moduly MUSÍ používat 3-vrstvý template: ModuleCoordinator (<300 LOC) + ListPanel + DetailPanel. Nahrazuje ADR-026.

## Pattern
- `frontend/src/components/tiling/modules/TileMaterials.vue` — referenční koordinátor
- `frontend/src/components/tiling/modules/PartDetailCard.vue` — referenční detail
- Každý soubor max 300 LOC (L-036 rule)

## Nesmíš
- vytvářet modul > 300 LOC
- duplikovat resize/split logiku mimo template
- mít více než 1 koordinátor na modul
- implementovat vlastní layout system
