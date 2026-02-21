# ADR-015: Material Norm Auto-Mapping

**Status:** Implemented (2026-01-26, v1.5.0)

## Context

Uživatel má 4000-5000 polotovarů s různými označeními (1.4301, X5CrNi18-10, AISI 304 — všechno nerez). Manuální přiřazení `material_group_id` pro každou položku je neefektivní. Potřebujeme auto-přiřazení z normy materiálu.

## Decision

**MaterialNorm conversion table** — DB tabulka se 4 sloupci (W.Nr | EN ISO | ČSN | AISI) mapuje normy na `MaterialGroup`. Service hledá case-insensitive napříč všemi 4 sloupci.

## Key Files / Models

- `app/models/material_norm.py` — `MaterialNorm` model (4 sloupce + `material_group_id` FK)
- `app/services/material_mapping.py` — `auto_assign_group()`, `auto_assign_categories()`
- `app/routers/admin_router.py` — CRUD API + Admin UI `/admin/material-norms`
- `scripts/seed_material_norms_complete.py` — 82 norem (UPSERT, idempotentní)

## DB Schema

```sql
CREATE TABLE material_norms (
    id                INTEGER PRIMARY KEY,
    w_nr              VARCHAR(50),    -- "1.4301", "1.0503"
    en_iso            VARCHAR(50),    -- "X5CrNi18-10", "C45"
    csn               VARCHAR(50),    -- "17240", "12050"
    aisi              VARCHAR(50),    -- "304", "1045"
    material_group_id INTEGER NOT NULL REFERENCES material_groups(id),
    note              TEXT
    -- + AuditMixin fields
);
-- Indexy na všechny 4 sloupce
```

## Service API

```python
async def auto_assign_group(db, norm_code: str) -> MaterialGroup:
    """Case-insensitive search napříč W.Nr | EN ISO | ČSN | AISI."""
    # WHERE upper(w_nr)=X OR upper(en_iso)=X OR upper(csn)=X OR upper(aisi)=X
    # Raises ValueError pokud norma není v DB

async def auto_assign_categories(db, norm_code: str, shape: StockShape
) -> tuple[MaterialGroup, MaterialPriceCategory]:
    """Auto-assign group + price category z (norma, tvar)."""
```

## Seed Coverage (82 norem)

Ocel konstrukční (S235, C45, 11xxx) | Ocel legovaná (42CrMo4, 16MnCr5) |
Nerez (304, 304L, 316, 316L) | Hliník (6060, 7075) |
Mosaz (CuZn37, CuZn39Pb3) | Plasty (PA6, POM)

## Seed Dependency Order

```
1. MaterialGroup  (seed_material_groups.py)
2. MaterialPriceCategory  (seed_price_categories.py)
3. MaterialNorm  (seed_material_norms_complete.py)
```

## Consequences

- Auto-přiřazení group + price category při vytvoření `MaterialItem`
- 1.4301 = X5CrNi18-10 = AISI 304 — všechny aliasy vedou na stejnou skupinu
- Editovatelné přes Admin UI bez redeploy
- JOIN pouze při CREATE, ne při LIST/READ — žádný performance dopad na denní queries
- Admin UI tab `/admin/material-norms` (live client-side filtering)

## Known Issues (opraveno 2026-01-26)

- Alpine.js nested components: komunikace přes `window.dispatchEvent` (ne `$refs`)
- Empty string vs null: frontend musí konvertovat `""` → `null` pro volitelná pole
- JSON serialization: ORM objekty převést na dicts před předáním do Jinja2 template

## References

- ADR-011: Material Hierarchy (Two-Tier System)
- ADR-014: Material Price Tiers
