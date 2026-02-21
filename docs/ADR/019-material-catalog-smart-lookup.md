# ADR-019: Material Catalog Import & Smart Upward Lookup

**Datum:** 2026-01-27
**Status:** NAVRZENO (ceka na implementaci po seed norms + import)
**Kontext:** v1.4.0 Costing → v2.0 Orders preparation

---

## Context

Excel katalog 2405 materialovych polotovaru neni v databazi. User musi rucne zadavat rozmery. Chybi katalogova `weight_per_meter` → nepresne hmotnosti.

Pri zadani rozmeru (Ø21mm) je nutne najit nejblizsi VETSI rozmer v katalogu (Ø25mm), ne mensi — fizikalne nelze pouzit mensi polotovar nez dil.

---

## Decision

Implementujeme:

1. **Material Catalog Import** — 2405 polotovaru z Excelu do `material_items` tabulky
2. **Smart Upward Lookup** — najde nejblizsi VETSI rozmer (UPWARD ONLY, tolerance >=)
3. **Catalog Weight Priority** — `weight_per_meter` z katalogu > vypocitana hmotnost
4. **Part.material_item_id** — Part ukla OBA: `material_item_id` + `price_category_id`

**Workflow:**
```
User zadá: "1.4404 Ø21mm"
  → Parse API: material_code=1.4404, shape=ROUND_BAR, diameter=21
  → Smart Lookup: najde MaterialItem "1.4404 Ø25mm" (diff=4mm)
  → UI: "Nalezena skladová položka o 4mm větší, chcete použít?"
  → Apply: uloží material_item_id + price_category_id + auto-fill geometry
```

**Upward Tolerance Rules:**
- ROUND_BAR: `item.diameter >= target.diameter`
- FLAT_BAR: `item.width >= target.width AND item.thickness >= target.thickness`
- TUBE: `item.diameter >= target.diameter AND item.wall_thickness >= target.wall_thickness`
- Select: MIN(diff) z validnich polozek

---

## Consequences

### Vyhody
- 2405 standardnich polotovaru v DB
- Auto-najde nejblizsi vetsi rozmer (Ø21 → Ø25)
- `weight_per_meter` z katalogu — presnejsi hmotnosti
- Part.material_item_id snapshot pripraven pro Orders v2.0

### Trade-offs
- `weight_per_meter` muze byt NULL → fallback na vypocitanou hmotnost (existujici logika)
- +1 API call pri parse → integrovano primo do `/api/materials/parse` (ne extra endpoint)

---

## Implementace

**Backend:**
- `app/services/material_search_service.py` — `find_nearest_upward_match()`, `_get_material_group()`
- `app/routers/materials_router.py` — rozsireni `/api/materials/parse` o smart lookup
- `app/services/price_calculator.py` — `weight_per_meter` prioritni logika

**Import:**
- `scripts/import_material_catalog.py` — dry-run + `--execute`, batch commits po 100
- Prerequisite: `python scripts/seed_material_norms.py` (W.Nr → MaterialGroup mapping)

**Frontend:**
- Match Result Card pod material search polem
- `applyMaterialItem()` — auto-fill `material_item_id`, `price_category_id`, geometry fields

**Data Model:**
- `material_items.material_number` — 7-digit format (2XXXXXX)
- `material_items.weight_per_meter` — NULLABLE, fallback zajisten
- Migrace: 2026-01-26 (uz existuje)

---

## Related ADRs

- ADR-011: Material Hierarchy (Two-Tier Model)
- ADR-014: Material Price Tiers
- ADR-015: Material Norm Mapping (W.Nr → MaterialGroup)
- ADR-017: 7-Digit Random Entity Numbering
