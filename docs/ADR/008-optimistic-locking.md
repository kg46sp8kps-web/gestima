# ADR-008: Optimistic Locking Pattern [ACCEPTED]
> Archive: docs/ADR/archive/008-optimistic-locking.md — Claude může požádat o přečtení

## Rozhodnutí
Každý update endpoint vyžaduje `version: int` — odmítne update pokud verze nesouhlasí s DB (concurrent edit protection).

## Pattern
- `app/database.py` — `AuditMixin.version` (auto-increment při každém save)
- Každý `XyzUpdate` schema — `version: int` povinně
- Router: porovnej `db_obj.version == data.version` před save

## Nesmíš
- Provést update bez version check
- Posílat z frontendu update bez `version` pole
