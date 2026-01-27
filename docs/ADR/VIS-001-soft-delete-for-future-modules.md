# ADR VIS-001: Soft Delete for Future Modules

**Date:** 2026-01-26
**Status:** Accepted
**Context:** Long-term vision (GESTIMA → Full ERP/MES)
**Related:** ADR-001 (Soft Delete Implementation)

---

## Context

GESTIMA v1.4 používá soft delete (ADR-001) pro audit trail a data recovery. S plánovaným rozšířením na moduly **Quotes, Orders, PLM, MES, Warehouse** vzniká nový požadavek:

**Historical references MUST remain valid even after "deletion".**

### Problémové scénáře (bez soft delete):

1. **Order → Part FK**
   - User "smaže" Part (hard delete)
   - Order.part_id → broken FK
   - Historická objednávka ztratila referenci na díl

2. **WorkOrder → Operation FK**
   - Admin "smaže" Operation z dílu (refaktoring)
   - WorkOrder.operation_id → broken FK
   - Výrobní příkaz ztratil tech. postup

3. **Quote → MaterialItem FK**
   - Supplier discontinued material → admin "smaže" MaterialItem
   - Quote.material_snapshot → broken FK pro audit
   - Nelze zpětně ověřit jaký materiál byl nabídnut

---

## Decision

**ALL entities MUST use soft delete (deleted_at timestamp).**

Toto rozhodnutí rozšiřuje ADR-001 na **všechny budoucí moduly**:
- Quotes, Orders, Order Items
- Work Orders, Work Order Items
- Drawings, Drawing Versions
- Customers, Suppliers (future)
- Tools, Tool Library (future)

---

## Implementation Pattern

### 1. Database Schema (REQUIRED)
```python
# Všechny modely MUSÍ dědit z AuditMixin
class Order(AuditMixin, Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    # ... fields ...
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
```

### 2. Query Filters (AUTOMATIC via AuditMixin)
```python
# AuditMixin má @declared_attr __table_args__ s default filter
# Ale v SELECT queries VŽDY explicitně:
query = select(Order).where(Order.deleted_at.is_(None))
```

### 3. Foreign Keys (STABLE REFERENCES)
```python
# FK references NEPOUŽÍVAJÍ deleted_at filter
# Důvod: historical data musí vidět i "smazané" entity

# ✅ CORRECT: Order vidí Part i když Part.deleted_at je SET
order = await db.get(Order, 123)
part = await db.get(Part, order.part_id)  # Funguje i když deleted
```

### 4. Snapshot Pattern (IMMUTABLE DATA)
```python
# Při "zamčení" reference (Quote approval, Order creation):
# Kopíruj data jako JSON snapshot

order = Order(
    part_id=part.id,  # FK pro relaci
    part_snapshot={   # Snapshot pro audit
        "part_id": part.id,
        "part_number": part.part_number,
        "material": part.material_item.name,
        "price_per_unit": calculated_price,
        "snapshot_date": datetime.utcnow().isoformat()
    }
)
```

**Pravidlo:**
- FK = relační integrita (pro joins)
- Snapshot = audit trail (immutable)
- Pokud Part.deleted → Order.part_id stále platný, ale UI zobrazí "Deleted Part (PN-001)"

---

## Consequences

### Positive
✅ **Historical Integrity:** Orders/Quotes/WorkOrders nikdy neztratí kontext
✅ **Audit Trail:** "Co bylo nabídnuto v lednu 2026?" → vždy odpovíme
✅ **Data Recovery:** Admin může "undelete" omylem smazané entity
✅ **Compliance:** ISO 9001, regulatory audits vyžadují historii
✅ **Consistency:** Jeden pattern pro celý systém

### Negative
❌ **Disk Space:** Smazané záznamy zabírají místo (mitigace: archival po 5 letech)
❌ **Query Complexity:** MUSÍME pamatovat na `deleted_at.is_(None)` filter
❌ **UI Confusion:** User "smazal" díl, ale v DB stále existuje (řešeno UI feedback)

### Neutral
🟡 **Performance:** Minimální dopad (<1% overhead s index na deleted_at)
🟡 **Migration:** SQLite → PostgreSQL migration neovlivněna (pattern funguje v obou)

---

## Validation & Enforcement

### Code Review Checklist
- [ ] Model dědí z `AuditMixin`?
- [ ] SELECT queries mají `deleted_at.is_(None)` filter?
- [ ] DELETE operations používají `soft_delete()` helper?
- [ ] FK relationships zachovány i po soft delete?
- [ ] UI zobrazuje "Deleted" badge pro smazané entity?

### Automated Checks (Future)
```python
# pytest fixture: Ověř že všechny modely mají deleted_at
def test_all_models_have_soft_delete():
    for model in Base.__subclasses__():
        assert hasattr(model, 'deleted_at'), f"{model.__name__} missing soft delete"
```

---

## Alternatives Considered

### 1. Hard Delete with Archival Table
**Pattern:** Před DELETE, COPY to `orders_archive` table
**Rejected:**
- ❌ Duplicita dat (2× schema maintenance)
- ❌ FK relationships broken (archive table nemá FK integrity)
- ❌ Complexity (union queries pro "show all including archived")

### 2. Event Sourcing
**Pattern:** Immutable event log, reconstruct state from events
**Rejected:**
- ❌ Over-engineering pro current scale (in-house, <100 users)
- ❌ Query complexity (projekce event streamu = 10× pomalejší)
- ❌ Learning curve pro team

### 3. Hybrid (Soft Delete for Critical, Hard Delete for Others)
**Pattern:** Orders/WorkOrders soft, Logs/Notifications hard
**Rejected:**
- ❌ Inconsistentní pattern (vysoký cognitive load)
- ❌ Riziko chyby (kdy soft, kdy hard?)
- ❌ Benefit marginální (disk space úspora <1GB/rok)

---

## Examples

### Scenario 1: Part Deleted, Order Remains
```python
# User "smaže" Part
part = await db.get(Part, 123)
await soft_delete(part, db, current_user.id)

# Order stále validní
order = await db.get(Order, 456)
print(order.part_id)  # 123 (FK platný)
print(order.part_snapshot["part_number"])  # "PN-001" (audit data)

# UI zobrazení
part = await db.get(Part, order.part_id)
if part.deleted_at:
    badge = "🗑️ Deleted Part"
else:
    badge = part.part_number
```

### Scenario 2: Quote with Obsolete Material
```python
# Admin "smaže" MaterialItem (discontinued by supplier)
material = await db.get(MaterialItem, 789)
await soft_delete(material, db, current_user.id)

# Quote z minulého roku stále čitelná
quote = await db.get(Quote, 111)
print(quote.material_snapshot)
# {
#   "material_id": 789,
#   "name": "Stainless 316L - ACME Supply",
#   "price_per_kg": 8.50,
#   "snapshot_date": "2025-11-15T10:00:00Z"
# }

# UI: "Material discontinued, but quote valid as-is"
```

### Scenario 3: WorkOrder with Deleted Operation
```python
# Engineer refaktoruje Part → smaže old Operation
operation = await db.get(Operation, 321)
await soft_delete(operation, db, current_user.id)

# WorkOrder z minulého měsíce stále trackuje čas
work_order = await db.get(WorkOrder, 555)
work_order_item = work_order.items[0]
print(work_order_item.operation_id)  # 321 (FK platný)
print(work_order_item.operation_snapshot["type"])  # "turning"

# Operator vidí: "⚠️ Operation deleted, but time tracking preserved"
```

---

## Migration Path (Current → Future)

### v1.4 (Current): ✅ DONE
- AuditMixin implemented
- Part, Operation, Feature, Batch, MaterialItem, Machine → soft delete ready

### v2.0 (Quotes & Orders):
- Quote, QuoteItem → inherit AuditMixin
- Order, OrderItem → inherit AuditMixin
- Customer → inherit AuditMixin
- Add `deleted_at` index to all new tables

### v3.0 (PLM):
- Drawing, DrawingVersion → inherit AuditMixin
- BOM, BOMItem → inherit AuditMixin
- ECN, ECO → inherit AuditMixin (even change requests need history!)

### v4.0 (MES):
- WorkOrder, WorkOrderItem → inherit AuditMixin
- WorkCenter → inherit AuditMixin (machine status history!)
- DowntimeLog → NO soft delete (log data, different pattern)

---

## Related Documents

- [ADR-001: Soft Delete Implementation](001-soft-delete.md) - Original pattern
- [docs/VISION.md](../VISION.md) - Long-term roadmap
- [CLAUDE.md](../../CLAUDE.md#kritická-pravidla) - Rule #7: Soft delete policy

---

## Approval

**Proposed by:** Roy (AI Assistant)
**Date:** 2026-01-26
**Status:** DRAFT → Pending user approval

**Sign-off required from:**
- [ ] Product Owner (long-term vision alignment)
- [ ] Development Team (implementation feasibility)
