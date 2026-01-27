# ADR-014: Material Price Tiers (Dynamic Quantity-Based Pricing)

**Datum:** 2026-01-26
**Status:** ✅ SCHVÁLENO
**Kontext:** Beta release - Material pricing podle množství (PDF ceník)

---

## Rozhodnutí

Implementujeme **dynamické cenové tiers pro materiály** podle celkového množství:

1. **MaterialPriceCategory** - Cenová kategorie (např. "OCEL konstrukční - kruhová tyč")
2. **MaterialPriceTier** - Konfigurovatelné cenové pásmo (min_weight, max_weight, price_per_kg)
3. Výběr ceny: **Největší min_weight ≤ total_weight_kg** (nejbližší nižší tier)

`MaterialItem` odkazuje na `MaterialPriceCategory` (místo flat `price_per_kg`).

---

## Kontext

**Problém:**
- Současný model: `MaterialItem.price_per_kg` = jedna flat cena (45 Kč/kg)
- Realita: Množstevní slevy podle PDF ceníku (malý <15kg, střední 15-100kg, velký >100kg)
- Požadavek: Centralizovaná údržba cen (13 kategorií místo stovek položek)
- Future-proof: Možnost přidat tiers nad 1000 kg bez změny kódu

**Příklad z PDF:**
```
OCEL konstrukční - kruhová tyč:
  - 0-15 kg:    49.4 Kč/kg
  - 15-100 kg:  34.5 Kč/kg
  - 100+ kg:    26.3 Kč/kg
```

**Požadavky:**
1. Dynamické tiers (admin konzole v budoucnu)
2. Výběr ceny: Nejbližší nižší tier
3. Frozen batches: Snapshot `price_per_kg` (imunní vůči změnám)
4. Implementovat pro beta release

---

## Důsledky

### ✅ Výhody

| Výhoda | Popis |
|--------|-------|
| **Centralizovaná údržba** | 13 kategorií (~40 tiers) místo stovek cen v MaterialItems |
| **Množstevní slevy** | Automaticky podle batch quantity (weight × quantity) |
| **Škálovatelnost** | Přidat nový tier (např. 1000+ kg) = INSERT bez změny kódu |
| **1:1 PDF mapping** | Přesná implementace reálného ceníku |
| **Admin-friendly** | Budoucí UI pro správu tiers (CRUD bez deploymentu) |

### ❌ Nevýhody

| Nevýhoda | Mitigace |
|----------|----------|
| Složitější queries (2 JOINy) | Eager loading (`selectinload`) - latence <10ms |
| Breaking change (remove price_per_kg) | Nemáme produkční data - clean slate |
| Vyšší initial effort (9h) | Vyplatí se dlouhodobě (škálovatelnost) |

---

## Alternativy (zamítnuté)

### 1. Tři fixed fieldy v MaterialItem
```python
class MaterialItem:
    price_small = 49.4
    price_medium = 34.5
    price_large = 26.3
```
**Zamítnuto:** Duplikace cen pro každý průměr. Nelze přidat tiers nad 1000 kg bez DB schema změny.

### 2. Hardcoded IF-ELSE v price_calculator.py
```python
if total_weight <= 15:
    return 49.4
elif total_weight <= 100:
    return 34.5
```
**Zamítnuto:** Nelze konfigurovat z admin UI. Změna cen = code deployment.

### 3. Tier podle váhy 1 kusu (ne batch)
```python
# Malý díl (0.1 kg) = vždy malý tier
```
**Zamítnuto:** Nesmysl - 1000× malý díl = velký nákup materiálu = měl by mít velký tier.

### 4. Cenová historie (valid_from/valid_to)
**Zamítnuto:** Overkill pro beta. Snapshot pattern (ADR-012) stačí pro frozen batches.

---

## Datový model

```
┌─────────────────────────┐
│ MaterialPriceCategory   │  (13 záznamů podle PDF)
├─────────────────────────┤
│ id                      │ PK
│ code                    │ UNIQUE  "OCEL-KRUHOVA"
│ name                    │         "OCEL konstrukční - kruhová tyč"
└────────┬────────────────┘
         │ 1:N
         │
┌────────▼────────────────┐
│ MaterialPriceTier       │  (~40 záznamů: 3 tiers × 13 kategorií)
├─────────────────────────┤
│ id                      │ PK
│ price_category_id       │ FK → MaterialPriceCategory
│ min_weight              │ FLOAT   0, 15, 100
│ max_weight              │ FLOAT?  15, 100, NULL (= ∞)
│ price_per_kg            │ FLOAT   49.4, 34.5, 26.3
└─────────────────────────┘
         ↑
         │ N:1
         │
┌────────┴────────────────┐
│ MaterialItem            │  (Stovky záznamů)
├─────────────────────────┤
│ material_group_id       │ FK → MaterialGroup (hustota)
│ price_category_id       │ FK → MaterialPriceCategory (ceny)
│ [REMOVED: price_per_kg] │
└─────────────────────────┘
         ↑
         │ 1:N
         │
┌────────┴────────────────┐
│ Part                    │
└─────────────────────────┘
```

---

## Použití ve výpočtech

### Výběr správného tier
```python
async def get_price_per_kg_for_weight(
    price_category: MaterialPriceCategory,
    total_weight_kg: float,
    db: AsyncSession
) -> float:
    """
    Najde správný tier podle celkové váhy.
    Pravidlo: Největší min_weight ≤ total_weight (nejbližší nižší).
    """
    # Filtrovat tiers: min_weight <= total_weight
    valid_tiers = [
        t for t in price_category.tiers
        if t.min_weight <= total_weight
    ]

    if not valid_tiers:
        logger.error(f"No valid tier for weight {total_weight}kg")
        return 0

    # Vybrat tier s největším min_weight
    selected_tier = max(valid_tiers, key=lambda t: t.min_weight)

    return selected_tier.price_per_kg
```

### Příklad
```
Tiers:
  - [0, 15):   49.4 Kč/kg
  - [15, 100): 34.5 Kč/kg
  - [100, ∞):  26.3 Kč/kg

Díl: 0.5 kg/ks

Batch 10 ks = 5 kg:
  → valid_tiers = [0]
  → max(0) = 0
  → 49.4 Kč/kg ✅

Batch 50 ks = 25 kg:
  → valid_tiers = [0, 15]
  → max(0, 15) = 15
  → 34.5 Kč/kg ✅

Batch 300 ks = 150 kg:
  → valid_tiers = [0, 15, 100]
  → max(0, 15, 100) = 100
  → 26.3 Kč/kg ✅
```

### Integrace s price_calculator.py
```python
async def calculate_stock_cost_from_part(
    part,
    quantity: int = 1,
    db: AsyncSession = None
) -> MaterialCost:
    """Výpočet ceny polotovaru s dynamickými price tiers."""
    # ... výpočet volume, weight_kg ...

    # NOVÉ: Dynamický výběr ceny podle quantity
    total_weight = weight_kg * quantity
    price_per_kg = await get_price_per_kg_for_weight(
        part.material_item.price_category,
        total_weight,
        db
    )

    cost = weight_kg * price_per_kg  # Cena za 1 ks

    result.price_per_kg = price_per_kg  # Pro snapshot (ADR-012)
    result.cost = round(cost, 2)

    return result
```

---

## Seed Data (podle PDF)

13 kategorií podle PDF ceníku:

| Code | Name | Tiers (kg) | Prices (Kč/kg) |
|------|------|-----------|----------------|
| OCEL-KRUHOVA | OCEL konstrukční - kruhová tyč | 0-15, 15-100, 100+ | 49.4, 34.5, 26.3 |
| OCEL-PLOCHA | OCEL konstrukční - plochá tyč | 0-15, 15-100, 100+ | 57.1, 40.9, 30.7 |
| OCEL-DESKY | OCEL konstrukční - desky/bloky | 0+ | 30.0 |
| OCEL-TRUBKA | OCEL konstrukční - trubka | 0-15, 15-100 | 210.3, 139.4 |
| NEREZ-KRUHOVA | NEREZ - kruhová tyč | 0-15, 15-100 | 119.3, 104.6 |
| NEREZ-PLOCHA | NEREZ - plochá tyč | 0-15, 15-100 | 205.0, 168.0 |
| HLINIK-DESKY | HLINÍK - desky a bloky | 0-15, 15-100 | 117.9, 108.0 |
| HLINIK-KRUHOVA | HLINÍK - kruhová tyč | 0-15, 15-100 | 179.4, 150.5 |
| HLINIK-PLOCHA | HLINÍK - plochá tyč | 0-15, 15-100 | 151.6, 146.8 |
| PLASTY-DESKY | PLASTY (POM/PA6) - desky | 0+ | 336.9 |
| PLASTY-TYCE | PLASTY (POM/PA6) - tyče | 0-15, 15-100 | 177.2, 177.4 |
| OCEL-NASTROJOVA | OCEL nástrojová - kruhová tyč | 0-15, 15-100 | 104.0, 95.0 |
| MOSAZ-BRONZ | MOSAZ/BRONZ - kruhová tyč | 0-15, 15-100 | 320.0, 290.0 |

**Poznámka:** Některé kategorie mají jen 1 tier (např. OCEL-DESKY) = flat price.

---

## Migration

**Breaking change:** `MaterialItem.price_per_kg` → `MaterialItem.price_category_id`

```python
# Migration steps:
# 1. Vytvořit material_price_categories (seed 13 kategorií)
# 2. Vytvořit material_price_tiers (seed ~40 tiers)
# 3. Přidat MaterialItem.price_category_id (nullable)
# 4. Update existující items (manual mapping podle code patterns)
# 5. Nastavit price_category_id NOT NULL
# 6. Drop MaterialItem.price_per_kg
```

**Stav:** Nemáme produkční data → čistá migrace bez data loss rizika.

---

## Testování

```python
# tests/test_material_price_tiers.py

async def test_tier_selection_small():
    """Malé množství (5 kg) → malý tier (49.4 Kč/kg)"""
    category = MaterialPriceCategory(code="OCEL-KRUHOVA", ...)
    category.tiers = [
        MaterialPriceTier(min_weight=0, max_weight=15, price_per_kg=49.4),
        MaterialPriceTier(min_weight=15, max_weight=100, price_per_kg=34.5),
        MaterialPriceTier(min_weight=100, max_weight=None, price_per_kg=26.3),
    ]

    price = await get_price_per_kg_for_weight(category, 5.0, db)
    assert price == 49.4

async def test_tier_selection_medium():
    """Střední množství (25 kg) → střední tier (34.5 Kč/kg)"""
    price = await get_price_per_kg_for_weight(category, 25.0, db)
    assert price == 34.5

async def test_tier_selection_large():
    """Velké množství (150 kg) → velký tier (26.3 Kč/kg)"""
    price = await get_price_per_kg_for_weight(category, 150.0, db)
    assert price == 26.3

async def test_batch_pricing_with_tiers():
    """Výpočet batch ceny s dynamickými tiers"""
    part = await create_demo_part()  # 0.5 kg díl

    # Batch 10 ks = 5 kg → malý tier
    cost_10 = await calculate_stock_cost_from_part(part, 10, db)
    assert cost_10.price_per_kg == 49.4

    # Batch 50 ks = 25 kg → střední tier
    cost_50 = await calculate_stock_cost_from_part(part, 50, db)
    assert cost_50.price_per_kg == 34.5

    # Batch 300 ks = 150 kg → velký tier
    cost_300 = await calculate_stock_cost_from_part(part, 300, db)
    assert cost_300.price_per_kg == 26.3

async def test_frozen_batch_snapshot():
    """Frozen batch má snapshot ceny (imunní vůči změnám)"""
    batch = await create_frozen_batch(quantity=100)
    original_price = batch.snapshot.price_per_kg

    # Změnit cenu v tier
    await update_tier_price(tier_id=1, new_price=99.9)

    # Batch pořád má původní cenu
    await db.refresh(batch)
    assert batch.snapshot.price_per_kg == original_price
```

---

## Future: Admin UI

**Material Price Categories:**
```
┌─────────────────────────────────────────────┐
│ Material Price Categories                   │
├─────────────────────────────────────────────┤
│ [+ Nová kategorie]                          │
│                                             │
│ OCEL-KRUHOVA - OCEL konstrukční - kruhová   │
│   Tiers: 3  [Edit] [Delete]                 │
│                                             │
│ NEREZ-PLOCHA - NEREZ - plochá tyč           │
│   Tiers: 2  [Edit] [Delete]                 │
└─────────────────────────────────────────────┘
```

**Edit Category (s tiers subgrid):**
```
┌─────────────────────────────────────────────┐
│ Edit: OCEL-KRUHOVA                          │
├─────────────────────────────────────────────┤
│ Code: OCEL-KRUHOVA                          │
│ Name: OCEL konstrukční - kruhová tyč        │
│                                             │
│ Price Tiers:                                │
│ ┌─────────────────────────────────────────┐ │
│ │ Min (kg) │ Max (kg) │ Price (Kč/kg)  │  │ │
│ ├──────────┼──────────┼────────────────┼──┤ │
│ │ 0        │ 15       │ 49.4           │⚙ │ │
│ │ 15       │ 100      │ 34.5           │⚙ │ │
│ │ 100      │ ∞        │ 26.3           │⚙ │ │
│ └─────────────────────────────────────────┘ │
│ [+ Přidat tier]                             │
│                                             │
│ [Uložit] [Zrušit]                           │
└─────────────────────────────────────────────┘
```

**Validace:**
- Žádné mezery mezi tiers (min[i+1] = max[i])
- Žádné překryvy
- Rostoucí cena s klesajícím min_weight (warning, ne error)

---

## Related

- **ADR-011:** Material Hierarchy (Two-Tier Model) - základ pro tento ADR
- **ADR-012:** Minimal Snapshot Strategy - snapshot `price_per_kg` pro frozen batches
- **L-006:** Anti-pattern "Hardcoded data" - řeší dynamickou konfiguraci

---

## Schváleno

✅ **Senior Development Team** - 2026-01-26

**Implementace:** Beta release (Priorita HIGH)
**Effort:** ~9 hodin
**Breaking:** Ano (remove price_per_kg), ale nemáme produkční data
