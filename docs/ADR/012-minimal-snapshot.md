# ADR-012: Minimal Snapshot Pattern

**Status:** Accepted
**Date:** 2026-01-24
**Context:** P2 Fáze B - Batch Snapshot (Zmrazení cen v nabídkách)

---

## Kontext

**Riziko:** Změna ceny materiálu v MaterialItem → nabídka z minulého měsíce ukazuje jinou cenu = **ztráta historické pravdy o cenách**.

**Scénář:**
1. Nabídka vytvořena 15.1.2026: Ocel 11xxx @ 80 Kč/kg → celková cena dílu 5 000 Kč
2. Cena materiálu změněna 20.1.2026: Ocel 11xxx → 90 Kč/kg (zvýšení o 12.5%)
3. Zobrazení nabídky z 15.1.2026 → **ukazuje 5 625 Kč** (chybně přepočítáno s novou cenou!)
4. Zákazník požaduje fakturu podle nabídky → nesoulad mezi nabízenou a fakturovanou cenou

**Problém:**
- Nabídky používají LIVE ceny (aktuální stav DB)
- Změna cen materiálů, strojových sazeb → změna ceny starých nabídek
- Nelze rekonstruovat historickou pravdu o cenách
- ERP standard: "Jednou vydaná nabídka = zmrazená cena"

**Požadavky:**
- Stabilní ceny v nabídkách (po "zmrazení")
- Minimální data (ne full snapshot celého dílu)
- Možnost klonovat zmrazenou nabídku pro úpravy
- Rychlé reporty (ORDER BY unit_price_frozen)

---

## Rozhodnutí

Implementujeme **Minimal Snapshot** - ukládáme pouze finální ceny + metadata do JSON.

### Princip

1. **Freeze operace:** `POST /api/batches/{id}/freeze`
   - Vytvoří snapshot s aktuálními cenami
   - Nastaví `is_frozen = True`
   - Uloží `unit_price_frozen`, `total_price_frozen` (redundantně pro reporty)

2. **Snapshot struktura (JSON):**
   ```json
   {
     "frozen_at": "2026-01-24T14:30:00",
     "frozen_by": "admin",
     "costs": {
       "material_cost": 250.0,
       "machining_cost": 180.0,
       "setup_cost": 50.0,
       "coop_cost": 0.0,
       "unit_cost": 480.0,
       "total_cost": 4800.0
     },
     "metadata": {
       "part_number": "DIL-001",
       "quantity": 10,
       "material_code": "11300",
       "material_price_per_kg": 80.0
     }
   }
   ```

3. **Imutabilita:**
   - Zmrazený batch NELZE editovat (HTTP 403)
   - DELETE → soft delete (batch.deleted_at) pro zachování historie
   - Unfreeze → NEIMPLEMENTOVÁNO (once frozen, always frozen)

4. **Clone operace:** `POST /api/batches/{id}/clone`
   - Vytvoří nový, nezmrazený batch se stejnými parametry
   - Nový batch má LIVE ceny (aktuální stav)
   - Uživatel může upravit klon

### Implementace

#### 1. Database Schema (app/models/batch.py)

```python
class Batch(Base, AuditMixin):
    # ... existing fields ...

    # Freeze metadata (ADR-012: Minimal Snapshot)
    is_frozen = Column(Boolean, default=False, nullable=False, index=True)
    frozen_at = Column(DateTime, nullable=True)
    frozen_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Snapshot (minimal - pouze ceny a metadata)
    snapshot_data = Column(JSON, nullable=True)

    # Redundantní sloupce pro reporty (hybrid approach)
    unit_price_frozen = Column(Float, nullable=True, index=True)
    total_price_frozen = Column(Float, nullable=True)

    frozen_by = relationship("User")
```

#### 2. Service Layer (app/services/snapshot_service.py)

```python
async def create_batch_snapshot(batch: Batch, username: str, db: AsyncSession) -> Dict[str, Any]:
    """Vytvoří minimal snapshot pro zmrazení cen batche."""
    snapshot = {
        "frozen_at": datetime.utcnow().isoformat(),
        "frozen_by": username,
        "costs": {
            "material_cost": batch.material_cost,
            "machining_cost": batch.machining_cost,
            # ... další ceny
        },
        "metadata": {
            "part_number": part.part_number,
            "material_code": material_group.code,
            "material_price_per_kg": material_item.price_per_kg,
        }
    }
    return snapshot

def get_batch_costs(batch: Batch) -> Dict[str, float]:
    """Vrátí ceny - ze snapshotu pokud frozen, jinak LIVE."""
    if batch.is_frozen and batch.snapshot_data:
        return batch.snapshot_data.get("costs", {})
    else:
        return {
            "material_cost": batch.material_cost,
            # ... LIVE ceny
        }
```

#### 3. API Endpoints (app/routers/batches_router.py)

```python
@router.post("/{batch_id}/freeze", response_model=BatchResponse)
async def freeze_batch(batch_id: int, db: AsyncSession, current_user: User):
    """Zmrazí ceny batche (ADR-012: Minimal Snapshot)."""
    if batch.is_frozen:
        raise HTTPException(409, "Dávka je již zmrazena")

    # Vytvořit snapshot
    snapshot = await create_batch_snapshot(batch, current_user.username, db)

    # Nastavit freeze metadata
    batch.is_frozen = True
    batch.frozen_at = datetime.utcnow()
    batch.frozen_by_id = current_user.id
    batch.snapshot_data = snapshot
    batch.unit_price_frozen = batch.unit_cost  # Redundantní pro reporty
    batch.total_price_frozen = batch.total_cost

    await db.commit()
    return batch

@router.post("/{batch_id}/clone", response_model=BatchResponse)
async def clone_batch(batch_id: int, db: AsyncSession, current_user: User):
    """Naklonuje batch (nový, nezmrazený batch se stejnými parametry)."""
    new_batch = Batch(
        part_id=original.part_id,
        quantity=original.quantity,
        # ... zkopírovat ceny (LIVE, ne ze snapshotu)
        # Freeze fields zůstanou default (False, None)
    )
    db.add(new_batch)
    await db.commit()
    return new_batch

@router.delete("/{batch_id}")
async def delete_batch(batch_id: int, db: AsyncSession, current_user: User):
    """Smazat batch - frozen batch soft delete (ADR-012)."""
    if batch.is_frozen:
        # Soft delete pro frozen batch
        batch.deleted_at = datetime.utcnow()
        batch.deleted_by = current_user.username
        await db.commit()
        return {"message": "Zmrazená dávka smazána (soft delete)"}
    else:
        # Hard delete pro nezamrzlé batches
        await db.delete(batch)
        await db.commit()
        return {"message": "Dávka smazána"}
```

---

## Alternativy

### Option A: Full Snapshot (celá struktura part+operations+features)

**Struktura:**
```json
{
  "part": { ... },
  "operations": [ ... ],
  "features": [ ... ],
  "materials": { ... },
  "machines": { ... }
}
```

**Proč jsme to neudělali:**
- ❌ Velké JSON objekty (kilobytes per batch)
- ❌ Duplikace dat (část a operace se nemění)
- ❌ Složitější queries
- ❌ Over-engineering (nepotřebujeme celou historii)
- ✅ **Minimal snapshot stačí** - ceny jsou to jediné co se mění a potřebujeme zmrazit

### Option B: Kopie cen do samostatných sloupců

```python
material_cost_frozen = Column(Float)
machining_cost_frozen = Column(Float)
setup_cost_frozen = Column(Float)
# ... 6+ sloupců
```

**Proč jsme to neudělali:**
- ❌ Duplikace (6+ redundantních sloupců)
- ❌ Ztráta metadata (kdy zmrazeno, kým, originální cena materiálu)
- ❌ Méně flexibilní (nelze přidat další metadata)
- ✅ **JSON je flexibilnější** - metadata + ceny v jedné struktuře

### Option C: Temporal Tables (verzování materials)

**Přístup:** Ukládat všechny verze MaterialItem (price_per_kg_history)

**Proč jsme to neudělali:**
- ❌ Over-engineering (90% změn cen je irelevantní)
- ❌ Složité queries (JOIN na historii)
- ❌ Více storage (všechny změny navždy)
- ❌ Neřeší freeze sazeb strojů, kooperací
- ✅ **Snapshot je jednodušší** - jedno místo pro všechny zmrazené ceny

---

## Důsledky

### Výhody

✅ **Stabilní ceny v nabídkách** - zmrazená nabídka ukazuje historicky správné ceny
✅ **Minimální data** - pouze ceny + metadata (desítky bytes, ne kilobytes)
✅ **Rychlé reporty** - `unit_price_frozen` sloupec pro SQL ORDER BY
✅ **Audit trail** - frozen_at, frozen_by → kdo zmrazil, kdy
✅ **Clone workflow** - uživatel může snadno vytvořit novou verzi nabídky
✅ **Flexibilita** - JSON umožňuje přidat další metadata v budoucnu
✅ **Standard ERP pattern** - zmrazení nabídek je běžná praxe

### Nevýhody

❌ **JSON není typovaný** - možné problémy při změně struktury snapshotu
  → Řešení: Verze snapshot struktury (`snapshot_version: 1`)

❌ **Redundance** - ceny jsou ve 2 místech (snapshot + redundantní sloupce)
  → Trade-off za rychlé reporty (acceptable)

❌ **Migrace existujících batches** - staré batches nemají snapshot
  → Řešení: Staré batches mají `is_frozen=False` (LIVE ceny)

### Rizika

⚠️ **Snapshot může být neúplný** - pokud chybí material_item nebo group
  → Ošetřeno: snapshot service načítá data s eager loading

⚠️ **Změna snapshot struktury** - budoucí verze může mít jinou strukturu
  → Řešení: Verze snapshot (`"snapshot_version": 1`), backward compatibility

⚠️ **Soft delete queries** - musíme filtrovat `deleted_at IS NULL`
  → Už existuje pattern (AuditMixin soft delete)

---

## Implementace

### Soubory změněny

- `app/models/batch.py` - přidány freeze fields ✅
- `app/services/snapshot_service.py` - nový soubor ✅
- `app/routers/batches_router.py` - POST /freeze, POST /clone, soft delete ✅
- `tests/test_snapshots.py` - 8 testů pro freeze, clone, immutability ✅

### Soubory odstraněny

- `app/models/enums.py` - odstraněn `PartStatus` enum (nepotřebujeme Part.status)
- `app/models/part.py` - odstraněn `status` column (freeze je pouze na Batch)

### Testy

```bash
pytest tests/test_snapshots.py -v
```

**Nové testy (8 testů):**

**Freeze:**
- `test_freeze_batch` - zmrazení batche vytvoří snapshot
- `test_freeze_already_frozen_batch` - zmrazení zmrazeného batche → HTTP 409
- `test_freeze_batch_not_found` - zmrazení neexistujícího batche → HTTP 404

**Immutability:**
- `test_frozen_batch_soft_delete` - smazání frozen batche → soft delete

**Clone:**
- `test_clone_batch` - klonování vytvoří nový, nezmrazený batch
- `test_clone_batch_not_found` - klonování neexistujícího batche → HTTP 404

**Price Stability:**
- `test_price_stability_after_freeze` - změna ceny materiálu neovlivní frozen batch ✅

### Kritéria úspěchu

✅ Zmrazená dávka vrací stabilní ceny (i po změně MaterialItem.price_per_kg)
✅ Endpoint POST /api/batches/{id}/freeze funguje
✅ Snapshot obsahuje: material, machines, costs, frozen_at, frozen_by
✅ Test: změna ceny materiálu neovlivní zmrazenou dávku
✅ Frozen batch lze smazat pouze soft delete
✅ Clone vytvoří nový batch s LIVE cenami

---

## Integrace s budoucím modulem nabídek

**Poznámka:** Freeze je prozatím manuální operace (uživatel klikne na tlačítko).

**Budoucí práce:**
- Modul nabídky (Quotes)
- Automatický freeze při změně stavu nabídky na "Nabídnuto"
- Vazba `Batch.quote_id → Quote.id`
- Workflow: DRAFT → CALCULATED → QUOTED (auto-freeze) → APPROVED → LOCKED

**Rozhodnutí:**
- **Part.status NENÍ potřeba** - freeze je na Batch level, ne Part level
- **Batch.is_frozen = nezávislé** - není vázané na Part (dokud nemáme Quote modul)

---

## Reference

- **ADR-008:** Optimistic Locking Pattern (version check)
- **ADR-011:** Material Hierarchy (MaterialGroup + MaterialItem)
- **ADR-001:** Soft Delete Pattern (AuditMixin.deleted_at)
- **ERP Best Practices:** Quote freezing, price stability
- **Audit report:** docs/audit.md - A3: Price Decay problem

---

## Budoucí práce

### Quote Module Integration

- [ ] Vytvořit `Quote` model (nabídka = kolekce batches)
- [ ] Vazba `Batch.quote_id → Quote.id`
- [ ] Automatický freeze při Quote.status = "QUOTED"
- [ ] Workflow stavy: DRAFT → CALCULATED → QUOTED → APPROVED

### UI Improvements

- [ ] Tlačítko "Zmrazit" v detailu batche
- [ ] Badge "FROZEN" v seznamu batches
- [ ] Disable edit controls pro frozen batch
- [ ] "Clone" button v UI (vytvořit kopii pro úpravy)

### Reporting

- [ ] Report "Nabídky podle ceny" (ORDER BY unit_price_frozen)
- [ ] Porovnání "snapshot vs aktuální cena" (ukazuje price drift)

### Snapshot Versioning

- [ ] Přidat `snapshot_version: 1` do snapshot struktury
- [ ] Backward compatibility při změně snapshot struktury

---

## Changelog

- 2026-01-24: Initial decision - Minimal Snapshot Pattern
- 2026-01-24: Rozhodnuto: Part.status NENÍ potřeba (freeze pouze na Batch)
- 2026-01-24: Implementace: freeze, clone, soft delete, 8 testů
