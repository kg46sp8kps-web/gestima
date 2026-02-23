# ADR-024: MaterialInput 1:N [ACCEPTED]
> Archive: docs/ADR/archive/024-material-input-refactor.md — Claude může požádat o přečtení

## Rozhodnutí
Part nemá material_* sloupce — materiál žije v MaterialInput tabulce (1:N na Part).

## Pattern
- `app/models/material_input.py` — MaterialInput model
- `app/routers/material_inputs_router.py` — CRUD endpointy
- `frontend/src/types/material-input.ts` — TypeScript typy

## Part model — odstraněná pole (v2.1.0, 2026-02-23)
- `length` a `notes` odstraněny z tabulky `parts` (migrace b3c4d5e6f7g8)
- `status` a `source` zůstávají v DB, ale nejsou editovatelné z PartDetailCard
- V PartDetailCard lze editovat pouze: `name`, `article_number`, `drawing_number`, `revision`, `customer_revision`

## Nesmíš
- přidávat material_* sloupce zpět na Part
- hard delete MaterialInput
- přímá vazba Part→MaterialItem bez MaterialInput mezivrstvy
- vracet `length` nebo `notes` na Part model
