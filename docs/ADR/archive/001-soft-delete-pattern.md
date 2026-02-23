# ADR-001: Soft Delete Pattern

## Status
Přijato (22.1.2026)

## Kontext

Pro ERP systém je kritické zachovat historii záznamů:
- Položky se nesmí fyzicky mazat (vazby v nabídkách, zakázkách)
- Potřeba audit trail pro compliance
- Budoucí moduly: poptávky, výroba, sklady vyžadují referenční integritu

## Rozhodnutí

**Soft Delete Pattern** - záznamy se označí jako smazané, ale fyzicky zůstávají v databázi.

### Implementace:
```python
class AuditMixin:
    deleted_at = Column(DateTime, nullable=True)  # NULL = aktivní
    deleted_by = Column(String(100), nullable=True)
```

### Použití:
- `deleted_at IS NULL` = aktivní záznamy
- `deleted_at IS NOT NULL` = smazané záznamy

## Alternativy

1. **Hard Delete** - fyzické mazání
   - ❌ Ztráta dat
   - ❌ Rozbitá reference v nabídkách

2. **Archive Table** - samostatná tabulka pro smazané
   - ❌ Složitější queries
   - ❌ Duplikace struktury

## Důsledky

### Pozitivní
- ✅ Zachování historických dat
- ✅ Možnost restore
- ✅ Audit trail
- ✅ Referenční integrita

### Negativní
- ⚠️ Větší databáze (~5% růst)
- ⚠️ Queries musí filtrovat `deleted_at IS NULL`

### Dopad na budoucí moduly
- **Poptávkový modul:** Nabídky vidí i smazané díly
- **Výroba:** Zakázky trackovatelné i po "smazání" dílu
- **Sklady:** Transakce zachovány
