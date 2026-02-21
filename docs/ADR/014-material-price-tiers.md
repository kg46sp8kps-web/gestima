# ADR-014: Material Price Tiers (Quantity-Based Pricing)

**Status:** Accepted (2026-01-26)

## Context

Flat `price_per_kg` na `MaterialItem` neodráží realitu — reálný ceník má množstevní slevy (malý <15 kg, střední 15-100 kg, velký >100 kg). Potřebujeme centralizovanou správu cen pro 13 kategorií místo stovek položek.

## Decision

**Dynamické cenové tiers**: nové modely `MaterialPriceCategory` + `MaterialPriceTier`, výběr ceny podle `total_weight_kg` batche (největší `min_weight <= total_weight`).

`MaterialItem.price_per_kg` odstraněno, nahrazeno FK `price_category_id`.

## Key Files / Models

```
MaterialPriceCategory  ← 13 kategorií (OCEL-KRUHOVA, NEREZ-PLOCHA, ...)
    └── MaterialPriceTier  ← ~40 záznamů: min_weight, max_weight, price_per_kg
MaterialItem.price_category_id FK → MaterialPriceCategory
```

- `app/models/material.py` — oba nové modely
- `app/services/price_calculator.py` — `get_price_per_kg_for_weight()`
- `scripts/seed_price_categories.py`, `scripts/seed_price_tiers.py`

## Tier Selection Logic

```python
# Největší min_weight <= total_weight_kg
valid_tiers = [t for t in category.tiers if t.min_weight <= total_weight]
selected = max(valid_tiers, key=lambda t: t.min_weight)
return selected.price_per_kg
```

Příklad (OCEL-KRUHOVA): 5 kg → 49.4 Kč/kg | 25 kg → 34.5 Kč/kg | 150 kg → 26.3 Kč/kg

## Seed Data (z PDF ceníku)

13 kategorií: OCEL-KRUHOVA, OCEL-PLOCHA, OCEL-DESKY, OCEL-TRUBKA, NEREZ-KRUHOVA,
NEREZ-PLOCHA, HLINIK-DESKY, HLINIK-KRUHOVA, HLINIK-PLOCHA, PLASTY-DESKY,
PLASTY-TYCE, OCEL-NASTROJOVA, MOSAZ-BRONZ — viz `scripts/seed_price_tiers.py`

## Consequences

- Centralizovaná údržba: 13 kategorií (~40 tiers) místo ceny na každém MaterialItem
- Přidání nového tier = INSERT do DB, žádná změna kódu
- Snapshot (ADR-012) zachycuje `price_per_kg` v momentu zmrazení — imunní vůči změnám tiers
- Breaking change: `price_per_kg` odstraněno z `MaterialItem` (provedeno při clean slate, bez prod. dat)
- Queries vyžadují eager loading (`selectinload`) pro tiers — latence <10 ms

## References

- ADR-011: Material Hierarchy (Two-Tier Model)
- ADR-012: Minimal Snapshot Strategy
