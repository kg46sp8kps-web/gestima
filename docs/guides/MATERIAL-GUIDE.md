# Material System — Reference

**ADRs:** ADR-011 (hierarchy), ADR-014 (price tiers), ADR-015 (norm mapping), ADR-016 (parser), ADR-019 (smart lookup)

---

## Hierarchy

```
MaterialNorm          W.Nr/EN/CSN/AISI → MaterialGroup
MaterialGroup         9 skupin, 8-digit kód 20910000–20910008
MaterialItem          konkrétní polotovar (shape, rozměry, cena)
MaterialPriceCategory cenové tabulky, 43 kategorií, 8-digit kód 20900000–20900042
```

**Seed pořadí:** MaterialGroups → PriceCategories (FK závisí) → MaterialNorms → MaterialItems

---

## MaterialNorm — parser pravidla

- Lookup přes W.Nr, EN, CSN nebo AISI (OR logika, case-insensitive)
- Min. 1 sloupec musí být vyplněn
- Chybějící norma = ERROR (import blokován, ne tichý fallback)
- Admin konzole: `/admin/material-norms` (admin only, optimistic locking)

---

## MaterialItem — shape enum

| Enum | Infor code |
|------|-----------|
| `ROUND_BAR` | KR |
| `FLAT_BAR` | HR (různé rozměry) |
| `SQUARE_BAR` | HR (stejné rozměry) |
| `HEXAGONAL_BAR` | OK |
| `TUBE` | TR |
| `PLATE` | DE |
| `BLOCK` | — |

HR disambiguation: `005x005` → SQUARE_BAR, `008x004` → FLAT_BAR

---

## Smart Lookup (ADR-019)

Lookup **upward only** — materiál musí být >= požadovaný rozměr:

```
Zadáno: D21 → Nalezeno: D25 (větší o 4mm) ✓
Zadáno: D21 → D20 NENALEZENO (menší = nelze použít) ✗
```

Postup: parse(text) → MaterialGroup (via MaterialNorm) → filter items kde dim >= požadovaný → vyber nejbližší

---

## PriceCategory matching

Matching přes `shape` sloupec — NE keyword matching. Chybějící PriceCategory = ERROR (import blokován).

---

## Seed scripts (canonical)

| Script | Co seeduje |
|--------|-----------|
| `scripts/seed_material_groups.py` | 9 skupin (CANONICAL) |
| `scripts/seed_price_categories.py` | 43 kategorií se shape (CANONICAL) |
| `scripts/seed_material_norms_complete.py` | 82 norem |
| `scripts/seed_material_items.py` | materiály |

Seed pravidla: UPSERT (nikdy DELETE ALL + INSERT), inline data, idempotentní.

---

## API

```
GET  /api/material-groups
GET  /api/material-norms/search?q=
POST /api/material-norms
PUT  /api/material-norms/{id}
GET  /api/materials/items
GET  /api/materials/parse?text=
```

**Kód:** `app/models/material.py`, `app/services/material_mapping.py`
