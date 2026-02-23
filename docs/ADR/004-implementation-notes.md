# ADR-004: Audit + WAL + Optimistic Locking [ACCEPTED]
> Archive: docs/ADR/archive/004-implementation-notes.md — Claude může požádat o přečtení

## Rozhodnutí
Každý model dědí AuditMixin (audit trail + version), SQLite běží v WAL mode, každý update vyžaduje `version` field.

## Pattern
- `app/database.py` — `AuditMixin`, `init_db()` (WAL PRAGMA + event listener)
- Každý `XyzUpdate` schema — `version: int` povinně

## Nesmíš
- Vytvořit model bez AuditMixin
- Provést update bez version check
- Volat raw `db.commit()` (použij `safe_commit`)
