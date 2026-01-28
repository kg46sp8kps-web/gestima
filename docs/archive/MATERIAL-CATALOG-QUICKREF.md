# Material Catalog + Smart Lookup - Quick Reference

**Status:** 📋 NAVRŽENO | **Effort:** ~12h | **Reference:** [ADR-019](ADR/019-material-catalog-smart-lookup.md)

---

## 🚀 Quick Start (Implementation Order)

### 1️⃣ PREP - Seed MaterialNorms

```bash
# MANDATORY před importem!
python scripts/seed_material_norms.py

# Verify:
sqlite3 gestima.db "SELECT COUNT(*) FROM material_norms;"
# → mělo by vrátit ~48 záznamů
```

**Proč důležité:**
- Import potřebuje MaterialNorm mapping (W.Nr → MaterialGroup)
- Bez toho import selže nebo použije jen fallback pattern matching

---

### 2️⃣ IMPORT - Material Catalog

```bash
# Preview (DRY-RUN):
python scripts/import_material_catalog.py

# Execute:
python scripts/import_material_catalog.py --execute

# Verify:
sqlite3 gestima.db "SELECT COUNT(*) FROM material_items;"
# → mělo by vrátit ~2405 záznamů
```

**Co vytvoří:**
- 16 MaterialGroups (litina přidána!)
- 39 PriceCategories (materiál + tvar)
- 2405 MaterialItems (7-digit material_number: 2XXXXXX)

---

### 3️⃣ BACKEND - Smart Lookup

**MaterialSearchService** (`app/services/material_search_service.py`):
```python
async def find_nearest_upward_match(
    material_code: str,      # "1.4404"
    shape: StockShape,       # ROUND_BAR
    target_dimensions: dict, # {diameter: 21.0}
    db: AsyncSession
) -> Optional[tuple[MaterialItem, float]]:
    """
    UPWARD TOLERANCE ONLY!

    Zadám Ø21 → najde Ø25 ✅ (větší o 4mm)
    Zadám Ø21 → NENAJDE Ø20 ❌ (menší!)
    """
```

**Parse API rozšíření** (`app/routers/materials_router.py`):
```python
@router.get("/parse")
async def parse_material_string(text: str, db: AsyncSession):
    """
    Input: "1.4404 Ø21"

    Output: {
        # Existing
        "material_code": "1.4404",
        "diameter": 21.0,

        # NEW: Smart lookup
        "matched_material_item": {...},
        "dimension_diff": 4.0,
        "match_message": "Nalezena skladová položka o 4mm větší"
    }
    """
```

---

### 4️⃣ FRONTEND - Match Card UI

**parts/edit.html:**
```html
<template x-if="parseResult && parseResult.matched_material_item">
    <div class="material-match-card">
        📦 Nalezena skladová položka o 4mm větší
        1.4404 Ø25mm - tyč kruhová nerez
        Průměr: 25mm | 3.85 kg/m
        [Použít]
    </div>
</template>
```

**Alpine.js:**
```javascript
async applyMaterialItem(matchedItem) {
    // Uloží OBA fieldy
    this.partData.material_item_id = matchedItem.id;
    this.partData.price_category_id = matchedItem.price_category.id;

    // Auto-fill geometry
    this.partData.stock_diameter = matchedItem.diameter;

    // Recalculate batches (s weight_per_meter z katalogu!)
    await this.loadBatches();
}
```

---

## 🔑 Key Decisions

### ✅ UPWARD Tolerance ONLY

```
User zadá: Ø21mm
→ Najde: Ø25mm ✅ (větší o 4mm)
→ NENAJDE: Ø20mm ❌ (menší!)

Důvod: Nelze použít menší polotovar než díl (fyzikálně nemožné).
```

### ✅ weight_per_meter OPTIONAL

```python
# Priority logic v price_calculator.py:
if part.material_item and part.material_item.weight_per_meter:
    # KATALOGOVÁ hmotnost (priorita!)
    weight_kg = weight_per_meter * stock_length / 1000.0
else:
    # FALLBACK: Geometry + density
    weight_kg = volume_dm3 * density
```

**Proč OPTIONAL:**
- Excel katalog NEMÁ weight_per_meter sloupec
- Doplníme později (UPDATE material_items SET ...)
- Fallback zajišťuje kompatibilitu

### ✅ Part má OBA fieldy

```sql
-- Part model (Migration 2026-01-26 - READY!):
material_item_id INTEGER NULL      -- Konkrétní rozměr (Ø25mm)
price_category_id INTEGER NULL     -- Cenová kategorie (NEREZ-KRUHOVA)
```

**Proč OBA:**
- `material_item_id` → specifický rozměr + weight_per_meter
- `price_category_id` → dynamic pricing (ADR-014)
- Orders v2.0 potřebuje snapshot OBOU!

---

## 📊 Data Structure

### MaterialGroup (16 kategorií)

```python
# MATERIAL_GROUPS mapping:
{
    "1.0": {"code": "10xxx", "name": "Ocel konstrukční", "density": 7.85},
    "1.4": {"code": "14xxx", "name": "Nerez", "density": 7.90},
    "3.0": {"code": "3xxxx", "name": "Hliník", "density": 2.70},

    # NEW: Litina (2026-01-27)
    "GG250": {"code": "LITINA-GG", "name": "Litina šedá", "density": 7.20},
    "GGG40": {"code": "LITINA-TV", "name": "Litina tvárná", "density": 7.10},

    # Plasty
    "PA6": {"code": "PLAST", "name": "Plasty", "density": 1.20},
    "POM": {"code": "PLAST", "name": "Plasty", "density": 1.20},
}
```

### PriceCategory (39 kombinací)

```python
# get_price_category_code(material_group_code, shape):
("10xxx", "ROUND_BAR") → ("OCEL-KONS-KRUHOVA", "Ocel konstrukční - kruhová tyč")
("14xxx", "PLATE") → ("NEREZ-DESKA", "Nerez - deska")
("LITINA-GG", "ROUND_BAR") → ("LITINA-GG-KRUHOVA", "Litina šedá - kruhová tyč")
```

### MaterialItem (2405 záznamů)

```sql
INSERT INTO material_items (
    material_number,  -- 2XXXXXX (7-digit, auto-generated)
    code,             -- "1.4404-D25"
    name,             -- "1.4404 Ø25mm - tyč kruhová nerez"
    shape,            -- ROUND_BAR
    diameter,         -- 25.0
    weight_per_meter, -- NULL (doplníme později)
    material_group_id,    -- FK → MaterialGroup
    price_category_id     -- FK → MaterialPriceCategory
) VALUES (...);
```

---

## 🧪 Testing Checklist

### Unit Tests (`tests/test_material_search.py`)

- [ ] test_exact_match() - Ø20 → Ø20 (diff=0)
- [ ] test_upward_match() - Ø21 → Ø25 (diff=4)
- [ ] test_no_smaller_match() - Ø21 NE Ø20!
- [ ] test_multi_dimension() - bloky (width + thickness OBA ≥)
- [ ] test_no_match_found() - žádný větší rozměr

### Integration Tests (`tests/test_material_integration.py`)

- [ ] test_parse_with_lookup() - parse API vrací matched_item
- [ ] test_apply_material_item() - uloží OBA fieldy
- [ ] test_catalog_weight_priority() - weight_per_meter > calculated

### Import Tests (`tests/test_material_import.py`)

- [ ] test_import_execution() - vytvoří MaterialItems
- [ ] test_material_number_uniqueness() - žádné duplicity
- [ ] test_fk_integrity() - MaterialGroup + PriceCategory exist

---

## 🎯 User Workflow (End-to-End)

```
1. User: Otevře parts/edit.html
2. User: Zadá do chytrého vyhledávání: "1.4404 Ø21"

3. System (Parse API):
   - Extrahuje: material_code=1.4404, shape=ROUND_BAR, diameter=21
   - Najde MaterialGroup (via MaterialNorm nebo pattern match)
   - Smart Lookup: filter items (group + shape + diameter >= 21)
   - Vybere nejbližší: MaterialItem "1.4404 Ø25mm" (diff=4mm)

4. UI (Match Card):
   📦 Nalezena skladová položka o 4mm větší
   1.4404 Ø25mm - tyč kruhová nerez
   Průměr: 25mm | 3.85 kg/m
   [Použít]

5. User: Klikne "Použít"

6. System (applyMaterialItem):
   - Uloží Part.material_item_id = 456
   - Uloží Part.price_category_id = 5
   - Auto-fill: stock_shape, stock_diameter, ...
   - Recalculate batches (priority weight_per_meter!)

7. UI: Batch prices aktualizovány (přesnější hmotnost!)
```

---

## 🔮 Future (Orders v2.0)

**Snapshot Strategy:**

```python
Order.part_snapshot = {
    # Existing
    "part_id": 123,
    "part_number": "1234567",

    # NEW: MaterialItem snapshot
    "material_item_id": 456,
    "material_item_number": "2789456",
    "material_item_name": "1.4404 Ø25mm - tyč kruhová nerez",
    "weight_per_meter": 3.85,  # Frozen catalog weight

    # Frozen pricing
    "price_per_kg": 119.3,     # Frozen tier price

    # Metadata
    "snapshot_date": "2026-01-27T10:00:00Z"
}
```

**Proč kritické:**
- Order musí být **immutable** (ceny se mění, Order zůstává)
- MaterialItem může být smazán → snapshot zachová info
- Audit-proof (reprodukovatelné kalkulace)

---

## ⚠️ Common Pitfalls

### ❌ WRONG: Bidirectional Tolerance (±)

```python
# User zadá: Ø21mm
# → Najde: Ø20mm (menší!) ❌
```

**Oprava:** UPWARD ONLY (business requirement!)

### ❌ WRONG: weight_per_meter MANDATORY

```python
# Import failne pokud weight_per_meter IS NULL ❌
```

**Oprava:** OPTIONAL (Excel nemá data, doplníme později)

### ❌ WRONG: Import PŘED seed_material_norms

```bash
# Import bez MaterialNorm mappingu ❌
python scripts/import_material_catalog.py --execute
```

**Oprava:** Seed norms FIRST!

---

## 📚 Reference

- **Full ADR:** [docs/ADR/019-material-catalog-smart-lookup.md](ADR/019-material-catalog-smart-lookup.md)
- **Next Steps:** [docs/NEXT-STEPS.md](NEXT-STEPS.md) - Material Catalog sekce
- **Vision Impact:** [docs/VISION.md](VISION.md) - v2.0 Orders preparation

---

**Last Updated:** 2026-01-27
**Status:** 📋 READY FOR IMPLEMENTATION (after seed + import)
