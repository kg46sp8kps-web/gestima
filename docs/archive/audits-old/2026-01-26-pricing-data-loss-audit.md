# 🚨 KRITICKÝ AUDIT - Výpočet ceny a ztráta dat (500 errors)

**Datum:** 2026-01-26
**Auditor:** Roy (Claude Code)
**Typ:** Critical Bug Audit + Data Loss Investigation
**Závažnost:** 🔴 HIGH (Data integrity risk, 500 errors, inconsistent pricing)

---

## 📋 EXECUTIVE SUMMARY

Provedl jsem hloubkový audit principu výpočtu ceny v GESTIMA v1.4.0. Identifikoval jsem **8 kritických problémů** způsobujících:
- ✅ **Nekonzistentní chování UI** (data mizí po 500 erroru)
- ✅ **Race conditions** v debounced save functions
- ✅ **Silent failures** v error handlerech (data se neuloží, UI nehlásí chybu)
- ✅ **Redundantní výpočty** (percentages 2× - Python + Pydantic)
- ⚠️ **Chybějící defensive checks** (missing material_item může způsobit 500)

**Dopad:** Uživatel vidí nekonzistentní ceny, data se ztrácí při rychlém editování, 500 errory při nekompletních datech.

---

## 🔍 METODOLOGIE

**Have you tried turning it off and on again?** ✅
**Root cause analysis?** ✅
**Anti-pattern detection?** ✅
**VISION compatibility check?** ✅

### Analyzované komponenty:
1. **Backend:**
   - `app/services/price_calculator.py` (733 řádků)
   - `app/services/batch_service.py` (169 řádků)
   - `app/routers/batches_router.py` (288 řádků)
   - `app/routers/parts_router.py` (529 řádků)
   - `app/routers/operations_router.py` (167 řádků)

2. **Frontend:**
   - `app/templates/parts/edit.html` (1053 řádků)
   - Alpine.js data flow, error handling, debouncing logic

3. **Data Model:**
   - `app/models/batch.py` (computed fields percentages)
   - Optimistic locking (version field)

---

## 🚨 KRITICKÉ NÁLEZY

### 🔴 **CRITICAL-001: Race Condition v `debouncedSaveAndLoadStock()`**

**Popis:**
Frontend volá `savePart()` a `loadStockCost()` **SEKVENČNĚ** (await chain), ale `recalculateAllBatches()` běží **PARALELNĚ**.

**Kód (řádek 785-791):**
```javascript
debouncedSaveAndLoadStock() {
    clearTimeout(this.saveTimeout);
    this.saveTimeout = setTimeout(async () => {
        await this.savePart();                  // ✅ Await
        await this.loadStockCost();             // ✅ Await
        await this.recalculateAllBatches();     // ⚠️ Paralelní fetches uvnitř!
    }, 400);
}
```

**Problém v `recalculateAllBatches()` (řádek 869-873):**
```javascript
const recalcPromises = this.batches.map(batch =>
    fetch(`/api/batches/${batch.id}/recalculate`, {
        method: 'POST'
    })
);
const responses = await Promise.all(recalcPromises);
```

**Race condition scenario:**
```
t=0ms:    User mění stock_diameter 50 → 70
t=400ms:  debouncedSaveAndLoadStock() fire
t=410ms:  savePart(diameter=70) starts
t=450ms:  savePart() commit to DB
t=460ms:  loadStockCost() fetches (OK, reads 70)
t=470ms:  recalculateAllBatches() starts 5× fetch in parallel
t=480ms:  Backend recalculate_batch_costs() číst Part.stock_diameter
          ❌ RISK: Pokud DB transakce savePart() není committed,
             backend může číst STARÁ data (50 místo 70)!
```

**Dopad:**
- Batch costs vypočítány ze starých dat
- UI zobrazuje nekonzistentní ceny
- User neví že ceny jsou špatně

**Relevance na L-010 (Stop záplatování):**
✅ Toto **NENÍ** záplata - je to designový problém v async flow.

**Fix:**
```javascript
// OPTION A: Sekvenční recalculate (pomalejší, ale bezpečnější)
for (const batch of this.batches) {
    await fetch(`/api/batches/${batch.id}/recalculate`, { method: 'POST' });
}

// OPTION B: Backend endpoint /api/batches/recalculate-all-for-part/{part_id}
// Jednodušší, atomické, rychlejší (DB může optimalizovat)
```

---

### 🔴 **CRITICAL-002: Silent Failures v Error Handlerech**

**Popis:**
Většina catch bloků jen loguje `console.error()` a **nic nehlásí uživateli**.

**Příklady (řádky 654-656, 666-667, 696-697, 780-781, 828-829, 840-841, 851-852, 886-887):**
```javascript
} catch (error) {
    console.error('Error loading stock cost:', error);
    // ❌ Žádný showToast!
    // ❌ Žádný fallback UI state!
    // ❌ Žádný retry mechanismus!
}
```

**Problém:**
- User nevidí error → myslí si že vše funguje
- Data se neuloží → ztráta práce
- UI zobrazuje **stará data** (this.stockCost zůstane starý)

**Příklad scenáře:**
```
1. User vybere materiál → selectMaterial()
2. savePart() fails (500 error - missing FK)
3. catch block: console.error() [TY JEDINĚ!]
4. loadStockCost() běží dál (s NULL material_item_id)
5. Backend vrací StockCostResponse(cost=0)
6. UI zobrazuje "Materiál: 0 Kč" → User myslí že materiál je zdarma
7. User pokračuje → ŠPATNÁ KALKULACE v batches
```

**Fix:** Všude kde je `catch (error)`, přidat:
```javascript
} catch (error) {
    console.error('Error loading stock cost:', error);
    window.showToast('Nepodařilo se načíst cenu polotovaru', 'error');
    // Optional: Set error state
    this.stockCost = { cost: 0, error: true };
}
```

---

### 🔴 **CRITICAL-003: Redundantní Výpočet Percentages (Python + Pydantic)**

**Popis:**
Percentages se počítají **2×**:
1. V `price_calculator.py::calculate_batch_prices()` (řádky 477-482)
2. V `batch.py::BatchResponse` computed fields (řádky 90-120)

**Kód - price_calculator.py:**
```python
# Calculate percentages (ADR-016: Výpočty POUZE Python)
if result.unit_cost > 0:
    result.material_percent = round((result.material_cost / result.unit_cost) * 100, 1)
    result.machining_percent = round((result.machining_cost / result.unit_cost) * 100, 1)
    result.setup_percent = round((result.setup_cost / result.unit_cost) * 100, 1)
    result.coop_percent = round((result.coop_cost / result.unit_cost) * 100, 1)
```

**Kód - batch.py:**
```python
@computed_field
@property
def material_percent(self) -> float:
    """Podíl materiálu v %"""
    if self.unit_cost > 0:
        return round((self.material_cost / self.unit_cost) * 100, 1)
    return 0.0
```

**Problém:**
- Duplikace logiky (L-002 anti-pattern)
- Percentages v `BatchPrices` dataclass se **NIKDE NEPOUŽÍVAJÍ** (calculate_batch_prices se volá jen v batch_service, která percentages ignoruje)
- Pydantic computed fields se volají při **KAŽDÉM** serializaci (overhead)

**Fix:**
```python
# OPTION 1: Smazat percentages z BatchPrices dataclass
# (Použít pouze Pydantic computed fields)

# OPTION 2: Smazat Pydantic computed fields
# (Použít jen calculate_batch_prices, uložit do DB columns)

# DOPORUČENÍ: OPTION 1 (computed fields jsou flexibilnější pro VISION)
```

**Důvod pro OPTION 1:**
- VISION: Orders/Quotes budou mít frozen batch data → percentages musí být computed on-the-fly ze snapshot
- Computed fields zachovávají ADR-016 (výpočty Python) i pro frozen batches

---

### 🟡 **HIGH-004: Chybějící Defensive Checks v `calculate_stock_cost_from_part()`**

**Popis:**
Funkce předpokládá že Part má `material_item` + `group` + `price_category`, ale **neověřuje** to.

**Kód (řádky 143-156):**
```python
item = part.material_item
if not item:
    return result  # ✅ OK

group = item.group
if not group:
    return result  # ✅ OK

price_category = item.price_category
if not price_category:
    logger.error(f"MaterialItem {item.id} has no price_category")
    return result  # ✅ OK

if db is None:
    logger.error("DB session required for dynamic price tier selection")
    return result  # ✅ OK
```

**Problém:**
Checks jsou OK, ale `batch_service.py::recalculate_batch_costs()` **neloguje** proč je `material_cost=0`.

**Kód - batch_service.py (řádek 59-71):**
```python
if not part.material_item:
    logger.warning(
        f"Part {part.id} has no material_item, setting material_cost=0"
    )
    batch.material_cost = 0.0
    material_cost = 0.0
else:
    # 2. Vypočítat material cost (s dynamic price tiers - ADR-014)
    material_calc = await calculate_stock_cost_from_part(
        part, batch.quantity, db
    )
    material_cost = material_calc.cost  # Za 1 kus
    batch.material_cost = material_cost
```

**Vylepšení:**
```python
# Přidat detailnější logging pro debugging
if not part.material_item:
    logger.warning(
        f"Part {part.id} ({part.part_number}) has no material_item, "
        f"setting material_cost=0. Batch {batch.id or 'NEW'} may have incorrect costs.",
        extra={"part_id": part.id, "batch_id": batch.id}
    )
elif not part.material_item.group:
    logger.error(
        f"MaterialItem {part.material_item.id} has no group, "
        f"cannot calculate density. Setting material_cost=0.",
        extra={"part_id": part.id, "material_item_id": part.material_item.id}
    )
elif not part.material_item.price_category:
    logger.error(
        f"MaterialItem {part.material_item.id} has no price_category, "
        f"cannot calculate price. Setting material_cost=0.",
        extra={"part_id": part.id, "material_item_id": part.material_item.id}
    )
```

---

### 🟡 **HIGH-005: Frontend Nevaliduje API Response Status**

**Popis:**
Některé fetch handlers **neověřují** `response.ok` před `response.json()`.

**Příklad - loadMaterialItems() (řádek 649-652):**
```javascript
const response = await fetch('/api/materials/items');
if (response.ok) {
    this.materialItems = await response.json();
    this.filteredMaterials = this.materialItems;
}
// ❌ Žádný else branch - pokud !response.ok, data zůstanou prázdná
// ❌ User neví že došlo k chybě
```

**Problém:**
- 500 error → `response.ok = false`
- `materialItems` zůstane `[]`
- UI zobrazuje "Žádné materiály" → User myslí že DB je prázdná

**Fix:**
```javascript
const response = await fetch('/api/materials/items');
if (response.ok) {
    this.materialItems = await response.json();
    this.filteredMaterials = this.materialItems;
} else {
    // Log error details
    const errorText = await response.text();
    console.error('Failed to load materials:', response.status, errorText);
    window.showToast('Nepodařilo se načíst materiály', 'error');
    // Keep existing data (don't reset to [])
}
```

**Další místa s tímto problémem:**
- `loadMachines()` (řádek 661)
- `loadPart()` (řádek 672)
- `loadStockCost()` (řádek 775)
- `loadOperations()` (řádek 834)
- `loadBatches()` (řádek 846)

---

### 🟡 **HIGH-006: Optimistic Locking Částečně Implementován**

**Popis:**
Part a Operation mají optimistic locking (version field), ale **chybí UI feedback při merge konfliktu**.

**Kód - savePart() (řádek 822-823):**
```javascript
} else if (response.status === 409) {
    window.showToast('Data změněna jiným uživatelem - obnovte stránku', 'error');
}
```

**Problém:**
- Toast zmizí po 3s → User neobnoví stránku
- Data zůstanou stará → další save selže znovu (409)
- **Nekonečný loop** 409 toastů

**Fix:**
```javascript
} else if (response.status === 409) {
    // Modal s akcemi místo toast
    if (confirm('Data byla změněna jiným uživatelem. Obnovit stránku? (Neuložené změny budou ztraceny)')) {
        window.location.reload();
    } else {
        // Načíst novou verzi Part
        await this.loadPart();
        window.showToast('Načtena nová verze. Zkuste změnu znovu.', 'warning');
    }
}
```

---

### 🟢 **MEDIUM-007: Debounce Timeout Nekonzistentní**

**Popis:**
Různé debounce timeouty:
- `debouncedSave()` → 500ms
- `debouncedSaveAndLoadStock()` → 400ms
- `debouncedUpdateOperation()` → 400ms

**Problém:**
- User netuší kdy se data uloží
- UX je nepředvídatelný

**Doporučení:**
```javascript
// Konstanta na začátku component
const DEBOUNCE_DELAY_MS = 500;  // Všude stejná hodnota

debouncedSave() {
    clearTimeout(this.saveTimeout);
    this.saveTimeout = setTimeout(() => this.savePart(), DEBOUNCE_DELAY_MS);
}
```

---

### 🟢 **MEDIUM-008: recalculateAllBatches() Nemá Progress Indicator**

**Popis:**
Pokud Part má 10 batches, `recalculateAllBatches()` posílá 10 paralelních POST requestů. User nevidí progress.

**UX problém:**
- UI freeze (až 2s pro 10 batches)
- User klikne znovu → duplicitní requesty
- Žádný feedback že se něco děje

**Fix:**
```javascript
async recalculateAllBatches() {
    if (!this.batches || this.batches.length === 0) return;

    // Show progress
    const batchCount = this.batches.length;
    window.showToast(`Přepočítávám ${batchCount} dávek...`, 'info');

    try {
        // Sequential with progress (alt: use progress bar)
        for (let i = 0; i < this.batches.length; i++) {
            const batch = this.batches[i];
            const response = await fetch(`/api/batches/${batch.id}/recalculate`, {
                method: 'POST'
            });
            if (!response.ok) {
                console.warn(`Batch ${batch.id} recalculation failed`);
            }
            // Optional: Update progress UI
        }

        await this.loadBatches();
        window.showToast('Všechny dávky přepočítány', 'success');
    } catch (error) {
        console.error('Error recalculating batches:', error);
        window.showToast('Chyba při přepočtu dávek', 'error');
    }
}
```

---

## 📊 ANALÝZA VÝPOČTU CEN - SPRÁVNOST

### ✅ Backend výpočty jsou **SPRÁVNÉ**

**Ověřeno:**
1. **Material cost:**
   - `calculate_stock_cost_from_part()` - geometrie + ADR-014 price tiers ✅
   - Volume calculations pro všechny tvary (round_bar, tube, plate, atd.) ✅
   - Dynamic price tier selection podle total_weight ✅

2. **Batch costs:**
   - `calculate_batch_prices()` - machining + setup + coop ✅
   - Setup distribuce (setup_cost / quantity) ✅
   - Coop min_price logic ✅
   - Machine hourly rates ✅

3. **Error handling:**
   - Transaction management (try/commit/rollback) ✅
   - Integrity error handling ✅
   - Logging (structured + exc_info=True) ✅

### ⚠️ Frontend data flow má **MEZERY**

**Problémy:**
- Race conditions (CRITICAL-001)
- Silent failures (CRITICAL-002)
- Chybějící validace (HIGH-005)
- Nekonzistentní UX (MEDIUM-007, MEDIUM-008)

---

## 🎯 DOPORUČENÍ (Prioritizované)

### 🔴 **IMMEDIATE (Dnes/zítra):**

1. **Fix CRITICAL-002 (Silent Failures):**
   - Přidat `window.showToast()` do VŠECH catch bloků
   - Priority: loadPart, savePart, loadStockCost, recalculateAllBatches
   - Estimate: 30 minut

2. **Fix HIGH-005 (Response Validation):**
   - Přidat `else { showToast }` do všech fetch handlers
   - Priority: loadMaterialItems, loadMachines, loadOperations, loadBatches
   - Estimate: 20 minut

3. **Fix CRITICAL-001 (Race Condition) - OPTION B:**
   - Backend endpoint `/api/batches/recalculate-all-for-part/{part_id}`
   - Frontend volá pouze 1× (místo N× paralelně)
   - Atomické, rychlejší, bezpečnější
   - Estimate: 1 hodina

### 🟡 **SHORT-TERM (Tento týden):**

4. **Fix HIGH-006 (Optimistic Locking UX):**
   - Modal pro 409 conflicts místo toast
   - Auto-reload nebo manual merge
   - Estimate: 45 minut

5. **Fix MEDIUM-008 (Progress Indicator):**
   - Sekvenční recalculate s progress bar
   - Nebo spinner overlay
   - Estimate: 30 minut

6. **Fix CRITICAL-003 (Redundant Percentages):**
   - Smazat percentages z `BatchPrices` dataclass
   - Keep pouze Pydantic computed fields
   - Update tests
   - Estimate: 45 minut

### 🟢 **MEDIUM-TERM (Příští sprint):**

7. **Unifikovat debounce timeouts (MEDIUM-007)**
8. **Enhanced logging (HIGH-004)**
9. **Unit tests pro race conditions**
10. **Frontend integration tests (Playwright)**

---

## 🔬 TESTING CHECKLIST

**Před deploymentem otestovat:**

### Scenario 1: Rychlá změna stock dimensions
```
1. Otevři Part edit
2. Rychle měň stock_diameter: 50 → 60 → 70 → 80 (< 400ms mezi změnami)
3. Počkej 1s
4. Zkontroluj:
   ✅ Stock cost se updatoval (žádný stale data)
   ✅ Všechny batches mají správný material_cost
   ✅ Žádný 500 error v console
```

### Scenario 2: Missing material_item
```
1. Vytvoř Part bez material_item
2. Přidej batch
3. Zkontroluj:
   ✅ Batch.material_cost = 0
   ✅ Toast "Díl nemá přiřazený materiál"
   ✅ Žádný 500 error
   ✅ Ostatní costs se vypočítají správně
```

### Scenario 3: Backend 500 error
```
1. Simuluj 500 error (breakpoint v batch_service)
2. Změň materiál
3. Zkontroluj:
   ✅ Toast "Chyba při ukládání"
   ✅ Data NEZMIZELÁ (UI si pamatuje původní stav)
   ✅ User může retry
```

### Scenario 4: Optimistic locking conflict
```
1. Otevři Part ve 2 tabech
2. Tab A: změň name
3. Tab B: změň length
4. Tab A: save (OK)
5. Tab B: save (409 conflict)
6. Zkontroluj:
   ✅ Modal "Data změněna jiným uživatelem"
   ✅ Option reload nebo merge
   ✅ Po reload vidím změny z Tab A
```

---

## 📝 ZÁVĚR

### Co funguje dobře:
✅ Backend price calculations (price_calculator.py) jsou **matematicky správné**
✅ Transaction management (commit/rollback) je **robustní**
✅ Optimistic locking (version field) je **implementováno**
✅ ADR-014 (Dynamic Price Tiers) funguje **correct**
✅ Logging je **strukturovaný** (extra fields)

### Co je problém:
❌ **Frontend error handling je nedostatečný** (silent failures)
❌ **Race conditions v async flow** (savePart → recalculate paralelně)
❌ **UX nekonzistence** (timeouty, progress indicators)
❌ **Redundantní výpočty** (percentages 2×)

### "Have you tried turning it off and on again?"
✅ Ano - root cause identified, není to záplatovatelný bug.
✅ Vyžaduje architectural fix (backend endpoint pro batch recalc).

---

## 🔗 RELATED DOCUMENTS

- [ADR-016: Price Breakdown with Coefficients](../ADR/016-price-breakdown-coefficients.md)
- [ADR-014: Material Price Tiers](../ADR/014-material-price-tiers.md)
- [ADR-012: Minimal Snapshot Strategy](../ADR/012-batch-price-snapshots.md)
- [ADR-008: Optimistic Locking](../ADR/008-optimistic-locking.md)
- [L-001: Výpočty POUZE Python](../../CLAUDE.md#L-001)
- [L-002: Single Source of Truth](../../CLAUDE.md#L-002)
- [L-010: Stop záplatování](../../CLAUDE.md#L-010)

---

**Status:** ✅ Audit completed
**Next Steps:** Implementovat IMMEDIATE fixes (1-3)
**Review Date:** Po implementaci fixes (2-3 dny)

---

*"This is going to be a long day..." - Roy, IT Crowd*
*"But at least now we know WHY it's broken." - Roy, after debugging*
