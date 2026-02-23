# ADR-008: Optimistic Locking Pattern

**Status:** Accepted
**Date:** 2026-01-24
**Context:** P2 Fáze 1 - Ochrana před data loss při concurrent edits

---

## Kontext

**Riziko:** Dva operátoři editují stejný díl současně → jeden přepíše data druhého = **DATA LOSS**.

**Scénář:**
1. Uživatel A otevře díl "DL-123" (version=0) v 10:00
2. Uživatel B otevře tentýž díl "DL-123" (version=0) v 10:01
3. Uživatel A změní stock_diameter na 50mm, uloží → version=1 ✅
4. Uživatel B změní material_group na "automatova_ocel", uloží → **přepíše stock_diameter zpět** ❌

**Problém:**
- Bez version check: poslední update vyhrává (lost update problem)
- Změna od uživatele A je ztracena
- Žádná notifikace že došlo ke konfliktu

**Požadavek:**
- Detekce concurrent updates
- Ochrana před lost update problem
- User-friendly chybová hláška když data změnil jiný uživatel

---

## Rozhodnutí

Implementujeme **Optimistic Locking** pomocí `version` column v AuditMixin.

### Princip

1. Každá editovatelná entita (Part, Operation, Feature, Batch) má `version` column
2. `version` se automaticky inkrementuje při každém update (SQLAlchemy event listener)
3. Frontend posílá `version` v PUT requestu
4. Backend kontroluje: `if db_version != request_version: raise 409`
5. Pokud version nesedí → HTTP 409 "Data byla změněna jiným uživatelem"

### Implementace

#### 1. Database (app/database.py)

```python
class AuditMixin:
    version = Column(Integer, default=0, nullable=False)

# Auto-increment version on update
@event.listens_for(Base, 'before_update', propagate=True)
def receive_before_update(mapper, connection, target):
    if hasattr(target, 'version'):
        target.version += 1
```

#### 2. Pydantic Schemas (app/models/*.py)

```python
class PartUpdate(BaseModel):
    # ... fields ...
    version: int  # Optimistic locking (ADR-008)

class PartResponse(PartBase):
    # ... fields ...
    version: int  # Frontend needs to know current version
```

#### 3. Routers (app/routers/*.py)

```python
@router.put("/{part_id}", response_model=PartResponse)
async def update_part(part_id: int, data: PartUpdate, db: AsyncSession, current_user: User):
    result = await db.execute(select(Part).where(Part.id == part_id))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(404, "Díl nenalezen")

    # Optimistic locking check (ADR-008)
    if part.version != data.version:
        logger.warning(f"Version conflict: expected {data.version}, got {part.version}")
        raise HTTPException(409, "Data byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu.")

    # Update (exclude version - auto-incremented by event listener)
    for key, value in data.model_dump(exclude_unset=True, exclude={'version'}).items():
        setattr(part, key, value)

    await db.commit()
    await db.refresh(part)
    return part
```

#### 4. Frontend Flow (future)

```javascript
// Load part
const part = await fetch(`/api/parts/${id}`).then(r => r.json());
console.log(part.version);  // e.g., 5

// User edits form...

// Save with version
const response = await fetch(`/api/parts/${id}`, {
    method: 'PUT',
    body: JSON.stringify({
        name: "New name",
        version: part.version  // Send current version
    })
});

if (response.status === 409) {
    alert("Data byla změněna jiným uživatelem. Obnovte stránku.");
    location.reload();  // Reload to get latest data
}
```

---

## Alternativy

### Option B: Pessimistic Locking (SELECT FOR UPDATE)

```python
# Lock row during read
result = await db.execute(
    select(Part).where(Part.id == part_id).with_for_update()
)
```

**Proč jsme to neudělali:**
- ❌ Locks drží transakci otevřenou → blokuje ostatní uživatele
- ❌ SQLite má omezenou podporu pro FOR UPDATE
- ❌ Dlouhé editační session → dlouhé locks
- ❌ Risk of deadlocks
- ✅ **Optimistic locking je lepší pro web aplikace** (low contention)

### Option C: Timestamp-Based Versioning

```python
updated_at = Column(DateTime, onupdate=datetime.utcnow)

# Check timestamp instead of version
if part.updated_at != data.updated_at:
    raise HTTPException(409)
```

**Proč jsme to neudělali:**
- ❌ Timestamp precision issues (microseconds, timezones)
- ❌ Méně spolehlivé než integer version
- ✅ Integer version je standard (Hibernate, Entity Framework)

---

## Důsledky

### Výhody

✅ **Ochrana před data loss** - detekuje concurrent updates
✅ **User-friendly** - jasná chybová hláška "změněno jiným uživatelem"
✅ **Performance** - žádné locks, optimistický přístup
✅ **Standard pattern** - používá se v Hibernate, Entity Framework, Django
✅ **Jednoduchá implementace** - `version` column + jeden check v routeru
✅ **Testovatelné** - lze snadno testovat concurrent updates

### Nevýhody

❌ **Frontend změna potřeba** - frontend musí posílat `version` v UPDATE requestech
  → Ale je to nutné pro funkčnost

❌ **User friction** - uživatel musí znovu načíst stránku při konfliktu
  → Trade-off za data integrity

❌ **Nepomůže při simultánních CREATE** - ale create nemá problém s lost updates

### Rizika

⚠️ **Breaking change:** Existující frontend kód musí být aktualizován
  → Všechny PUT requesty musí obsahovat `version`
  → Řešení: Postupná migrace, možnost dočasně povolit update bez version (grace period)

⚠️ **False positives:** Pokud user edituje dlouho (hodiny), může dostat 409 i když nikdo jiný neupravoval
  → Přijatelné - uživatel by měl reload pro aktuální data

---

## Implementace

### Soubory změněny

- `app/database.py` - AuditMixin už má `version` + event listener ✅
- `app/models/part.py` - přidán `version` do PartUpdate, PartResponse
- `app/models/operation.py` - přidán `version` do OperationUpdate, OperationResponse
- `app/models/feature.py` - přidán `version` do FeatureUpdate, FeatureResponse
- `app/models/batch.py` - přidán `version` do BatchResponse
- `app/routers/parts_router.py` - version check v `update_part()`
- `app/routers/operations_router.py` - version check v `update_operation()`, `change_mode()`
- `app/routers/features_router.py` - version check v `update_feature()`
- `tests/test_optimistic_locking.py` - 14 testů pro optimistic locking

### Testy

```bash
pytest tests/test_optimistic_locking.py -v
```

**Nové testy (14 testů):**

**Part:**
- `test_part_update_success_increments_version` - úspěšný update zvýší version
- `test_part_update_version_conflict_raises_409` - outdated version → HTTP 409
- `test_part_concurrent_updates_one_fails` - concurrent updates → druhý selže

**Operation:**
- `test_operation_update_success_increments_version`
- `test_operation_update_version_conflict_raises_409`
- `test_operation_change_mode_version_check` - change_mode endpoint kontroluje version
- `test_operation_change_mode_missing_version_raises_400` - missing version → HTTP 400

**Feature:**
- `test_feature_update_success_increments_version`
- `test_feature_update_version_conflict_raises_409`
- `test_feature_concurrent_updates_one_fails`

**Infrastructure:**
- `test_version_auto_increments_on_db_update` - SQLAlchemy event listener funguje

### Kritéria úspěchu

✅ Souběžný update vrací HTTP 409 "Conflict"
✅ Frontend zobrazuje alert "Data změněna jiným uživatelem" (future)
✅ Testy: 2 concurrent updates = jeden selže s 409
✅ Version auto-increment funguje (event listener)

---

## Reference

- **Martin Fowler - Optimistic Offline Lock:** https://martinfowler.com/eaaCatalog/optimisticOfflineLock.html
- **Hibernate Optimistic Locking:** https://docs.jboss.org/hibernate/orm/6.0/userguide/html_single/Hibernate_User_Guide.html#locking-optimistic
- **SQLAlchemy Version Counter:** https://docs.sqlalchemy.org/en/20/orm/versioning.html
- Related: ADR-001 Soft Delete Pattern (AuditMixin)

---

## Budoucí práce

### Frontend Integration

- [ ] Přidat `version` do všech PUT requestů
- [ ] Zobrazit user-friendly alert při HTTP 409
- [ ] Auto-reload stránky při konfliktu (nebo merge UI)

### Conflict Resolution UI (future)

- [ ] "Merge view" - ukázat rozdíly mezi verzemi
- [ ] "Accept theirs / Accept mine" buttons
- [ ] Možnost ručního merge konfliktů

---

## Changelog

- 2026-01-24: Initial decision - Optimistic Locking Pattern
