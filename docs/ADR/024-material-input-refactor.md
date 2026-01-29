# ADR-024: MaterialInput Refactor

**Status:** Implementováno ✅
**Datum:** 2026-01-29
**Verze:** 1.8.0
**Autor:** Roy (AI Assistant)

---

## Context

Part model obsahoval 8 polí pro materiál přímo na sobě:
- `material_item_id`, `price_category_id`
- `stock_shape`, `stock_diameter`, `stock_length`, `stock_width`, `stock_height`, `stock_wall_thickness`

**Problémy:**
1. Part nemohl mít více materiálových vstupů (svařence, sestavy)
2. Materiál nebyl navázán na operace (nebylo jasné kdy se spotřebovává)
3. Part byl "tlustý" model (fat model anti-pattern)
4. Komplikace pro budoucí BOM (v3.0 PLM)

**Trigger:**
- Diskuze o workflow zakládání dílu
- Návrh "Lean Part" architektury
- Příprava na BOM model (VISION v3.0)

---

## Decision

**Přesun materiálu do samostatné tabulky `material_inputs` s M:N vztahem k operacím.**

### DB Schema

```sql
-- Nová tabulka
CREATE TABLE material_inputs (
    id INTEGER PRIMARY KEY,
    part_id INTEGER NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL DEFAULT 0,

    price_category_id INTEGER NOT NULL REFERENCES material_price_categories(id),
    material_item_id INTEGER REFERENCES material_items(id),

    stock_shape VARCHAR(50) NOT NULL,
    stock_diameter FLOAT,
    stock_length FLOAT,
    stock_width FLOAT,
    stock_height FLOAT,
    stock_wall_thickness FLOAT,

    quantity INTEGER NOT NULL DEFAULT 1,
    notes VARCHAR(500),

    -- AuditMixin
    version, created_at, updated_at, created_by, updated_by, deleted_at
);

-- M:N association table
CREATE TABLE material_operation_link (
    material_input_id INTEGER REFERENCES material_inputs(id) ON DELETE CASCADE,
    operation_id INTEGER REFERENCES operations(id) ON DELETE CASCADE,
    consumed_quantity INTEGER,  -- Volitelné: kolik z materiálu se spotřebovává v TÉTO operaci
    PRIMARY KEY (material_input_id, operation_id)
);

-- Změny v Part
ALTER TABLE parts ADD COLUMN revision VARCHAR(2) DEFAULT 'A' NOT NULL;
ALTER TABLE parts ADD COLUMN customer_revision VARCHAR(50);
ALTER TABLE parts ADD COLUMN status VARCHAR(20) DEFAULT 'active' NOT NULL;

ALTER TABLE parts DROP COLUMN material_item_id;
ALTER TABLE parts DROP COLUMN price_category_id;
ALTER TABLE parts DROP COLUMN stock_shape;
ALTER TABLE parts DROP COLUMN stock_diameter;
ALTER TABLE parts DROP COLUMN stock_length;
ALTER TABLE parts DROP COLUMN stock_width;
ALTER TABLE parts DROP COLUMN stock_height;
ALTER TABLE parts DROP COLUMN stock_wall_thickness;
```

### Relationships

```python
Part
├── material_inputs: List[MaterialInput] (1:N, cascade)
└── operations: List[Operation] (1:N, cascade)

MaterialInput
├── part: Part (N:1)
├── operations: List[Operation] (M:N via material_operation_link)
├── price_category: MaterialPriceCategory (N:1)
└── material_item: MaterialItem (N:1, optional)

Operation
├── part: Part (N:1)
├── material_inputs: List[MaterialInput] (M:N via material_operation_link)
└── features: List[Feature] (1:N, cascade)
```

---

## Consequences

### ✅ Pozitivní

1. **Lean Part model** - Part je čistě identita (part_number, name, revision)
2. **Flexibilita** - Díl může mít 1-N materiálových vstupů
3. **M:N vazba** - Materiál může být spotřebován ve více operacích
4. **Nezávislost** - MaterialInput existuje i když Part nemá operace (nakupované díly)
5. **BOM ready** - Připraveno pro v3.0 PLM (BOM → MaterialInput)
6. **Revize** - Přidána pole `revision` (interní) + `customer_revision` (zákaznická)

### ⚠️ Negativní

1. **Breaking change** - Všechny existující dotazy na Part.material_* musí být aktualizovány
2. **Migration complexity** - Data musela být přesunuta (ale DB byla prázdná)
3. **JOINy** - Výpočet ceny materiálu vyžaduje JOIN přes MaterialInput (ale indexed FK = fast)

### 🔄 Mitigace

- **Backward compatibility:** DEPRECATED `calculate_stock_cost_from_part()` funkce zachována
- **Performance:** Indexes na `material_inputs(part_id)`, `material_inputs(part_id, seq)`, `material_operation_link(*)`
- **API:** Nové endpointy `/api/material-inputs/*` s CRUD + link/unlink

---

## Edge Cases Covered

| Use Case | Řešení |
|----------|--------|
| Díl bez operací (nakupovaný díl) | ✅ MaterialInput existuje samostatně |
| Díl bez materiálu (montáž) | ✅ Operations existují bez MaterialInputs |
| 1 materiál → N operací | ✅ M:N link table |
| N materiálů → 1 operace | ✅ M:N link table |
| Materiál bez operace | ✅ Link table prázdný |
| Přeřazení operací (seq změna) | ✅ Vazba na Operation.id (ne seq) |
| Smazání operace | ✅ CASCADE na link table, MaterialInput zůstává |
| Kalkulace | ✅ `sum(material_inputs.cost) + sum(operations.cost)` |

---

## Implementation

### Files Changed

**Models:**
- `app/models/material_input.py` - Nový model + schemas ✅
- `app/models/part.py` - Removed material fields, added revision fields ✅
- `app/models/operation.py` - Added `material_inputs` relationship ✅
- `app/models/enums.py` - Added `PartStatus` enum ✅

**API:**
- `app/routers/material_inputs_router.py` - Nový router (CRUD + link/unlink) ✅
- `app/gestima_app.py` - Router registration ✅

**Services:**
- `app/services/price_calculator.py` - Nové funkce:
  - `calculate_stock_cost_from_material_input()` ✅
  - `calculate_part_material_cost()` ✅

**Database:**
- `alembic/versions/a8b9c0d1e2f3_material_input_refactor.py` - Migration ✅

**Frontend (TODO):**
- `frontend/src/views/workspace/modules/PartMaterialModule.vue` - Update pro MaterialInput API
- `frontend/src/views/workspace/modules/PartOperationsModule.vue` - Zobrazení linked materials

---

## API Endpoints

```http
# CRUD
GET    /api/material-inputs/parts/{part_id}         # List materiálů pro díl
GET    /api/material-inputs/{material_id}           # Detail materiálu
POST   /api/material-inputs                         # Vytvoření materiálu
PUT    /api/material-inputs/{material_id}           # Aktualizace (optimistic lock)
DELETE /api/material-inputs/{material_id}           # Smazání (soft delete)

# M:N Linking
POST   /api/material-inputs/{material_id}/link-operation/{operation_id}     # Přiřadit k operaci
DELETE /api/material-inputs/{material_id}/unlink-operation/{operation_id}   # Odebrat vazbu
GET    /api/material-inputs/operations/{operation_id}/materials             # Materiály operace
```

---

## Migration Notes

- **DB stav:** Prázdná databáze → žádná data migrace
- **Alembic:** Version `7ddc9817b579` → `a8b9c0d1e2f3`
- **Downgrade:** Podporováno (obnoví Part.material_* fields)

---

## Future Considerations

### v3.0 PLM - BOM Integration

```python
# Budoucí migrace na BOM
class BOM(Base):
    id = Column(Integer, primary_key=True)
    part_id = Column(Integer, ForeignKey("parts.id"))

class BOMItem(Base):
    id = Column(Integer, primary_key=True)
    bom_id = Column(Integer, ForeignKey("boms.id"))

    # Polymorphic
    item_type = Column(Enum("material", "part"))
    material_input_id = Column(Integer, ForeignKey("material_inputs.id"))  # ← Reuse!
    sub_part_id = Column(Integer, ForeignKey("parts.id"))

    quantity = Column(Integer, default=1)
```

**Migration path:** MaterialInput → BOMItem (reference, ne data kopie)

---

## Related ADRs

- **ADR-011:** Two-Tier Material Model (MaterialGroup → MaterialPriceCategory)
- **ADR-014:** Dynamic Price Tiers (tier selection by weight)
- **ADR-017:** 8-digit random numbering (Part: 10XXXXXX)
- **ADR-021:** WorkCenter model (unified machines)
- **ADR-022:** BatchSet model (frozen pricing)

---

## Status

✅ **Implementováno:** 2026-01-29
✅ **Cleanup Fixed:** 2026-01-29 (v1.9.2)
🚧 **Frontend:** Pending
📝 **Tests:** Pending

---

## Post-Implementation Cleanup (2026-01-29 v1.9.2)

**Issues Found:**

1. **11× deprecated `Part.material_item` usage** - Code still referenced old relationship after refactor
   - **Impact:** 500 Internal Server Error on `/api/parts/` endpoint
   - **Root cause:** Incomplete code migration - only models updated, not queries
   - **Fix:** Replaced all `selectinload(Part.material_item)` → `selectinload(Part.material_inputs).selectinload(MaterialInput.material_item)`

2. **Orphaned `MaterialItem.parts` relationship** - No corresponding FK in Part model
   - **Impact:** SQLAlchemy mapping error on startup (circular import + no join condition)
   - **Fix:** Removed relationship from MaterialItem (one-way reference not needed)

3. **Part.status Enum mismatch** - SQLAlchemy Enum vs SQLite VARCHAR
   - **Impact:** `LookupError: 'active' is not among defined enum values (DRAFT, ACTIVE, ARCHIVED)`
   - **Root cause:** Migration created `VARCHAR(20)`, model used `Enum(PartStatus)` → Python-side validation looked for uppercase NAMES but DB had lowercase values
   - **Fix:** Changed model to `String(20)` (match migration), Pydantic handles validation

**Lessons:**
- ⚠️ Breaking changes require **grep for old patterns** across entire codebase
- ⚠️ SQLite + SQLAlchemy `Enum(str, Enum)` = broken (use `String` + Pydantic validation)
- ⚠️ Migration vs Model mismatch = runtime error (always verify types match!)

---

**Závěr:** MaterialInput refactor úspěšně oddělil materiál od Part modelu, umožnil flexibilní M:N vazby s operacemi a připravil základ pro BOM v v3.0 PLM. Post-cleanup fix zajistil konzistenci mezi migrací a kódem.
