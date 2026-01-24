# ADR-011: Material Hierarchy (Two-Tier Model)

**Datum:** 2026-01-24
**Status:** ✅ SCHVÁLENO
**Kontext:** Fáze A - Refactoring materiálů z hardcoded dat do DB

---

## Rozhodnutí

Implementujeme **dvoustupňovou hierarchii materiálů**:

1. **MaterialGroup** - Kategorie pro výpočty (hustota, řezné podmínky)
2. **MaterialItem** - Konkrétní polotovar (geometrie, cena)

`Part` (díl) odkazuje na `MaterialItem` (FK), čímž eliminujeme volný text v `stock_type`.

---

## Kontext

**Problém:**
- Materiály hardcoded v JS/HTML (L-006 anti-pattern)
- `Part.stock_type` jako string → nelze validovat, počítat váhu, linkovat ceny
- Nelze škálovat na stovky druhů polotovarů

**Požadavek:**
- Hierarchie: Kategorie (pro výpočty) + Položky (pro ekonomiku/skladování)
- Škálovatelnost: Stovky `MaterialItems`, desítky `MaterialGroups`

---

## Důsledky

### ✅ Výhody

| Výhoda | Popis |
|--------|-------|
| **Single Source of Truth** | Ceny, hustota, geometrie v DB (ne hardcoded) |
| **Škálovatelnost** | Snadné přidání nových polotovarů (admin UI) |
| **Validace** | FK integrity → nelze vytvořit Part s neexistujícím materiálem |
| **Separace concerns** | Výpočty (density) oddělené od ekonomiky (price_per_kg) |
| **Údržba cen** | Editace price_per_kg na 1 místě (MaterialItem) |

### ❌ Nevýhody

| Nevýhoda | Mitigace |
|----------|----------|
| Složitější queries (JOIN 2 tabulky) | Eager loading (`selectinload`) |
| UI performance (stovky options v selectu) | Future: Autocomplete nebo lazy loading |
| Breaking change (odstranění `stock_type`) | Není problém - nemáme produkční data |

---

## Alternativy (zamítnuté)

### 1. Flat struktura (1 tabulka Materials)
```python
class Material(Base):
    code = "1.0715-D20"
    density = 7.85  # DUPLIKACE pro každý průměr!
    price_per_kg = 45.50
```
**Zamítnuto:** Duplikace `density` pro každý průměr (D20, D25, D30...).

### 2. Polymorphic (Group/Item dědí z Material)
```python
class Material(Base):
    type = Column(String)  # "group" | "item"

class MaterialGroup(Material):
    __mapper_args__ = {'polymorphic_identity': 'group'}
```
**Zamítnuto:** Over-engineering, složitější queries.

### 3. God Table (Item univerzální pro Part/Material/Nástroj)
**Zamítnuto v auditu:** Porušení separace "Engineering" vs "Master Data".

---

## Datový model

```
┌─────────────────┐
│ MaterialGroup   │  (15-20 záznamů: Ocel automatová, Hliník 6060, ...)
├─────────────────┤
│ id              │ PK
│ code            │ UNIQUE  "11xxx", "S235"
│ name            │         "Ocel automatová"
│ density         │ FLOAT   7.85 kg/dm³
└────────┬────────┘
         │ 1:N
         │
┌────────▼────────┐
│ MaterialItem    │  (Stovky záznamů: 1.0715-D20, 1.0715-D25, ...)
├─────────────────┤
│ id              │ PK
│ code            │ UNIQUE  "1.0715-D20"
│ name            │         "1.0715 D20 - tyč kruhová ocel"
│ shape           │ ENUM    ROUND_BAR, SQUARE_BAR, PLATE
│ diameter        │ FLOAT   20 mm (pro round_bar)
│ width           │ FLOAT   (pro square/plate)
│ thickness       │ FLOAT   (pro plate)
│ price_per_kg    │ FLOAT   45.50 Kč/kg (LIVE cena)
│ supplier        │ STRING
│ material_group_id│ FK → MaterialGroup
└────────┬────────┘
         │ 1:N
         │
┌────────▼────────┐
│ Part            │
├─────────────────┤
│ material_item_id│ FK → MaterialItem (MÍSTO stock_type string)
└─────────────────┘
```

---

## Použití ve výpočtech

```python
# Výpočet váhy polotovaru
def calculate_stock_weight(part: Part) -> float:
    item = part.material_item       # Geometrie (diameter, shape)
    group = item.group              # Hustota (density)

    volume = calculate_volume(item.shape, item.diameter, part.length)
    weight = volume * group.density
    return weight

# Výpočet nákladů na materiál
def calculate_material_cost(part: Part, quantity: int) -> float:
    weight = calculate_stock_weight(part)
    price_per_kg = part.material_item.price_per_kg  # LIVE cena
    return weight * price_per_kg * quantity
```

---

## Migrace

**Stav:** Nemáme produkční data → žádná migrace nutná.

**Akce:**
1. Vytvořit tabulky `material_groups`, `material_items`
2. Odstranit `Part.stock_type`, `Part.material_group`
3. Přidat `Part.material_item_id` (FK, NOT NULL)
4. Seed data: 4 groups, 10-20 items (základní polotovary)

---

## Testování

```python
# tests/test_material_hierarchy.py
async def test_create_part_with_material_item():
    """Part musí mít validní material_item_id"""
    item = await create_material_item(code="1.0715-D20", ...)
    part = await create_part(material_item_id=item.id)
    assert part.material_item.code == "1.0715-D20"

async def test_calculate_weight_uses_group_density():
    """Váha se počítá z MaterialGroup.density"""
    group = MaterialGroup(density=7.85)
    item = MaterialItem(group=group, diameter=20, shape=ROUND_BAR)
    part = Part(material_item=item, length=100)

    weight = calculate_stock_weight(part)
    # π × (10mm)² × 100mm × 7.85 kg/dm³
    assert weight > 0
```

---

## Related

- **ADR-002:** Snapshot Pattern (potřebuje Material.price_per_kg v DB)
- **ADR-012:** Minimal Snapshot Strategy (závisí na této implementaci)
- **L-006:** Anti-pattern "Hardcoded data" (řeší tento ADR)

---

## Schváleno

✅ **Senior Development Team** - 2026-01-24

**Implementace:** Fáze A (Priorita 1)
