# ADR-004: Audit + WAL + Optimistic Locking

**Status:** Implemented (2026-01-22)

## Context

Všechny modely potřebují audit trail, SQLite vyžaduje WAL pro concurrent přístup a optimistic locking zabraňuje conflictům při souběžných editacích.

## Decision

Implementovat `AuditMixin`, WAL mode a optimistic locking jako automatickou infrastrukturu — vývojáři na to nemusí myslet.

## Key Files

- `app/database.py` — `AuditMixin`, `init_db()` (WAL PRAGMA), SQLAlchemy event listener
- `app/db_helpers.py` — `soft_delete()`, `restore()`, `get_active()`, `get_all_active()`
- `tests/test_audit_infrastructure.py`

## Models

```python
class AuditMixin:
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    created_by = Column(String)
    updated_by = Column(String)
    deleted_at = Column(DateTime)   # NULL = aktivní (soft delete)
    deleted_by = Column(String)
    version = Column(Integer)       # Optimistic locking — auto-increment on UPDATE
```

**WAL PRAGMAs:** `journal_mode=WAL`, `synchronous=NORMAL`, `cache_size=-64000`

## Usage

```python
# Soft delete
await soft_delete(db, part, deleted_by="jan@firma.cz")

# Conflict detection (frontend posílá expected_version)
if part.version != expected_version:
    raise HTTPException(409, "Díl byl upraven jiným uživatelem")
```

## Consequences

- Audit fieldy a WAL jsou transparentní — žádný boilerplate v modelech
- `version` se inkrementuje automaticky přes SQLAlchemy event listener
- Soft delete zachovává historii; `get_all_active()` filtruje `deleted_at IS NULL`
- Migrace existující DB: smaž DB a znovu spusť (nebo alembic migration)

## References

- ADR-001: Soft Delete Pattern
- ADR-003: Integer ID vs UUID
