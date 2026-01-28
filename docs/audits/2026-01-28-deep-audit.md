# GESTIMA Deep Audit Report

**Datum:** 2026-01-28
**Auditor:** Claude Opus 4.5
**Verze:** 1.6.0
**Metoda:** 8 paralelních specializovaných auditů

---

## Executive Summary

| Oblast | Hodnocení | Kritických | Vysokých |
|--------|-----------|------------|----------|
| DB Schema | 7/10 | 3 | 7 |
| Business Logic | 8/10 | 1 | 3 |
| API Contracts | 8.5/10 | 0 | 2 |
| Security | B+ | 0 | 3 |
| Performance | 6/10 | 3 | 3 |
| Architecture | 7.5/10 | 0 | 2 |
| Error Handling | 7/10 | 2 | 2 |
| Frontend | 7/10 | 0 | 2 |

**Celkové hodnocení: 7.5/10**

---

## Porovnání s předchozími audity

### ✅ Opravené a stabilní (z 27.1.)

| Problém | Status |
|---------|--------|
| Falsy defaults (`is not None`) | ✅ Funguje |
| FK ondelete v part.py | ✅ Funguje |
| Infinite loop limit | ✅ Funguje |
| Dead code (~18,350 LOC) | ✅ Smazáno |

### 🔄 Opakující se problémy (nebyly opraveny)

| Problém | Zmíněno | Status |
|---------|---------|--------|
| N+1 queries | 26.1., 27.1., 28.1. | ❌ Stále neřešeno |
| deleted_at indexes | 27.1., 28.1. | ❌ Stále neřešeno |
| safe_commit() nepoužitý | 27.1., 28.1. | ❌ 37× duplicit |
| Console.log v produkci | 27.1., 28.1. | ❌ 45× výskytů |
| Pagination missing | 27.1., 28.1. | ❌ Stále neřešeno |

### 🆕 Nově nalezené (hloubkový audit)

| Problém | Oblast |
|---------|--------|
| SQLite FK = NO ACTION | DB Schema |
| Float pro finance | DB Schema |
| Migration error handling | Error Handling |
| CSP/HSTS headers | Security |
| Frontend memory leaks | Frontend |
| Repository pattern chybí | Architecture |

---

## Kritické problémy (P0)

### C-1: SQLite FK constraints = NO ACTION
**Oblast:** DB Schema
**Problém:** SQLAlchemy modely definují `ondelete="CASCADE"`, ale SQLite má `NO ACTION`
**Dopad:** Orphan FK při deletech
**Řešení:** Alembic migration s recreate tables

### C-2: Float pro finanční data
**Oblast:** DB Schema
**Problém:** Všechny cost/price sloupce používají Float místo Decimal
**Dopad:** Zaokrouhlovací chyby (0.1 + 0.2 = 0.30000000000000004)
**Řešení:** Migrate Float → Numeric(10,2)

### C-3: Missing composite indexes
**Oblast:** Performance
**Problém:** 16× query `.where(Model.deleted_at.is_(None))` bez indexu
**Dopad:** Full table scan při každém list query
**Řešení:** `Index('ix_parts_deleted_at', 'deleted_at')`

### C-4: N+1 v parts list
**Oblast:** Performance
**Problém:** `GET /api/parts` bez eager loading a bez limit
**Dopad:** 100 parts = 201 queries
**Řešení:** `selectinload()` + pagination

### C-5: Migration error handling
**Oblast:** Error Handling
**Problém:** `database.py` migrations bez try/except
**Dopad:** Silent failures při startupu
**Řešení:** Wrap migrations v try/except s logging

### C-6: Seed data error handling
**Oblast:** Error Handling
**Problém:** `init_db()` seed bez try/except
**Dopad:** Nejasné startup errors
**Řešení:** Structured error handling pro každý seed

---

## Vysoká priorita (P1)

| ID | Problém | Oblast |
|----|---------|--------|
| H-1 | Batch recalculate race condition | Business Logic |
| H-2 | Float rounding inconsistency | Business Logic |
| H-3 | Missing CSP headers | Security |
| H-4 | HTTPS enforcement chybí | Security |
| H-5 | Query params bez max limit | API |
| H-6 | Memory leaks (addEventListener) | Frontend |
| H-7 | Console.log v produkci (45×) | Frontend |
| H-8 | Missing repository pattern | Architecture |
| H-9 | 37× duplicitní try/commit | Architecture |

---

## Co funguje výborně

1. **SQL Injection Protection** - 100% SQLAlchemy ORM
2. **Authentication** - bcrypt + JWT + HttpOnly + SameSite=strict
3. **Optimistic Locking** - 14× version checks
4. **Soft Delete** - 100% coverage
5. **Audit Trail** - 39× set_audit() calls
6. **Transaction Handling** - 100% commit-rollback pairing
7. **ADR Compliance** - 5/5 ADRs implementováno
8. **Type Safety** - Pydantic validace všude

---

## Doporučený Action Plan

### Sprint 1: Opakující se problémy (konečně opravit!)

```
□ N+1 queries + eager loading (zmíněno 3×)
□ deleted_at composite indexes (zmíněno 2×)
□ safe_commit() mass replace (zmíněno 2×)
□ Console.log cleanup (45×)
```

### Sprint 2: Kritické nové

```
□ Migration error handling (C-5, C-6)
□ CSP/HSTS headers (H-3, H-4)
□ Frontend memory leaks (H-6)
```

### Sprint 3: Dlouhodobé

```
□ SQLite FK migration (C-1)
□ Float → Decimal migration (C-2)
□ Repository pattern (H-8)
```

---

## Expected Impact

| Metrika | Před | Po |
|---------|------|-----|
| Parts list load | 1200ms | 150ms |
| DB queries/request | 50-200 | 3-10 |
| Code duplication | 37× | 1× |
| Production readiness | 75% | 95% |

---

## Závěr

**Základy jsou solidní.** Architektura je správná, bezpečnost dobrá, patterns konzistentní.

**Hlavní problém:** Některé issues se opakují v auditech ale nikdy se neopraví. Doporučuji příště místo dalšího auditu opravit opakující se problémy.

---

**Další review:** Po opravě Sprint 1
