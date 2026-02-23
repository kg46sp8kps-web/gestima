# ADR-024: MaterialInput 1:N [ACCEPTED]
> Archive: docs/ADR/archive/024-material-input-refactor.md — Claude může požádat o přečtení

## Rozhodnutí
Part nemá material_* sloupce — materiál žije v MaterialInput tabulce (1:N na Part).

## Pattern
- `app/models/material_input.py` — MaterialInput model
- `app/routers/material_inputs_router.py` — CRUD endpointy
- `frontend/src/types/material-input.ts` — TypeScript typy

## Nesmíš
- přidávat material_* sloupce zpět na Part
- hard delete MaterialInput
- přímá vazba Part→MaterialItem bez MaterialInput mezivrstvy
