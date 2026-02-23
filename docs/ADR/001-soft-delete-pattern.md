# ADR-001: Soft Delete Pattern [ACCEPTED]
> Archive: docs/ADR/archive/001-soft-delete-pattern.md — Claude může požádat o přečtení

## Rozhodnutí
Záznamy se nikdy fyzicky nemažou — označí se `deleted_at` timestampem.

## Pattern
- `app/db_helpers.py` — `soft_delete(db, instance, username)`
- `app/database.py` — `AuditMixin` (deleted_at, deleted_by fields)

## Nesmíš
- Volat `db.delete()` nebo `session.delete()`
- Psát přímé DELETE SQL
