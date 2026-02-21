# ADR-017: 8-Digit Entity Numbering System

**Status:** Accepted (v2.0, 2026-01-28)

## Context

Auto-increment INT id není vhodný jako user-facing identifikátor (předvídatelný, nečitelný v reportech). Původní 7-digit systém (v1.0) umožňoval jen 10 prefixů — nedostatečné pro 15+ plánovaných typů entit.

## Decision

**8-digit numbering** s 2-digit prefixem: `[PP][XXXXXX]` — 100 prefixů, 1M kapacita na prefix.

## Format

```
PP = 2-digit prefix (10-99)   — doména entity
XXXXXX = 6 číslic (random nebo sequential)
Total = 8 digits, vždy fixed length
```

## Prefix Allocation

| Prefix | Entita | Generování | Status |
|--------|--------|------------|--------|
| 10 | Parts | Random | Implementováno |
| 20 | Materials (sub-ranges) | Random/Sequential | Implementováno |
| 30 | Batches | Random | Implementováno |
| 40 | Orders | Random | Rezervováno |
| 50 | Quotes | Random | Rezervováno |
| 70 | Customers | Random | Rezervováno |
| 80 | WorkCenters | **Sequential** | Implementováno |
| 90 | Drawings/Docs | Random | Rezervováno |

## Materials Sub-Ranges (prefix 20)

```
20_000_001 – 20_899_999   MaterialItem          [900k]
20_900_000 – 20_909_999   MaterialPriceCategory [ 10k]
20_910_000 – 20_919_999   MaterialGroup         [ 10k]
20_920_000 – 20_929_999   MaterialNorm          [ 10k]
```

## Key Files

- `app/services/number_generator.py` — `NumberGenerator` class, všechny `generate_*` metody
- `app/schemas/*.py` — `Field(min_length=8, max_length=8)` na číselná pole
- `alembic/versions/xxx_8digit_numbering.py` — migrace 7→8 digits (prepend "1"/"2"/"3")

## Number Generator Pattern

```python
# Random (Parts, Materials, Batches)
await _generate_random_number(db, Model, 'field', MIN, MAX)

# Sequential (WorkCenters)
max_num = await db.execute(select(func.max(WorkCenter.work_center_number)))
return str(int(max_num or WORK_CENTER_MIN - 1) + 1)
```

## Migration (7 → 8 digits)

```sql
UPDATE parts SET part_number = '1' || part_number WHERE length(part_number) = 7;
UPDATE material_items SET material_number = '2' || material_number WHERE length(material_number) = 7;
UPDATE batches SET batch_number = '3' || batch_number WHERE length(batch_number) = 7;
```

## Consequences

- Fixed 8-digit formát: konzistentní zobrazení v tabulkách a výrobních příkazech
- 100 prefixů pokryje plánovaných 15+ typů entit s velkou rezervou
- Collision rate 0.45% pro 3000 položek (birthday paradox) — stejné jako v1.0
- WorkCenters jsou sequential (operátoři si pamatují "stroj 80000003")
- Breaking change z v1.0: alembic migrace provedena v1.6.0

## References

- Industry standard: SAP (8-digit), Oracle (8-15 digit), Infor (7-12 digit)
