# ADR-022: BatchSet Model (Sady cen)

**Status:** Prijato
**Date:** 2026-01-28

---

## Context

Uzivatele potrebuji seskupovat cenove davky (Batch) do pojmenovanych sad, ktere lze najednou zmrazit (snapshot cen) a udrzovat jejich historii per-Part. Stavajici model mel pouze individualne zmrazitelne batche (ADR-012) bez seskupeni.

---

## Decision

Pridat novou tabulku `batch_sets` s FK `batch_set_id` na existujici `Batch`.

### Model

```python
class BatchSet(Base, AuditMixin):
    __tablename__ = "batch_sets"
    id           = Column(Integer, primary_key=True)
    set_number   = Column(String(8), unique=True, nullable=False, index=True)  # 35XXXXXX
    part_id      = Column(Integer, ForeignKey("parts.id", ondelete="SET NULL"), nullable=True)
    name         = Column(String(100), nullable=False)   # auto: "2026-01-28 14:35"
    status       = Column(String(20), default="draft")   # draft | frozen
    frozen_at    = Column(DateTime, nullable=True)
    frozen_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
```

Klic:
- `part_id` nullable + `ondelete="SET NULL"` — historicke sady zustanou po smazani Part
- `name` = timestamp `"YYYY-MM-DD HH:MM"` (auto-generovany, ISO-sortable)
- `Batch.batch_set_id` nullable — legacy batches bez sady muzou zustat

### API Endpoints

```
GET    /api/pricing/part/{part_id}/batch-sets     # seznam sad pro dil
POST   /api/pricing/batch-sets                    # nova prazda sada  { part_id }
POST   /api/pricing/batch-sets/{id}/freeze        # atomicke zmrazeni vsech batchu
DELETE /api/pricing/batch-sets/{id}               # soft delete (ADMIN only)
POST   /api/pricing/batch-sets/{id}/batches       # pridat batch  { quantity }
DELETE /api/pricing/batch-sets/{id}/batches/{bid} # odebrat batch
POST   /api/pricing/batch-sets/{id}/recalculate   # prepocet cen
```

### Freeze logika

Freeze je atomicka — vsechny batchy v sade dostanou `is_frozen=True` + `snapshot_data` v jednom commitu. Prazdnou sadu nelze zmrazit (HTTP 400), znovu zmrazenou take ne (HTTP 409).

### Soft delete

Soft delete sady i vsech jejich batchu najednou. Pouze ADMIN (`require_role([UserRole.ADMIN])`).

---

## Key Files

- `app/models/batch_set.py` — BatchSet model
- `app/schemas/batch_set.py` — BatchSetCreate, BatchSetResponse
- `app/services/batch_set_service.py` — freeze, delete logika
- `app/routers/pricing_router.py` — endpointy
- `alembic/versions/*_add_batch_set.py` — migrace (nova tabulka + sloupec na Batch)

---

## Consequences

- Atomicke zmrazeni cele sady cen
- Historie cenove sady per-Part (vice sad, kazda s timestampem)
- Pripraveno pro Quote modul (VISION v2.0) a Workspace (ADR-023)
- Nova tabulka → JOIN pri nacteni batchu
- Legacy batches (batch_set_id=NULL) mozno smazat bez migrace

---

## References

- ADR-012: Minimal Snapshot Pattern (freeze logika)
- ADR-023: Workspace Module Architecture
