# ADR-012: Minimal Snapshot Pattern (Zmrazení cen)

**Status:** Accepted (2026-01-24)

## Context

Změna ceny materiálu v `MaterialItem` přepočítá ceny starých nabídek — nabídka z minulého měsíce ukazuje jinou cenu. ERP standard: jednou vydaná nabídka = zmrazená cena.

## Decision

**Minimal Snapshot** — při zmrazení batche uložit pouze finální ceny + metadata do JSON pole.
Žádný full snapshot celé struktury (díl + operace), jen to co se mění: ceny.

## Key Files

- `app/models/batch.py` — freeze fields + `snapshot_data` JSON
- `app/services/snapshot_service.py` — `create_batch_snapshot()`, `get_batch_costs()`
- `app/routers/batches_router.py` — `POST /{id}/freeze`, `POST /{id}/clone`
- `tests/test_snapshots.py` — 8 testů

## Model

```python
class Batch(Base, AuditMixin):
    is_frozen         = Column(Boolean, default=False, index=True)
    frozen_at         = Column(DateTime, nullable=True)
    frozen_by_id      = Column(Integer, ForeignKey("users.id"), nullable=True)
    snapshot_data     = Column(JSON, nullable=True)         # costs + metadata
    unit_price_frozen = Column(Float, nullable=True, index=True)   # pro reporty
    total_price_frozen = Column(Float, nullable=True)
```

**Snapshot JSON struktura:**
```json
{
  "frozen_at": "2026-01-24T14:30:00",
  "frozen_by": "admin",
  "costs": { "material_cost": 250.0, "machining_cost": 180.0, "unit_cost": 480.0 },
  "metadata": { "part_number": "DIL-001", "material_price_per_kg": 80.0 }
}
```

## Rules

- Zmrazený batch: **HTTP 403** na editaci, soft delete místo hard delete
- `get_batch_costs()`: vrací ze snapshotu pokud `is_frozen`, jinak LIVE ceny
- Clone (`POST /{id}/clone`): nový nezmrazený batch s LIVE cenami
- Unfreeze: **NEIMPLEMENTOVÁNO** — once frozen, always frozen

## Consequences

- Stabilní historické ceny v nabídkách
- `unit_price_frozen` sloupec umožňuje rychlé SQL reporty (ORDER BY)
- Redundance: ceny jsou na 2 místech (snapshot + redundantní sloupce) — akceptovatelný trade-off
- Staré batches bez snapshotu: `is_frozen=False` → LIVE ceny

## References

- ADR-008: Optimistic Locking
- ADR-011: Material Hierarchy
- ADR-001: Soft Delete Pattern
