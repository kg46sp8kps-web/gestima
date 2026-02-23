# ADR-048: Orphan Detection — Soft-Deleted Parts [ACCEPTED]
> Archive: docs/ADR/archive/048-orphan-detection-soft-deleted-parts.md — Claude může požádat o přečtení

## Rozhodnutí
Orphan detekce zahrnuje soubory jejichž FileLinky vedou VÝHRADNĚ na soft-deleted díly — nejen soubory bez FileLinku.

## Pattern
- `app/services/file_service.py` — `find_orphans(include_soft_deleted_parts=True)` parametr

## Nesmíš
- považovat soubor za aktivní jen proto, že má FileLink (Part může být soft-deleted)
- spouštět orphan cleanup bez `include_soft_deleted_parts=True`
- mazat soubory s aktivními FileLinky
