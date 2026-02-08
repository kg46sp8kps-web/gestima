# GESTIMA - Data Integrity Audit

**Datum:** 2026-02-03
**Verze aplikace:** 1.3.x
**Auditor:** Claude Opus 4.5
**Typ:** Data Integrity (Defense in Depth)

---

## Executive Summary

| Metrika | Hodnota |
|---------|---------|
| **Celkove skore Data Integrity** | 56/100 |
| **Kriticke problemy (P0)** | 18 |
| **Vysoka priorita (P1)** | 12 |
| **Stredni priorita (P2)** | 15 |
| **Nizka priorita (P3)** | 8 |
| **Celkem issues** | 53 |

### Pokryti podle vrstev

| Vrstva | Pokryti | Kriticke mezery |
|--------|---------|-----------------|
| LAYER 1: DB Constraints | 65% | Chybi ondelete, partial unique, CHECK |
| LAYER 2: Pydantic Validation | 60% | Chybi pattern regex, @model_validator |
| LAYER 3: Service Guards | 50% | Chybi can_delete(), cascade soft delete |
| LAYER 4: Transaction Safety | 75% | Raw db.commit() na 2 mistech |
| LAYER 5: Integration Tests | 45% | MaterialInput bez testu, FK testy chybi |

**Verdikt:** Projekt ma solidni zaklad, ale kriticke mezery v kazde vrstve. Bez oprav P0 hrozi data corruption a orphaned records.

---

## Metodologie auditu

Audit pouzil "Defense in Depth" model s 5 vrstvami ochrany:

```
User Input → [L2: Pydantic] → [L3: Service Guards] → [L4: Transaction] → [L1: DB]
                  ↓ FAIL            ↓ FAIL              ↓ FAIL           ↓ FAIL
              ValidationError   HTTPException        Rollback      IntegrityError

[L5: Tests] bezi pred deploymentem a overuje vsechny ostatni vrstvy
```

Kazda vrstva byla auditovana samostatnym agentem pro hloubkovou analyzu.

---

## P0 - KRITICKE PROBLEMY (Blokujici produkci)

### P0-001: Chybejici ondelete na FK constraints

**Zavaznost:** KRITICKA
**Vrstva:** L1 - Database Constraints
**Dopad:** FK violation pri mazani parent entity

**Postizene modely:**
| Model | FK Column | Chybi |
|-------|-----------|-------|
| Batch | frozen_by_id | `ondelete="SET NULL"` |
| BatchSet | frozen_by_id | `ondelete="SET NULL"` |
| MaterialItem | material_group_id | `ondelete="RESTRICT"` |
| MaterialItem | price_category_id | `ondelete="RESTRICT"` |
| MaterialPriceCategory | material_group_id | `ondelete="SET NULL"` |
| MaterialPriceTier | price_category_id | `ondelete="CASCADE"` |
| ModuleLayout | user_id | `ondelete="CASCADE"` |

**Oprava:** Alembic migrace pro pridani ondelete

---

### P0-002: Chybi partial unique index pro soft delete

**Zavaznost:** KRITICKA
**Vrstva:** L1 - Database Constraints
**Dopad:** Nelze vytvorit zaznam se stejnym cislem po soft delete

**Problem:**
```python
# Aktualni: Unique plati i pro smazane zaznamy
part_number = Column(String(8), unique=True)

# Po soft delete part_number='10000001' nelze vytvorit novy se stejnym cislem!
```

**Postizene sloupce:**
- parts.part_number, parts.article_number
- quotes.quote_number
- partners.partner_number
- batches.batch_number
- batch_sets.set_number
- material_items.material_number, material_items.code

**Oprava:**
```sql
DROP INDEX IF EXISTS ix_parts_part_number;
CREATE UNIQUE INDEX ix_parts_part_number_active
ON parts(part_number) WHERE deleted_at IS NULL;
```

---

### P0-003: Chybi CHECK constraints pro enum a kladne hodnoty

**Zavaznost:** KRITICKA
**Vrstva:** L1 - Database Constraints
**Dopad:** Moznost ulozit neplatny status nebo zaporne mnozstvi primo do DB

**Chybejici CHECK pro enum:**
- parts.status - IN ('draft', 'active', 'archived')
- quotes.status - IN ('draft', 'sent', 'approved', 'rejected')
- batch_sets.status - IN ('draft', 'frozen')

**Chybejici CHECK pro quantity > 0:**
- batches.quantity
- quote_items.quantity
- material_inputs.quantity

**Oprava:**
```python
__table_args__ = (
    CheckConstraint("status IN ('draft', 'active', 'archived')", name='ck_parts_status'),
    CheckConstraint('quantity > 0', name='ck_batches_quantity_positive'),
)
```

---

### P0-004: Konflikt nullable=False + ondelete=SET NULL

**Zavaznost:** KRITICKA
**Vrstva:** L1 - Database Constraints
**Soubor:** `app/models/material_input.py`

**Problem:**
```python
price_category_id = Column(
    Integer,
    ForeignKey("material_price_categories.id", ondelete="SET NULL"),
    nullable=False  # KONFLIKT! SET NULL selze na NOT NULL constraint
)
```

**Dopad:** IntegrityError pri mazani MaterialPriceCategory

**Oprava:** Zmenit na `ondelete="RESTRICT"` nebo `nullable=True`

---

### P0-005: Chybi pattern regex pro entity numbers

**Zavaznost:** KRITICKA
**Vrstva:** L2 - Pydantic Validation
**Dopad:** Moznost vytvorit entitu s neplatnym formatem cisla

**Postizena pole (pouze min/max_length, chybi pattern):**
| Pole | Aktualni | Melo by byt |
|------|----------|-------------|
| part_number | `min_length=8, max_length=8` | `pattern=r"^10\d{6}$"` |
| batch_number | `min_length=8, max_length=8` | `pattern=r"^30\d{6}$"` |
| quote_number | `min_length=8, max_length=8` | `pattern=r"^50\d{6}$"` |
| partner_number | `min_length=8, max_length=8` | `pattern=r"^70\d{6}$"` |
| material_number | `min_length=8, max_length=8` | `pattern=r"^20\d{6}$"` |
| set_number | `min_length=8, max_length=8` | `pattern=r"^35\d{6}$"` |

---

### P0-006: Chybi @model_validator pro cross-field validace

**Zavaznost:** KRITICKA
**Vrstva:** L2 - Pydantic Validation
**Dopad:** Neplatne kombinace poli projdou validaci

**Chybejici validatory:**
| Schema | Validace | Problem |
|--------|----------|---------|
| MaterialPriceTierBase | min_weight < max_weight | Moznost vytvorit tier s min > max |
| MaterialInputBase | dimensions by shape | ROUND_BAR bez stock_diameter projde |
| QuoteFromRequestCreate | partner_id XOR partner_data | Moznost zadat obe nebo zadne |

---

### P0-007: Partner delete bez kontroly zavislosti

**Zavaznost:** KRITICKA
**Vrstva:** L3 - Service Guards
**Soubor:** `app/routers/partners_router.py`
**Dopad:** Partner s aktivnimi Quote lze smazat, Quote osiri

**Chybejici kontrola:**
```python
# CHYBI v delete endpoint:
active_quotes = await db.execute(
    select(Quote).where(
        Quote.partner_id == partner.id,
        Quote.status.in_([QuoteStatus.DRAFT.value, QuoteStatus.SENT.value]),
        Quote.deleted_at.is_(None)
    )
)
if active_quotes.scalars().first():
    raise HTTPException(409, "Nelze smazat - partner ma aktivni nabidky")
```

---

### P0-008: Quote soft delete nekaskaduje na QuoteItems

**Zavaznost:** KRITICKA
**Vrstva:** L3 - Service Guards
**Soubor:** `app/routers/quotes_router.py`
**Dopad:** Orphaned QuoteItems po soft delete Quote

**Chybejici kaskada:**
```python
# Pri soft delete Quote CHYBI:
for item in quote.items:
    item.deleted_at = datetime.utcnow()
    item.deleted_by = username
```

---

### P0-009: Raw db.commit() bez error handling

**Zavaznost:** KRITICKA
**Vrstva:** L4 - Transaction Safety
**Dopad:** Unhandled exceptions, session corruption

**Postizena mista:**
| Soubor | Radky | Operace |
|--------|-------|---------|
| material_inputs_router.py | 193, 258, 327, 399, 428 | create, update, delete, link, unlink |
| operations_router.py | 218, 248 | link material, unlink material |

**Oprava:** Nahradit za `safe_commit(db, entity, "operation description")`

---

### P0-010: MaterialInput - zadne testy

**Zavaznost:** KRITICKA
**Vrstva:** L5 - Integration Tests
**Dopad:** Core feature bez pokryti, mozne regrese

**Chybejici testy:**
- Create MaterialInput with valid/invalid Part
- Update MaterialInput recalculates costs
- Delete MaterialInput recalculates costs
- Soft delete cascade from Part

---

### P0-011: Part cascade delete testy CHYBI

**Zavaznost:** KRITICKA
**Vrstva:** L5 - Integration Tests
**Dopad:** Neoverene CASCADE chovani

**Chybejici testy:**
- Delete Part → verify Operations deleted (CASCADE)
- Delete Part → verify Features deleted (CASCADE)
- Delete Part → verify MaterialInputs deleted (CASCADE)
- Delete Part → verify Batches orphaned/blocked

---

### P0-012 az P0-018: Dalsi kriticke problemy

| ID | Problem | Vrstva |
|----|---------|--------|
| P0-012 | ICO/DIC validatory spatne propojene v PartnerBase | L2 |
| P0-013 | Part status ARCHIVED neni enforceovan (read-only) | L3 |
| P0-014 | Chybejici version check v module_layouts_router.py | L4 |
| P0-015 | Chybejici version check v module_defaults_router.py | L4 |
| P0-016 | Quote FK constraint testy CHYBI | L5 |
| P0-017 | Delete-in-use entity testy CHYBI | L5 |
| P0-018 | MaterialGroup CASCADE delete muze smazat 500+ items | L1 |

---

## P1 - VYSOKA PRIORITA (Tento sprint)

| ID | Problem | Vrstva | Soubor |
|----|---------|--------|--------|
| P1-001 | Chybejici back_populates na 5 vztazich | L1 | models/*.py |
| P1-002 | Chybejici indexy na 8 FK sloupcich | L1 | models/*.py |
| P1-003 | Quote.status jako str misto QuoteStatus enum | L2 | quote.py |
| P1-004 | Chybejici BatchSetStatus enum | L2 | batch_set.py |
| P1-005 | WorkCenter delete guard (pouzivan v Operations) | L3 | work_centers_router.py |
| P1-006 | MaterialPriceCategory delete guard | L3 | admin_router.py |
| P1-007 | Chybejici savepoints pro dlouhe importy | L4 | materials_router.py |
| P1-008 | Nekonsistentni audit trail (set_audit vs manual) | L4 | 25 mist |
| P1-009 | Operation/Feature CRUD testy CHYBI | L5 | tests/ |
| P1-010 | MaterialNorm CRUD testy CHYBI | L5 | tests/ |
| P1-011 | CuttingCondition testy CHYBI | L5 | tests/ |
| P1-012 | Part.name je nullable=True (melo by byt False?) | L1 | part.py |

---

## P2 - STREDNI PRIORITA (Pristi sprint)

| ID | Problem | Vrstva |
|----|---------|--------|
| P2-001 | Postal code bez pattern validace | L2 |
| P2-002 | Phone bez pattern validace | L2 |
| P2-003 | Email bez EmailStr validace | L2 |
| P2-004 | notes max_length nekonzistentni (500 vs 1000) | L2 |
| P2-005 | Batch.total_cost invariant neni validovan | L3 |
| P2-006 | BatchSet invariant (same part) neni enforceovan | L3 |
| P2-007 | Retry logic pro deadlocks CHYBI | L4 |
| P2-008 | Chybejici 404 testy pro Part, Quote, Operation | L5 |
| P2-009 | Chybejici 409 testy pro Quote version conflict | L5 |
| P2-010 | ModuleLayout testy CHYBI | L5 |
| P2-011 | ModuleDefaults testy CHYBI | L5 |
| P2-012 | Soft delete recovery testy CHYBI | L5 |
| P2-013 | Race condition testy (concurrent QuoteItem add) | L5 |
| P2-014 | Factory fixtures pro Part, Quote, Batch CHYBI | L5 |
| P2-015 | Drawings version nema incoming check | L4 |

---

## P3 - NIZKA PRIORITA (Backlog)

| ID | Problem | Vrstva |
|----|---------|--------|
| P3-001 | Duplikovany IntegrityError handling | L4 |
| P3-002 | Test fixtures nejsou znovupouzitelne | L5 |
| P3-003 | Test data hardcoded misto centralizovanych fixtures | L5 |
| P3-004 | Chybejici gt=0 pro nektere ID fieldy | L2 |
| P3-005 | Distributed transaction support (pro budouci scaling) | L4 |
| P3-006 | Property-based testing (hypothesis) | L5 |
| P3-007 | Chaos testing | L5 |
| P3-008 | Trigery pro komplexni validace (future) | L1 |

---

## Co je DOBRE

### L1 - Database Constraints
- Vsechny *_number a CODE sloupce maji unique=True
- Vetsina FK ma spravne definovane ondelete
- AuditMixin poskytuje deleted_at s index=True
- Optimistic locking (version column) na vsech modelech

### L2 - Pydantic Validation
- Field(gt=0) pro quantity, price, weight
- Field(max_length) na stringech
- ConfigDict(from_attributes=True) pro ORM
- version: int pro optimistic locking

### L3 - Service Guards
- Quote SENT/APPROVED nelze editovat (check_edit_lock)
- Batch is_frozen guards funguji
- State transitions pro Quote workflow

### L4 - Transaction Safety
- safe_commit() pattern ve vetsine routeru (70+ pouziti)
- Optimistic locking via AuditMixin.version
- Session management pres dependency injection

### L5 - Integration Tests
- Auth/Authorization dobre pokryto (16+ testu)
- Optimistic locking testy (10+ testu)
- Number generator testy (15+ testu)
- Quote workflow testy (15+ testu)

---

## Akcni plan

### Tyden 1: P0 opravy (KRITICKE)

| Den | Ukol | Soubory |
|-----|------|---------|
| Po | P0-001, P0-002: Alembic migrace pro ondelete + partial unique | alembic/ |
| Ut | P0-003, P0-004: CHECK constraints + fix nullable konflikt | alembic/, models/ |
| St | P0-005, P0-006: Pattern regex + @model_validator | schemas/ |
| Ct | P0-007, P0-008, P0-013: Service guards (partner, quote cascade, part status) | routers/ |
| Pa | P0-009, P0-014, P0-015: Transaction safety (safe_commit, version checks) | routers/ |

### Tyden 2: P0 testy + P1

| Den | Ukol |
|-----|------|
| Po-Ut | P0-010, P0-011, P0-016, P0-017: Kriticke testy |
| St-Ct | P1-001 az P1-006: DB fixes + service guards |
| Pa | P1-007 az P1-011: Savepoints + dalsi testy |

### Tyden 3: P2

| Ukol |
|------|
| Pydantic validace (postal, phone, email) |
| Dalsi invariant checks |
| Retry logic |
| Zbyle testy |

---

## Zaver

Data Integrity audit odhalil **18 kritickych problemu** rozlozenych pres vsech 5 vrstev ochrany. Nejzavaznejsi jsou:

1. **Chybejici DB constraints** - ondelete, partial unique, CHECK
2. **Nedostatecna Pydantic validace** - pattern regex, cross-field validators
3. **Chybejici service guards** - partner delete, quote cascade
4. **Transaction safety mezery** - raw commits bez error handling
5. **Kriticke mezery v testech** - MaterialInput, Part cascade, FK constraints

**Doporuceni:** Opravit P0 pred jakymkoliv production deploymentem. Odhadovany cas: 2 tydny.

**Pozitivni:** Projekt ma solidni zaklad (safe_commit, optimistic locking, audit trail) - potrebuje doplnit chybejici casti.

---

**Souvisejici dokumenty:**
- [DATA_INTEGRITY_MAP.md](../../DATA_INTEGRITY_MAP.md) - Pracovni dokument s ERD a edge cases
- [ADR-008](../ADR/008-optimistic-locking.md) - Optimistic Locking
- [RULES.md](../core/RULES.md) - Blocking rules

---

*Audit proveden s vyuzitim 5 paralelnich agentu (Opus model) pro hloubkovou analyzu kazde vrstvy.*
