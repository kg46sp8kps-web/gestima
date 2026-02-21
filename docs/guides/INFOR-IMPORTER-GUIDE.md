# Infor Generic Importer — Developer Guide

**ADR:** [ADR-031](../ADR/ADR-031-infor-generic-importer.md)

---

## Architecture

`InforImporterBase<T>` — abstract base class, config-driven field mappings, automatic validation + duplicate detection, M:N relationship support.

---

## Import Flow

```
Infor IDO rows
  → FieldMapping (source → target, optional transform/fallback)
  → map_row_custom() (custom logic: FK lookups, shape detection)
  → validate_mapped_row() (required fields + duplicates)
  → preview_import() → staged rows with status
  → execute_import() → create_entity() / update_entity()
```

---

## Abstract Methods (MUST implement)

| Method | Purpose |
|--------|---------|
| `get_config() -> InforImporterConfig` | FieldMappings, IDO name, duplicate_check_field |
| `map_row_custom(row, basic_mapped, db)` | FK lookups, shape parsing, transforms |
| `create_entity(mapped_data, db) -> T` | Instantiate + number generation |
| `check_duplicate(mapped_data, db) -> Optional[T]` | Query by unique key |

## Optional Methods

| Method | Default |
|--------|---------|
| `update_entity(existing, mapped_data, db)` | no-op (logs warning) |
| `validate_mapped_row(mapped_data, db)` | checks required fields + duplicates |

---

## FieldMapping Options

```python
FieldMapping("Item", "code", required=True)
FieldMapping("UnitMeasure", "unit", fallback_fields=["UM", "Unit"])
FieldMapping("IsActive", "is_active", transform=lambda x: x in ["Y", "1"])
```

---

## Router Endpoint Pattern

```python
@router.post("/import/{entity}/preview", response_model=PreviewResponse)
async def preview(data: PreviewRequest, db=Depends(get_db), user=Depends(require_role([UserRole.ADMIN]))):
    importer = EntityImporter()
    return await importer.preview_import(data.rows, db)

@router.post("/import/{entity}/execute", response_model=ExecuteResponse)
async def execute(data: ExecuteRequest, db=Depends(get_db), user=Depends(require_role([UserRole.ADMIN]))):
    importer = EntityImporter()
    return await importer.execute_import([r.dict() for r in data.rows], db)
```

---

## Batch Config

- Preview: 5000 rows/batch
- Execute: 2000 rows/batch
- `postWithRetry()` on 429

---

## Performance Rules

- Batch number generation: `NumberGenerator.generate_*_batch(db, len(rows))` — never generate one-by-one in loop
- Preload reference data (MaterialGroups, WC map) once before loop, lookup in-memory dict
- FK constraint errors: ensure parent entities exist before import

---

## Error Handling Rules

- `duplicate_check_field` must match field name in `mapped_data` (not Infor field name)
- `validate_mapped_row()` — call `await super().validate_mapped_row(...)` first, then add custom checks
- Do NOT call `db.begin()` manually — base class handles transactions
- FK missing → ERROR, block import (no silent fallback)

---

## M:N Relationships

```python
async def map_row_custom(self, row, basic_mapped, db):
    ops = await self.client.load_collection("SLOperations", ..., filter=f"Item='{row['Item']}'")
    return {"operations_data": ops["data"]}

async def create_entity(self, mapped_data, db):
    part = Part(...)
    db.add(part)
    await db.flush()  # get part.id before adding children
    for op in mapped_data.get("operations_data", []):
        db.add(PartOperation(part_id=part.id, ...))
    return part
```

---

## Infor Routing Import (SLJobRoutes)

- Default filter: `Type = 'S'` (standard routing, NOT production orders)
- Group by `DerJobItem` (article_number) → Part lookup → Operations UPSERT by seq
- WC Mapper: exact match + prefix fallback (KOO1→KOO→80000016), `warmup_cache()` for batch
- Skip rules: CLO*, CADCAM, ObsDate → `_skip=True`
- Kooperace: KOO* → `is_coop=True`, type="coop", op_time=0, manning=100%
- Times: `operation_time_min = 60 / DerRunMchHrs` (pcs/h → min/pcs), `manning = (Mch/Lbr)*100`
