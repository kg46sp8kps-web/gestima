# ADR-019: Material Catalog Import & Smart Upward Lookup

**Datum:** 2026-01-27
**Status:** 📋 NAVRŽENO (čeká na implementaci po seed norms + import)
**Kontext:** v1.4.0 Costing → v2.0 Orders preparation

---

## Rozhodnutí

Implementujeme **Material Catalog Import** (2405 MaterialItems) + **Smart Upward Dimension Lookup** pro automatické hledání skladových rozměrů:

1. **Material Catalog Import** - Import Excelu (2405 položek) do MaterialItem tabulky
2. **Smart Upward Lookup** - Fuzzy matching s UPWARD tolerance (najde nejbližší VĚTŠÍ rozměr)
3. **Part.material_item_id Integration** - Part má OBA fieldy (material_item_id + price_category_id)
4. **Catalog Weight Priority** - weight_per_meter z katalogu > calculated weight

**Workflow:**
```
User zadá: "1.4404 Ø21mm"
  → Parse API: material_code=1.4404, shape=ROUND_BAR, diameter=21
  → Smart Lookup: najde MaterialItem "1.4404 Ø25mm" (diff=4mm)
  → UI: "Nalezena skladová položka o 4mm větší, chcete použít?"
  → Apply: uloží material_item_id + price_category_id + auto-fill geometry
  → Pricing: použije weight_per_meter z katalogu (pokud je v DB)
```

---

## Kontext

**Problém:**

1. **Material Catalog:**
   - Excel katalog (2405 položek) není v databázi
   - User musí ručně zadávat rozměry polotovarů
   - Chybí katalogová weight_per_meter → nepřesné hmotnosti

2. **Dimension Matching:**
   - User zadá Ø21mm → Excel má Ø20mm a Ø25mm
   - Nutnost najít nejbližší VĚTŠÍ rozměr (tolerance upward only)
   - Multi-dimension matching (bloky: width + thickness OBA ≥ target)

3. **Future (Orders v2.0):**
   - Order snapshot potřebuje material_item_id reference
   - Part.material_item_id už existuje (nullable) - ready!
   - Tento modul připraví data pro v2.0

**Příklad Excel katalogu:**
```
Pol.           | Materiál | Tvar        | Rozměry
---------------|----------|-------------|----------
1.0715-D20     | 1.0715   | Kruhová tyč | Ø20mm
1.4404-D25     | 1.4404   | Kruhová tyč | Ø25mm
PA6-DESKA-30   | PA6      | Deska       | 30mm
GG250-D50      | GG250    | Kruhová tyč | Ø50mm
```

**Excel má:**
- ✅ Kód, materiál, tvar, rozměry
- ❌ CHYBÍ: weight_per_meter, standard_length, norms, supplier_code (doplníme později)

---

## Důsledky

### ✅ Výhody

| Výhoda | Popis |
|--------|-------|
| **Katalogové rozměry** | 2405 standardních polotovarů v DB |
| **Smart matching** | Auto-najde nejbližší větší rozměr (Ø21 → Ø25) |
| **Přesnější hmotnosti** | weight_per_meter z katalogu > vypočtená |
| **Orders v2.0 ready** | Part.material_item_id snapshot připraven |
| **User-friendly UX** | "Nalezena skladová položka o 4mm větší" |

### ❌ Trade-offs

| Trade-off | Mitigace |
|-----------|----------|
| 2405 záznamů v DB | MaterialItem má 7-digit numbering (2XXXXXX) - scalable |
| weight_per_meter NULL | Fallback: calculate z geometry (existující logic) |
| Import complexity | Dry-run preview, postupný import (100× batch commits) |
| UPWARD tolerance only | Business requirement - nelze použít menší polotovar |

---

## Architektura

### 1. Data Model (READY! - Migration 2026-01-26)

```sql
-- Part má OBA fieldy (připraveno pro tento modul):
CREATE TABLE parts (
    material_item_id INTEGER NULL,      -- Konkrétní rozměr (2405 options)
    price_category_id INTEGER NULL,     -- Cenová kategorie (39 options)

    stock_shape VARCHAR(20),            -- Auto-fill z MaterialItem
    stock_diameter FLOAT,               -- Auto-fill
    stock_width FLOAT,                  -- Auto-fill
    stock_height FLOAT,                 -- Auto-fill (thickness)
    stock_wall_thickness FLOAT,         -- Auto-fill
    ...
);

-- MaterialItem (po importu):
CREATE TABLE material_items (
    id INTEGER PRIMARY KEY,
    material_number VARCHAR(7) UNIQUE NOT NULL,  -- 2XXXXXX
    code VARCHAR(50) UNIQUE NOT NULL,            -- "1.4404-D25"
    name VARCHAR(200) NOT NULL,                  -- "1.4404 Ø25mm - tyč kruhová nerez"

    shape VARCHAR(20) NOT NULL,                  -- ROUND_BAR, PLATE, ...
    diameter FLOAT NULL,                         -- mm
    width FLOAT NULL,                            -- mm
    thickness FLOAT NULL,                        -- mm
    wall_thickness FLOAT NULL,                   -- mm

    weight_per_meter FLOAT NULL,                 -- kg/m (z katalogu - OPTIONAL!)
    standard_length FLOAT NULL,                  -- mm (6000mm typicky)
    norms VARCHAR(200) NULL,                     -- "EN 10025, EN 10060"
    supplier_code VARCHAR(50) NULL,              -- "T125110001"
    supplier VARCHAR(100) NULL,
    stock_available FLOAT DEFAULT 0.0,

    material_group_id INTEGER NOT NULL,          -- FK → MaterialGroup
    price_category_id INTEGER NOT NULL,          -- FK → MaterialPriceCategory

    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    version INTEGER DEFAULT 0
);
```

**Klíčová rozhodnutí:**
- `material_number` = 7-digit (2XXXXXX) - user-facing, v URL
- `weight_per_meter` = NULLABLE (fallback na calculated weight)
- Part ukládá OBA: `material_item_id` (specifický rozměr) + `price_category_id` (cenová kategorie)

---

### 2. Import Strategy

**Workflow:**
```
1. PREP: Seed MaterialNorms (PŘED importem!)
   → MaterialNorm mapping: W.Nr → MaterialGroup

2. DRY-RUN Preview:
   python scripts/import_material_catalog.py
   → Zobrazí: MaterialGroups, PriceCategories, sample items
   → User kontrola: kategorie OK?

3. EXECUTE Import:
   python scripts/import_material_catalog.py --execute
   → Create MaterialGroups (16 kategorií)
   → Create PriceCategories (39 kombinací materiál+tvar)
   → Generate 2405× material_number (2XXXXXX)
   → Create MaterialItems (batch commit každých 100)
```

**Material Groups Mapping:**
```python
MATERIAL_GROUPS = {
    # Oceli
    "1.0": {"code": "10xxx", "name": "Ocel konstrukční", "density": 7.85},
    "1.1": {"code": "11xxx", "name": "Ocel automatová", "density": 7.85},
    "1.4": {"code": "14xxx", "name": "Nerez", "density": 7.90},

    # Neželezné kovy
    "2.0": {"code": "20xxx", "name": "Měď a slitiny mědi", "density": 8.90},
    "2.1": {"code": "21xxx", "name": "Mosaz", "density": 8.40},
    "3.0": {"code": "3xxxx", "name": "Hliník", "density": 2.70},

    # Litina (NEW - 2026-01-27)
    "GG250": {"code": "LITINA-GG", "name": "Litina šedá", "density": 7.20},
    "GGG40": {"code": "LITINA-TV", "name": "Litina tvárná", "density": 7.10},
    "GG": {"code": "LITINA-GG", "name": "Litina šedá", "density": 7.20},    # Fallback GG200, GG300
    "GGG": {"code": "LITINA-TV", "name": "Litina tvárná", "density": 7.10}, # Fallback GGG50

    # Plasty (SLOUČENO)
    "PA6": {"code": "PLAST", "name": "Plasty", "density": 1.20},
    "POM": {"code": "PLAST", "name": "Plasty", "density": 1.20},
    "POM-C": {"code": "PLAST", "name": "Plasty", "density": 1.20},
    "PE1000": {"code": "PLAST", "name": "Plasty", "density": 1.20},
}
```

**Price Categories:**
```python
def get_price_category_code(material_group_code: str, shape: str) -> tuple[str, str]:
    """
    Returns (code, name) pro PriceCategory.

    Examples:
        ("10xxx", "ROUND_BAR") → ("OCEL-KONS-KRUHOVA", "Ocel konstrukční - kruhová tyč")
        ("14xxx", "PLATE") → ("NEREZ-DESKA", "Nerez - deska")
        ("LITINA-GG", "ROUND_BAR") → ("LITINA-GG-KRUHOVA", "Litina šedá - kruhová tyč")
    """
```

---

### 3. Smart Upward Lookup

**KRITICKÉ: Tolerance UPWARD ONLY!**

```
User zadá: Ø21mm
→ Najde: Ø25mm ✅ (větší o 4mm)
→ NENAJDE: Ø20mm ❌ (menší!)

Důvod: Nelze použít menší polotovar než díl (fyzikálně nemožné).
```

**Algorithm:**

```python
async def find_nearest_upward_match(
    material_code: str,      # "1.4404"
    shape: StockShape,       # ROUND_BAR
    target_dimensions: dict, # {diameter: 21.0}
    db: AsyncSession
) -> Optional[tuple[MaterialItem, float]]:
    """
    Najde nejbližší VĚTŠÍ MaterialItem.

    Rules:
    - ROUND_BAR: item.diameter >= target.diameter
    - PLATE: item.thickness >= target.thickness
    - FLAT_BAR: item.width >= target.width AND item.thickness >= target.thickness
    - SQUARE_BAR: item.width >= target.width
    - TUBE: item.diameter >= target.diameter AND item.wall_thickness >= target.wall_thickness

    Select: MIN(diff) z valid items

    Returns:
        (matched_item, dimension_diff) nebo None pokud žádný není větší
    """

    # 1. Get MaterialGroup (via MaterialNorm mapping nebo pattern match)
    material_group = await _get_material_group(material_code, db)

    # 2. Filter: material_group_id + shape
    candidates = await db.execute(
        select(MaterialItem)
        .where(
            MaterialItem.material_group_id == material_group.id,
            MaterialItem.shape == shape
        )
    )

    # 3. Filter UPWARD (pouze >= target)
    valid_items = []

    for item in candidates:
        if shape == StockShape.ROUND_BAR:
            if item.diameter >= target['diameter']:
                diff = item.diameter - target['diameter']
                valid_items.append((item, diff))

        elif shape == StockShape.FLAT_BAR:
            # OBA rozměry musí být >=
            if (item.width >= target['width'] and
                item.thickness >= target['thickness']):
                # Euclidean distance
                diff = sqrt(
                    (item.width - target['width'])**2 +
                    (item.thickness - target['thickness'])**2
                )
                valid_items.append((item, diff))

        # ... další shapes

    if not valid_items:
        return None  # Žádný větší rozměr

    # 4. Select MIN diff
    matched_item, min_diff = min(valid_items, key=lambda x: x[1])

    return matched_item, min_diff
```

**Dimension Diff Examples:**

| Shape | Target | Catalog Item | Diff | Formula |
|-------|--------|-------------|------|---------|
| ROUND_BAR | Ø21mm | Ø25mm | 4.0mm | 25 - 21 |
| PLATE | 15mm | 20mm | 5.0mm | 20 - 15 |
| FLAT_BAR | 100×15mm | 120×20mm | 22.4mm | √((120-100)² + (20-15)²) |
| SQUARE_BAR | 40×40mm | 50×50mm | 10.0mm | 50 - 40 |

---

### 4. API Integration

**A. Rozšíření /api/materials/parse (EXISTING endpoint):**

```python
@router.get("/parse")
async def parse_material_string(
    text: str,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Parse material string + SMART LOOKUP (NEW!)

    Input: "1.4404 Ø21"
    Output: {
        # Existing parse fields
        "material_code": "1.4404",
        "shape": "ROUND_BAR",
        "diameter": 21.0,
        "suggested_material_group_name": "Nerez",

        # NEW: Smart lookup result
        "matched_material_item": {
            "id": 456,
            "material_number": "2789456",
            "name": "1.4404 Ø25mm - tyč kruhová nerez",
            "diameter": 25.0,
            "weight_per_meter": 3.85,
            "material_group": {...},
            "price_category": {...}
        },
        "dimension_diff": 4.0,
        "exact_match": false,
        "match_message": "Nalezena skladová položka o 4mm větší"
    }
    """
    # Existing parse logic (material_parser.py)
    parse_result = material_parser.parse(text)

    result = {
        "material_code": parse_result.material_code,
        "shape": parse_result.shape,
        "diameter": parse_result.diameter,
        # ... další parsované hodnoty
    }

    # NEW: Smart lookup (pokud máme material_code + shape + dimensions)
    if parse_result.material_code and parse_result.shape:
        try:
            search_service = MaterialSearchService()

            target_dims = {}
            if parse_result.diameter:
                target_dims['diameter'] = parse_result.diameter
            if parse_result.width:
                target_dims['width'] = parse_result.width
            if parse_result.thickness:
                target_dims['thickness'] = parse_result.thickness

            match_result = await search_service.find_nearest_upward_match(
                material_code=parse_result.material_code,
                shape=parse_result.shape,
                target_dimensions=target_dims,
                db=db
            )

            if match_result:
                matched_item, diff = match_result
                await db.refresh(matched_item, ['group', 'price_category'])

                exact = (diff < 0.01)
                if exact:
                    message = "Nalezena přesná skladová položka"
                else:
                    message = f"Nalezena skladová položka o {diff:.1f}mm větší"

                result.update({
                    "matched_material_item": MaterialItemWithGroupResponse.model_validate(matched_item).model_dump(),
                    "dimension_diff": diff,
                    "exact_match": exact,
                    "match_message": message
                })
        except Exception as e:
            logger.warning(f"Smart lookup failed: {e}")
            # Nepadnout celý parse, jen skip lookup

    return result
```

**B. NEW Service: MaterialSearchService:**

```python
# app/services/material_search_service.py

class MaterialSearchService:
    """Smart lookup MaterialItems s UPWARD tolerance"""

    async def find_nearest_upward_match(...) -> Optional[tuple[MaterialItem, float]]:
        """Viz Algorithm sekce výše"""

    async def _get_material_group(
        self,
        material_code: str,
        db: AsyncSession
    ) -> Optional[MaterialGroup]:
        """
        Najde MaterialGroup podle material_code.

        Strategy:
        1. Try MaterialNorm mapping (W.Nr → MaterialGroup) - PRIORITA!
        2. Fallback: Pattern matching (import_material_catalog.py logic)
        """
        # 1. MaterialNorm mapping (exact)
        result = await db.execute(
            select(MaterialGroup)
            .join(MaterialNorm)
            .where(MaterialNorm.w_nr == material_code)
        )
        group = result.scalar_one_or_none()

        if group:
            return group

        # 2. Fallback: Pattern matching
        from scripts.import_material_catalog import identify_material_group

        group_info = identify_material_group(material_code)
        if group_info:
            result = await db.execute(
                select(MaterialGroup).where(MaterialGroup.code == group_info['code'])
            )
            return result.scalar_one_or_none()

        return None
```

---

### 5. Price Calculator Integration

**weight_per_meter Priority Logic:**

```python
# app/services/price_calculator.py (rozšířit existující)

async def calculate_stock_cost_from_part(
    part: Part,
    quantity: int = 1,
    db: AsyncSession = None
) -> MaterialCost:
    """
    Výpočet ceny polotovaru s OPTIONAL MaterialItem.weight_per_meter.

    Strategy:
    1. IF Part.material_item_id AND weight_per_meter IS NOT NULL:
       → Use catalog weight (PRIORITA - přesnější!)
    2. ELSE:
       → Calculate from geometry + density (fallback)
    """

    # Eager load material_item pokud je
    if part.material_item_id and not part.material_item:
        await db.refresh(part, ['material_item', 'price_category'])

    # 1. Calculate weight_kg (per piece)
    if part.material_item and part.material_item.weight_per_meter:
        # KATALOGOVÁ HMOTNOST (priorita!)
        weight_kg = (
            part.material_item.weight_per_meter *
            part.stock_length / 1000.0
        )
        logger.info(f"Using catalog weight_per_meter: {part.material_item.weight_per_meter} kg/m")
    else:
        # FALLBACK: Geometry + density (existující logic)
        volume_dm3 = await calculate_stock_volume(part)  # Existující funkce
        density = part.price_category.material_group.density
        weight_kg = volume_dm3 * density
        logger.info(f"Calculated weight from geometry: {weight_kg} kg")

    # 2. Select price_per_kg (existing ADR-014 logic)
    total_weight = weight_kg * quantity
    price_per_kg = await get_price_per_kg_for_weight(
        part.price_category,
        total_weight,
        db
    )

    # 3. Calculate cost
    cost = weight_kg * price_per_kg

    # 4. Snapshot (pro frozen batches - ADR-012)
    return MaterialCost(
        weight_kg=round(weight_kg, 3),
        price_per_kg=round(price_per_kg, 2),
        cost=round(cost, 2),

        # NEW: Snapshot MaterialItem reference (pro Orders v2.0!)
        material_item_id=part.material_item_id,
        material_item_number=part.material_item.material_number if part.material_item else None,
    )
```

**Důsledky:**
- weight_per_meter (katalog) má přednost před vypočítanou hmotností
- Fallback zajišťuje kompatibilitu (pokud katalog nemá data)
- Snapshot v MaterialCost připraven pro Orders v2.0

---

### 6. Frontend UI (parts/edit.html)

**Material Match Card:**

```html
<!-- Match result panel (pod material dropdown) -->
<template x-if="parseResult && parseResult.matched_material_item">
    <div class="material-match-card" style="
        background: var(--bg-secondary);
        border: 2px solid var(--accent-green);
        border-radius: 8px;
        padding: 16px;
        margin-top: 12px;
    ">
        <div style="display: flex; align-items: center; gap: 12px;">
            <!-- Icon podle exact_match -->
            <span x-show="parseResult.exact_match" style="font-size: 24px;">✅</span>
            <span x-show="!parseResult.exact_match" style="font-size: 24px;">📦</span>

            <div style="flex: 1;">
                <div style="font-weight: bold; margin-bottom: 4px;">
                    <span x-text="parseResult.match_message"></span>
                </div>
                <div style="font-size: 14px; color: var(--text-secondary);">
                    <strong x-text="parseResult.matched_material_item.name"></strong>
                </div>

                <!-- Dimensions preview -->
                <div style="margin-top: 8px; font-size: 13px;">
                    <!-- Round bar -->
                    <template x-if="parseResult.matched_material_item.shape === 'ROUND_BAR'">
                        <span>Průměr: <strong x-text="parseResult.matched_material_item.diameter"></strong>mm</span>
                    </template>

                    <!-- Plate -->
                    <template x-if="parseResult.matched_material_item.shape === 'PLATE'">
                        <span>Tloušťka: <strong x-text="parseResult.matched_material_item.thickness"></strong>mm</span>
                    </template>

                    <!-- Flat bar -->
                    <template x-if="parseResult.matched_material_item.shape === 'FLAT_BAR'">
                        <span>
                            <strong x-text="parseResult.matched_material_item.width"></strong>×<strong x-text="parseResult.matched_material_item.thickness"></strong>mm
                        </span>
                    </template>

                    <!-- Weight info (pokud je v DB) -->
                    <template x-if="parseResult.matched_material_item.weight_per_meter">
                        <span style="margin-left: 12px; color: var(--text-tertiary);">
                            | <span x-text="parseResult.matched_material_item.weight_per_meter.toFixed(2)"></span> kg/m
                        </span>
                    </template>
                </div>
            </div>

            <!-- Action button -->
            <button
                @click="applyMaterialItem(parseResult.matched_material_item)"
                class="btn-primary"
                style="white-space: nowrap;"
            >
                Použít
            </button>
        </div>
    </div>
</template>
```

**Alpine.js Logic:**

```javascript
// app/templates/parts/edit.html (Alpine.js component)

async applyMaterialItem(matchedItem) {
    // Auto-fill OBA fieldy + geometry
    this.partData.material_item_id = matchedItem.id;
    this.partData.price_category_id = matchedItem.price_category.id;

    // Auto-fill geometry z MaterialItem
    this.partData.stock_shape = matchedItem.shape;

    if (matchedItem.diameter) {
        this.partData.stock_diameter = matchedItem.diameter;
    }
    if (matchedItem.width) {
        this.partData.stock_width = matchedItem.width;
    }
    if (matchedItem.thickness) {
        this.partData.stock_height = matchedItem.thickness;  // Note: Part má stock_height
    }
    if (matchedItem.wall_thickness) {
        this.partData.stock_wall_thickness = matchedItem.wall_thickness;
    }

    // Update UI (selectedMaterial pro display)
    this.selectedMaterial = matchedItem.price_category;
    this.materialSearch = matchedItem.price_category.name;

    // Clear parseResult (hide match panel)
    this.parseResult = null;

    // Refresh batches (price calculation s NOVÝM MaterialItem!)
    await this.loadBatches();
}
```

---

## User Workflow

**Krok za krokem:**

```
1. User: Otevře parts/edit.html
2. User: Zadá do chytrého vyhledávání: "1.4404 Ø21"
3. System:
   - Parse API extrahuje: material_code=1.4404, shape=ROUND_BAR, diameter=21
   - Smart lookup najde: MaterialItem "1.4404 Ø25mm" (diff=4mm)
   - Vrátí: matched_material_item + dimension_diff + match_message
4. UI: Zobrazí match result card:
   📦 Nalezena skladová položka o 4mm větší
   1.4404 Ø25mm - tyč kruhová nerez
   Průměr: 25mm | 3.85 kg/m
   [Použít]
5. User: Klikne "Použít"
6. System:
   - Uloží Part.material_item_id = 456
   - Uloží Part.price_category_id = 5
   - Auto-fill: stock_shape, stock_diameter, ...
   - Recalculate batches (s weight_per_meter z katalogu!)
7. UI: Batch prices aktualizovány (přesnější hmotnost!)
```

---

## Implementation Tasks

### PREP (před importem):

```bash
# 1. Seed MaterialNorms (MANDATORY!)
python scripts/seed_material_norms.py

# Verification:
sqlite3 gestima.db "SELECT COUNT(*) FROM material_norms;"
# → mělo by vrátit ~48 záznamů
```

### Import Phase:

```bash
# 2. Preview import (DRY-RUN)
python scripts/import_material_catalog.py

# 3. Execute import
python scripts/import_material_catalog.py --execute

# Verification:
sqlite3 gestima.db "SELECT COUNT(*) FROM material_items;"
# → mělo by vrátit ~2405 záznamů
```

### Backend Implementation:

- [ ] **MaterialSearchService** (`app/services/material_search_service.py`)
  - [ ] `find_nearest_upward_match()` - upward tolerance algorithm
  - [ ] `_get_material_group()` - MaterialNorm mapping + fallback
  - [ ] Unit tests (exact match, upward match, no match, multi-dim)

- [ ] **API Integration** (`app/routers/materials_router.py`)
  - [ ] Rozšířit `/api/materials/parse` (smart lookup integration)
  - [ ] Error handling (no match → 404 with message)

- [ ] **Price Calculator** (`app/services/price_calculator.py`)
  - [ ] weight_per_meter priority logic
  - [ ] MaterialCost snapshot fields (material_item_id, material_item_number)

- [ ] **Import Execution** (`scripts/import_material_catalog.py`)
  - [ ] `execute_import()` implementace
  - [ ] MaterialGroup creation (if not exists)
  - [ ] PriceCategory creation (if not exists)
  - [ ] MaterialItem batch creation (100× commit)
  - [ ] NumberGenerator integration (2XXXXXX range)

### Frontend Implementation:

- [ ] **Match Result Card** (`app/templates/parts/edit.html`)
  - [ ] HTML template (icon, message, dimensions, button)
  - [ ] Dimension preview per shape (ROUND_BAR, PLATE, FLAT_BAR, ...)
  - [ ] Weight preview (pokud weight_per_meter exists)

- [ ] **Alpine.js Logic**
  - [ ] `applyMaterialItem()` function
  - [ ] Auto-fill fields (material_item_id, price_category_id, geometry)
  - [ ] Batch recalculation trigger

### Testing:

- [ ] **Unit Tests** (`tests/test_material_search.py`)
  - [ ] test_exact_match() - Ø20 → Ø20 (diff=0)
  - [ ] test_upward_match() - Ø21 → Ø25 (diff=4)
  - [ ] test_no_smaller_match() - Ø21 NE Ø20!
  - [ ] test_multi_dimension() - bloky (width + thickness)
  - [ ] test_no_match_found() - žádný větší rozměr

- [ ] **Integration Tests** (`tests/test_material_integration.py`)
  - [ ] test_parse_with_lookup() - parse API vrací matched_item
  - [ ] test_apply_material_item() - uloží OBA fieldy
  - [ ] test_catalog_weight_priority() - weight_per_meter > calculated

- [ ] **Import Tests** (`tests/test_material_import.py`)
  - [ ] test_import_execution() - vytvoří MaterialItems
  - [ ] test_material_number_uniqueness() - žádné duplicity
  - [ ] test_fk_integrity() - MaterialGroup + PriceCategory exist

### Documentation:

- [ ] **CHANGELOG.md** - Material Catalog Import & Smart Lookup feature
- [ ] **UI-GUIDE.md** - Material Lookup workflow screenshots
- [ ] **NEXT-STEPS.md** - Update s novým modulem

---

## Orders v2.0 Integration (Future)

**Snapshot Strategy:**

```python
# v2.0 Orders (Q1 2026) - PŘIPRAVENO!

Order.part_snapshot = {
    # Existing fields (z Batch snapshot)
    "part_id": 123,
    "part_number": "1234567",
    "length": 150.0,

    # NEW: MaterialItem snapshot
    "material_item_id": 456,
    "material_item_number": "2789456",  # User-facing
    "material_item_name": "1.4404 Ø25mm - tyč kruhová nerez",
    "weight_per_meter": 3.85,           # Frozen catalog weight

    # Frozen pricing
    "price_category_id": 5,
    "price_per_kg": 119.3,              # Frozen tier price

    # Snapshot metadata
    "snapshot_date": "2026-01-27T10:00:00Z"
}
```

**Proč je to kritické:**
- Order musí být **immutable** (ceny se mění, Order zůstává)
- MaterialItem může být smazán → snapshot zachová info
- Audit-proof (reprodukovatelné kalkulace)
- PDF export Orders → zobrazí material_item_name

---

## Alternativy (zamítnuté)

### 1. Bidirectional Tolerance (±)

```python
# User zadá: Ø21mm
# → Najde: Ø20mm (diff=-1mm) nebo Ø25mm (diff=+4mm)
```

**Zamítnuto:**
- Fyzikálně nemožné použít menší polotovar (Ø20 pro díl Ø21)
- User requirement: "Tolerance vždy do plusu"
- UPWARD ONLY je business requirement

### 2. Catalog weight_per_meter MANDATORY

```python
# Import failne pokud weight_per_meter IS NULL
```

**Zamítnuto:**
- Excel katalog NEMÁ weight_per_meter sloupec
- Fallback na calculated weight funguje dobře
- Můžeme doplnit později (UPDATE material_items SET weight_per_meter)

### 3. Separate API Endpoint (ne integrace do /parse)

```python
# NEW: POST /api/materials/items/search-dimension
```

**Zamítnuto:**
- Redundantní (parse už dělá to samé)
- Extra API call = latence
- Integrace do /parse je čistší UX (1 request)

### 4. Manual MaterialItem Selection (dropdown)

```
User vybírá z 2405 položek v dropdownu
```

**Zamítnuto:**
- Nepoužitelné UX (2405 options)
- Smart lookup řeší automaticky
- Dropdown jen pro PriceCategory (39 options - OK)

---

## Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Import selže (bad data) | MEDIUM | HIGH | Dry-run preview před execute, batch commits |
| MaterialNorm mapping incomplete | MEDIUM | MEDIUM | Fallback na pattern matching (identify_material_group) |
| No upward match found | LOW | MEDIUM | Error message: "Žádná skladová položka >= rozměr" |
| weight_per_meter NULL všude | LOW | LOW | Fallback na calculated weight (funguje dnes) |
| 2405 čísel generuje duplicity | VERY LOW | HIGH | NumberGenerator retry logic (jako u Parts) |

---

## Related ADRs

- **ADR-011:** Material Hierarchy (Two-Tier Model) - základ pro MaterialItem
- **ADR-014:** Material Price Tiers - cenová strategie podle množství
- **ADR-012:** Minimal Snapshot Strategy - snapshot pattern pro frozen data
- **ADR-017:** 7-Digit Random Entity Numbering - material_number formát
- **ADR-015:** Material Norm Mapping - MaterialNorm → MaterialGroup

---

## Effort Estimate

**Total:** ~12 hodin (AI-accelerated)

| Task | Effort | Priority |
|------|--------|----------|
| MaterialSearchService (backend) | 3h | HIGH |
| API integration (/parse rozšíření) | 2h | HIGH |
| Frontend UI (match card + Alpine.js) | 2h | HIGH |
| Price calculator integration | 1h | HIGH |
| Import execution (execute_import) | 2h | HIGH |
| Testing (unit + integration) | 2h | MEDIUM |
| Documentation (CHANGELOG, UI-GUIDE) | 1h | MEDIUM |

---

## Schválení

⏳ **ČEKÁ NA:**
1. Seed MaterialNorms (PREP)
2. Import catalog --execute
3. User verification (kontrola importovaných dat)

🎯 **READY FOR:**
- v2.0 Orders preparation
- User workflow optimization
- Catalog weight precision

---

**Status:** 📋 NAVRŽENO (ready for implementation)
**Next Step:** `python scripts/seed_material_norms.py` → `python scripts/import_material_catalog.py --execute`
