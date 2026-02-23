# ADR-031: Module Defaults Persistence [ACCEPTED]
> Archive: docs/ADR/archive/031-module-defaults-persistence.md — Claude může požádat o přečtení

## Rozhodnutí
Výchozí rozměry modulů jsou per-type (ne globální), uloženy v localStorage, různé pro laptop vs desktop (detekce viewport).

## Pattern
- `frontend/src/stores/` nebo composable — module defaults per type
- localStorage klíče `gestima-module-defaults-{type}`

## Nesmíš
- používat stejné 800×600px defaults pro všechny moduly
- globální single default bez type distinction
- ukládat defaults do Pinia (nepřetrvají přes refresh)
