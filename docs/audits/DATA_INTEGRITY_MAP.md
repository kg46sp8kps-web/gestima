# DATA INTEGRITY MAP - GESTIMA

**Účel:** Kompletní přehled datové integrity, vazeb a kontrolních mechanismů.
**Verze:** 1.0 (2026-02-03)

---

## 0. DEFENSE IN DEPTH - 5 VRSTEV OCHRANY

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: DATABASE CONSTRAINTS                                               │
│ Poslední obranná linie - databáze VŽDY odmítne neplatná data               │
├─────────────────────────────────────────────────────────────────────────────┤
│ ✅ MÁME:                          │ ❌ CHYBÍ:                               │
│ • FK constraints (všechny modely) │ • Partial unique indexes (soft delete) │
│ • Unique constraints (codes/nums) │ • CHECK constraints (status values)    │
│ • NOT NULL na povinných polích    │ • Trigery pro komplexní validace       │
│ • ON DELETE akce definovány       │ • Composite unique (module+user)       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: PYDANTIC VALIDATION                                                │
│ Vstupní brána - validace dat PŘED uložením do DB                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ ✅ MÁME:                          │ ❌ CHYBÍ:                               │
│ • Field(gt=0) pro kladná čísla    │ • Regex pro part_number format         │
│ • max_length na stringech         │ • Cross-field validace (from < to)     │
│ • Enum validace pro statusy       │ • Business rule validators             │
│ • Optional vs required fields     │ • Custom validators pro finance        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: SERVICE LAYER GUARDS                                               │
│ Business logika - kontrola PŘED provedením akce                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ ✅ MÁME:                          │ ❌ CHYBÍ:                               │
│ • Quote status check (SENT/APPR)  │ • can_delete(entity) → bool + reason   │
│ • Batch is_frozen check           │ • can_modify(entity) → bool + reason   │
│ • require_role() decorator        │ • validate_state_transition(from, to)  │
│ • safe_commit() wrapper           │ • pre_delete_check() hooks             │
│                                   │ • invariant_check() po každé operaci   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: TRANSACTION SAFETY                                                 │
│ Atomicita - buď vše nebo nic                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ ✅ MÁME:                          │ ❌ CHYBÍ:                               │
│ • Optimistic locking (version)    │ • Explicitní BEGIN/COMMIT bloky        │
│ • safe_commit() s rollback        │ • Savepoints pro částečné rollback     │
│ • Audit trail (who, when)         │ • Distributed transaction support      │
│ • SQLAlchemy session management   │ • Retry logic pro deadlocks            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: INTEGRATION TESTS                                                  │
│ Důkaz správnosti - testy které dokazují že systém funguje                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ ✅ MÁME:                          │ ❌ CHYBÍ:                               │
│ • Unit testy pro services         │ • Edge case test suite                 │
│ • API endpoint testy              │ • Chaos testing (random operations)    │
│ • pytest fixtures                 │ • Property-based testing (hypothesis)  │
│                                   │ • Invariant verification testy         │
│                                   │ • Referential integrity testy          │
│                                   │ • Reconciliation testy                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Jak vrstvy spolupracují

```
User Input → [LAYER 2: Pydantic] → [LAYER 3: Service Guards] → [LAYER 4: Transaction] → [LAYER 1: DB]
                  ↓ FAIL                    ↓ FAIL                   ↓ FAIL              ↓ FAIL
              ValidationError           HTTPException             Rollback          IntegrityError

[LAYER 5: Tests] běží před deploymentem a ověřuje všechny ostatní vrstvy
```

### Coverage Score (aktuální stav)

| Vrstva | Pokrytí | Kritické mezery |
|--------|---------|-----------------|
| LAYER 1: DB Constraints | 70% | Partial unique indexes, CHECK constraints |
| LAYER 2: Pydantic | 60% | Cross-field validace, business validators |
| LAYER 3: Service Guards | 40% | can_delete, can_modify, state transitions |
| LAYER 4: Transaction | 80% | Explicitní transakce, retry logic |
| LAYER 5: Tests | 30% | Edge cases, chaos, invariant verification |

**Celkové pokrytí: ~65%** - Po opravách z 2026-02-03.

### Opravy provedené 2026-02-03

| Komponenta | Změna |
|------------|-------|
| `price_calculator.py` | Filtruje deleted operations a material_inputs |
| `batch_service.py` | Filtruje deleted material_inputs |
| `snapshot_service.py` | Filtruje deleted material_inputs |
| `quote_service.py` | Invariant checks (subtotal == sum items) |
| `parts_router.py` | Soft delete s kaskádou na children |
| `partners_router.py` | Soft delete |
| `operations.ts` | Auto-reload při 409 conflict |
| `parts.ts` | Auto-reload při 409 conflict |

---

## 1. ERD - ENTITY RELATIONSHIP DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    MASTER DATA                                          │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  ┌──────────────┐         ┌────────────────────┐         ┌─────────────────┐           │
│  │ MaterialGroup│◄────────│MaterialPriceCategory│────────►│MaterialPriceTier│           │
│  │──────────────│ 1     N │────────────────────│ 1     N │─────────────────│           │
│  │ code (UQ)    │         │ code (UQ)          │         │ min_weight      │           │
│  │ name         │         │ material_group_id  │         │ max_weight      │           │
│  │ shape        │         │                    │         │ price_per_kg    │           │
│  └──────┬───────┘         └─────────┬──────────┘         └─────────────────┘           │
│         │                           │                                                   │
│         │ 1                         │ N                                                 │
│         ▼ N                         ▼ 1                                                 │
│  ┌──────────────┐         ┌────────────────────┐                                       │
│  │ MaterialItem │◄────────│                    │         ┌─────────────────┐           │
│  │──────────────│         │                    │         │   WorkCenter    │           │
│  │ material_num │         │                    │         │─────────────────│           │
│  │ (UQ)         │         │                    │         │ work_center_num │           │
│  │ code         │         │                    │         │ (UQ)            │           │
│  │ name         │         │                    │         │ hourly_rate     │           │
│  └──────────────┘         │                    │         └────────┬────────┘           │
│                           │                    │                  │                     │
│  ┌──────────────┐         │                    │                  │                     │
│  │ MaterialNorm │         │                    │                  │                     │
│  │──────────────│         │                    │                  │                     │
│  │ w_nr         │         │                    │                  │                     │
│  │ en_iso       │         │                    │                  │                     │
│  └──────────────┘         │                    │                  │                     │
│                           │                    │                  │                     │
├───────────────────────────┼────────────────────┼──────────────────┼─────────────────────┤
│                           │    OPERATIONAL     │                  │                     │
├───────────────────────────┼────────────────────┼──────────────────┼─────────────────────┤
│                           │                    │                  │                     │
│                           │                    │                  │                     │
│  ┌────────────────────────┴────────────────────┴──────────────────┴───────────────┐    │
│  │                                    PART                                         │    │
│  │─────────────────────────────────────────────────────────────────────────────────│    │
│  │ part_number (UQ)  │  name  │  description  │  status  │  deleted_at             │    │
│  └────────┬────────────────────────┬─────────────────────┬────────────────┬────────┘    │
│           │                        │                     │                │             │
│           │ 1                      │ 1                   │ 1              │ 1           │
│           ▼ N                      ▼ N                   ▼ N              ▼ N           │
│  ┌─────────────────┐    ┌──────────────────┐    ┌────────────┐    ┌──────────────┐     │
│  │  MaterialInput  │    │    Operation     │    │   Batch    │    │   Drawing    │     │
│  │─────────────────│    │──────────────────│    │────────────│    │──────────────│     │
│  │ seq             │    │ seq              │    │ batch_num  │    │ file_name    │     │
│  │ width           │    │ name             │    │ quantity   │    │ is_primary   │     │
│  │ length          │    │ time_minutes     │    │ unit_price │    │ version      │     │
│  │ weight_kg       │    │ work_center_id ──┼────┼──► SET NULL│    │              │     │
│  │ price_category ─┼────┼──► SET NULL      │    │ is_frozen  │    │              │     │
│  │ material_item ──┼────┼──► SET NULL      │    │            │    │              │     │
│  └─────────────────┘    └────────┬─────────┘    └────────────┘    └──────────────┘     │
│                                  │ 1                                                    │
│                                  ▼ N                                                    │
│                         ┌──────────────────┐                                           │
│                         │     Feature      │                                           │
│                         │──────────────────│                                           │
│                         │ name             │                                           │
│                         │ value            │                                           │
│                         └──────────────────┘                                           │
│                                                                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                    SALES                                                │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  ┌──────────────┐                        ┌─────────────────────────────────────────┐   │
│  │   Partner    │                        │                  Quote                  │   │
│  │──────────────│ 1                    N │─────────────────────────────────────────│   │
│  │ partner_num  │◄───────────────────────│ quote_number (UQ)                       │   │
│  │ (UQ)         │       SET NULL         │ partner_id ────► SET NULL               │   │
│  │ name         │                        │ status (DRAFT/SENT/APPROVED/REJECTED)   │   │
│  │ ico          │                        │ total                                   │   │
│  │ dic          │                        │ snapshot_data (JSON) ← na SENT          │   │
│  └──────────────┘                        │ deleted_at                              │   │
│                                          └────────────────────┬────────────────────┘   │
│                                                               │ 1                       │
│                                                               ▼ N                       │
│                                          ┌─────────────────────────────────────────┐   │
│                                          │              QuoteItem                  │   │
│                                          │─────────────────────────────────────────│   │
│                                          │ quote_id ──────► CASCADE                │   │
│                                          │ part_id ───────► SET NULL               │   │
│                                          │ part_number (denormalized snapshot)     │   │
│                                          │ part_name (denormalized snapshot)       │   │
│                                          │ quantity                                │   │
│                                          │ unit_price                              │   │
│                                          │ total_price                             │   │
│                                          │ deleted_at                              │   │
│                                          └─────────────────────────────────────────┘   │
│                                                                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                    PRODUCTION                                           │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                 BatchSet                                          │  │
│  │──────────────────────────────────────────────────────────────────────────────────│  │
│  │ set_number (UQ)  │  part_id ──► SET NULL  │  is_frozen  │  snapshot_data (JSON)  │  │
│  └────────────────────────────────────────────────────────┬─────────────────────────┘  │
│                                                           │ 1                          │
│                                                           ▼ N                          │
│                                                    ┌────────────┐                      │
│                                                    │   Batch    │ (také pod Part)      │
│                                                    │────────────│                      │
│                                                    │ batch_set  │                      │
│                                                    │ ──► CASCADE│                      │
│                                                    └────────────┘                      │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘

LEGENDA:
─────────────────────────────────────────────────
►  FK směr
◄  Zpětný vztah (back_populates)
1  One side
N  Many side
(UQ) Unique constraint
SET NULL  ondelete="SET NULL" - FK zůstane, hodnota NULL
CASCADE   ondelete="CASCADE" - smaže se s parentem
RESTRICT  Nelze smazat parent dokud existují children
```

---

## 2. DELETE BEHAVIOR MATICE

| Parent Entity | Child Entity | ON DELETE | Důsledek |
|---------------|--------------|-----------|----------|
| **Part** | Operation | CASCADE (code) | ⚠️ HARD delete operací |
| **Part** | MaterialInput | CASCADE (code) | ⚠️ HARD delete vstupů |
| **Part** | Batch | CASCADE | ⚠️ HARD delete dávek |
| **Part** | Drawing | CASCADE | ⚠️ HARD delete výkresů |
| **Part** | BatchSet.part_id | SET NULL | BatchSet osiří |
| **Part** | QuoteItem.part_id | SET NULL | QuoteItem zachová snapshot |
| **Quote** | QuoteItem | CASCADE | Smaže položky s nabídkou |
| **Quote** | Partner.partner_id | SET NULL | Quote osiří |
| **Partner** | Quote.partner_id | SET NULL | Quotes zůstanou |
| **MaterialGroup** | MaterialItem | CASCADE (code) | ⚠️ SMAŽE VŠECHNY POLOŽKY! |
| **MaterialGroup** | MaterialNorm | RESTRICT | Nelze smazat s normami |
| **MaterialPriceCategory** | MaterialPriceTier | CASCADE (code) | Smaže cenové úrovně |
| **MaterialPriceCategory** | MaterialInput.price_category_id | SET NULL | Input ztratí kategorii |
| **MaterialItem** | MaterialInput.material_item_id | SET NULL | Input ztratí položku |
| **WorkCenter** | Operation.work_center_id | SET NULL | Operace ztratí pracoviště |
| **Operation** | Feature | CASCADE | Smaže features |
| **BatchSet** | Batch | CASCADE (code) | Smaže dávky v sadě |

---

## 3. KONTROLNÍ MECHANISMY - CO MÁME

### ✅ FUNGUJE

| Mechanismus | Kde | Popis |
|-------------|-----|-------|
| FK Constraints | DB level | Databáze hlídá referenční integritu |
| Soft Delete | AuditMixin | deleted_at, deleted_by pro většinu entit |
| Optimistic Locking | AuditMixin | version column, auto-increment |
| Audit Trail | AuditMixin | created_at/by, updated_at/by |
| Pydantic Validation | Schemas | Field(gt=0), max_length, regex |
| Transaction Rollback | safe_commit() | Při chybě rollback |
| Quote Snapshot | Quote.snapshot_data | Při SENT se uloží stav |
| Batch Freeze | Batch.is_frozen | Zamkne ceny |
| Status Protection | Quote delete | SENT/APPROVED nelze smazat |

### ❌ CHYBÍ / NEFUNGUJE

| Problém | Riziko | Popis |
|---------|--------|-------|
| Part HARD delete | 🔴 CRITICAL | Smaže vše bez možnosti recovery |
| Partner HARD delete | 🔴 HIGH | Quotes osiří bez historie |
| Soft delete nekaskáduje | 🔴 HIGH | Part soft delete ≠ children soft delete |
| Unique vs Soft Delete | 🔴 CRITICAL | Nelze vytvořit záznam se stejným číslem po soft delete |
| MaterialGroup CASCADE | 🔴 CRITICAL | Smaže VŠECHNY MaterialItems bez varování |
| NumberGenerator nefiltruje | 🟡 MEDIUM | Může vygenerovat číslo soft-deleted záznamu |
| Žádné invariant checks | 🔴 HIGH | Neověřujeme konzistenci výpočtů |
| Žádný reconciliation | 🔴 HIGH | Nevíme jestli Quote.total == sum(items) |
| Query nefiltruje deleted | 🟡 MEDIUM | Některé queries vrací smazané záznamy |

---

## 4. INVARIANTY - PRAVIDLA KTERÁ MUSÍ VŽDY PLATIT

### Finanční invarianty (KRITICKÉ)

```
INV-F01: QuoteItem.total_price == QuoteItem.unit_price × QuoteItem.quantity
INV-F02: Quote.total == SUM(QuoteItem.total_price) pro aktivní items
INV-F03: Batch.unit_price musí odpovídat kalkulaci (pokud není frozen)
INV-F04: MaterialInput.calculated_price == weight_kg × tier.price_per_kg
```

### Strukturální invarianty

```
INV-S01: Part.part_number je unikátní mezi aktivními (deleted_at IS NULL)
INV-S02: Quote.quote_number je unikátní mezi aktivními
INV-S03: Partner.partner_number je unikátní mezi aktivními
INV-S04: MaterialItem.material_number je unikátní mezi aktivními
INV-S05: Batch.batch_number je unikátní mezi aktivními
```

### Workflow invarianty

```
INV-W01: Quote se statusem SENT/APPROVED má snapshot_data
INV-W02: Quote se statusem SENT/APPROVED nelze editovat
INV-W03: Frozen Batch nelze editovat (kromě soft delete)
INV-W04: QuoteItem bez part_id musí mít part_number (denormalized)
```

### Referenční invarianty

```
INV-R01: Operation.part_id ukazuje na existující Part
INV-R02: MaterialInput.part_id ukazuje na existující Part
INV-R03: QuoteItem.quote_id ukazuje na existující Quote
INV-R04: Pokud MaterialInput.material_item_id není NULL, musí existovat
```

---

## 5. EDGE CASES - RIZIKOVÉ SCÉNÁŘE

### Scénář 1: Delete → Re-create same ID
```
1. Vytvořím Part P00001234
2. Přidám Operations, MaterialInputs
3. Přidám do Quote
4. Smažu Part (HARD DELETE)
5. Vytvořím NOVÝ Part P00001234
6. ❓ Co se stane?

SOUČASNÝ STAV: Operations/MaterialInputs jsou CASCADE deleted.
               QuoteItem.part_id = NULL, ale má denormalized data.
               Nový Part P00001234 je čistý.
               ✅ Data se nepromíchají (díky hard delete)
               ❌ Ztratili jsme historii
```

### Scénář 2: Soft Delete Part vs Children
```
1. Part má 5 Operations, 3 MaterialInputs
2. Soft delete Part (deleted_at = now)
3. ❓ Co se stane s Operations/MaterialInputs?

SOUČASNÝ STAV: Children NEJSOU soft deleted!
               Query na Operations vrátí 5 operací bez parenta
               ❌ ORPHANED DATA
```

### Scénář 3: Změna ceny po vytvoření Quote
```
1. Quote v DRAFT, QuoteItem odkazuje na Part
2. Změním MaterialPriceTier.price_per_kg
3. ❓ Změní se QuoteItem.unit_price?

SOUČASNÝ STAV: NE - unit_price je uložena v QuoteItem
               ⚠️ Může být outdated vs aktuální kalkulace
               ❓ Není mechanismus pro detekci rozdílu
```

### Scénář 4: Partner smazán, Quote osiří
```
1. Quote odkazuje na Partner
2. Smažu Partner (HARD DELETE)
3. ❓ Co se stane s Quote?

SOUČASNÝ STAV: Quote.partner_id = NULL (SET NULL)
               Quote ztratí info o zákazníkovi
               ❌ Pokud nemá snapshot, ztraceno navždy
```

### Scénář 5: MaterialGroup CASCADE disaster
```
1. MaterialGroup "OCEL" má 500 MaterialItems
2. Admin omylem smaže MaterialGroup
3. ❓ Co se stane?

SOUČASNÝ STAV: CASCADE delete-orphan → 500 MaterialItems SMAZÁNO!
               MaterialInputs.material_item_id = NULL (SET NULL)
               ❌ KATASTROFÁLNÍ ZTRÁTA DAT
```

---

## 6. AKČNÍ PLÁN OPRAV

### Priorita 1: CRITICAL (blokuje produkci)

| # | Oprava | Soubor | Status |
|---|--------|--------|--------|
| 1 | Part delete → soft delete + cascade | parts_router.py | 🟡 ROZPRACOVÁNO |
| 2 | Partner delete → soft delete | partners_router.py | ⬜ TODO |
| 3 | MaterialGroup delete → ochrana | admin_router.py | ⬜ TODO |
| 4 | Partial unique indexy | alembic migration | ⬜ TODO |

### Priorita 2: HIGH (může způsobit finanční ztrátu)

| # | Oprava | Soubor | Status |
|---|--------|--------|--------|
| 5 | Invariant checks pro kalkulace | services/quote_service.py | ⬜ TODO |
| 6 | Quote total reconciliation | services/quote_service.py | ⬜ TODO |
| 7 | Price change detection | services/pricing_service.py | ⬜ TODO |

### Priorita 3: MEDIUM (kvalita dat)

| # | Oprava | Soubor | Status |
|---|--------|--------|--------|
| 8 | NumberGenerator filter | services/number_generator.py | ⬜ TODO |
| 9 | Query filter deleted_at | všechny routery | ⬜ TODO |
| 10 | WorkCenter delete ochrana | work_centers_router.py | ⬜ TODO |

---

## 7. VALIDAČNÍ CHECKLISTY

### Před vytvořením Quote
- [ ] Partner existuje a není smazán?
- [ ] Všechny Parts existují a nejsou smazány?
- [ ] Ceny jsou aktuální (přepočítat)?

### Před odesláním Quote (DRAFT → SENT)
- [ ] Quote.total == sum(items.total_price)?
- [ ] Všechny položky mají platnou cenu > 0?
- [ ] Partner stále existuje?
- [ ] Snapshot vytvořen?

### Před smazáním entity
- [ ] Nemá aktivní závislosti?
- [ ] Není použita v SENT/APPROVED quote?
- [ ] Není frozen?
- [ ] Uživatel potvrdil akci?

---

**Další krok:** Rozhodnutí které opravy implementovat první.
