# GESTIMA - Hloubkový Audit Kódu

**Datum:** 2026-01-26
**Verze aplikace:** 1.2.0
**Auditor:** Claude Opus 4.5
**Účel:** Pre-release audit před beta verzí

---

## Executive Summary

| Metrika | Hodnota |
|---------|---------|
| **Celkový bezpečnostní skóre** | 65/100 |
| **Kritické problémy (P0)** | 12 |
| **Vysoká priorita (P1)** | 23 |
| **Střední priorita (P2)** | 21 |
| **Nízká priorita (P3)** | 18 |
| **Celkem issues** | 74 |
| **Existující testy** | 114 |
| **Chybějící testy** | ~90 |

**Verdikt:** Aplikace vyžaduje opravu P0 blokerů před release. Po opravě P0 a doplnění kritických testů je připravena na beta.

---

## Metodologie auditu

Audit pokryl 6 oblastí s paralelní analýzou:

1. **Modely a schémata** - SQLAlchemy modely, Pydantic validace, vztahy
2. **Bezpečnost** - Auth, OWASP Top 10, headers, secrets
3. **Business logika** - Services, routery, transakce, error handling
4. **Testy** - Pokrytí, kvalita, chybějící testy
5. **Frontend** - Templates, Alpine.js, HTMX, CSS
6. **Infrastruktura** - Databáze, konfigurace, dependencies

---

## P0 - KRITICKÉ PROBLÉMY (Blokující release)

### P0-001: Soft Delete filtry CHYBÍ ve všech SELECT queries

**Závažnost:** KRITICKÁ
**Typ:** Data Integrity
**CVSS:** N/A (Logic error)

**Popis:**
Všechny SELECT dotazy v routers vrací i soft-deleted záznamy. Smazané díly, operace, features a batche se zobrazují uživatelům.

**Postižené soubory:**
- `app/routers/parts_router.py` (řádky 28, 84)
- `app/routers/operations_router.py` (řádek 27)
- `app/routers/features_router.py` (řádek 27)
- `app/routers/batches_router.py` (řádek 32)
- `app/routers/materials_router.py` (řádky 45, 126)

**Aktuální kód:**
```python
result = await db.execute(select(Part).order_by(Part.updated_at.desc()))
```

**Požadovaná oprava:**
```python
result = await db.execute(
    select(Part)
    .where(Part.deleted_at.is_(None))
    .order_by(Part.updated_at.desc())
)
```

**Dopad:** Uživatelé vidí smazaná data, porušení GDPR při soft-delete osobních údajů.

---

### P0-002: Division by Zero v price_calculator.py

**Závažnost:** KRITICKÁ
**Typ:** Runtime Error
**Soubor:** `app/services/price_calculator.py`

**Problém 1 - řádek 293-299:**
```python
def calculate_coop_cost(coop_price: float, coop_min_price: float, quantity: int) -> float:
    if coop_price <= 0:
        return 0
    raw_total = coop_price * quantity
    total = max(raw_total, coop_min_price)
    return round(total / quantity, 2)  # ZeroDivisionError pokud quantity == 0!
```

**Problém 2 - řádek 288-290:**
```python
def calculate_setup_cost(setup_time_min: float, hourly_rate: float, quantity: int) -> float:
    total_setup = (setup_time_min / 60) * hourly_rate
    return round(total_setup / quantity, 2) if quantity > 0 else 0
```
Tento má guard, ale chybí validace `hourly_rate > 0`.

**Požadovaná oprava:**
```python
def calculate_coop_cost(coop_price: float, coop_min_price: float, quantity: int) -> float:
    if coop_price <= 0 or quantity <= 0:
        return 0
    # ...
```

**Dopad:** HTTP 500 při vytváření batch s quantity=0 (bypass Pydantic validace přes DB).

---

### P0-003: Chybějící nullable=False v DB modelech

**Závažnost:** KRITICKÁ
**Typ:** Data Integrity

**Soubor:** `app/models/machine.py` (řádky 15-17)
```python
code = Column(String(50), unique=True, index=True)  # Chybí nullable=False
name = Column(String(200))                           # Chybí nullable=False
type = Column(String(50))                            # Chybí nullable=False
```

**Soubor:** `app/models/batch.py` (řádek 17)
```python
quantity = Column(Integer, default=1)  # Chybí nullable=False
```

**Dopad:**
- DB dovolí NULL hodnoty, Pydantic je odmítne = nekonzistence
- SQLite dovolí NULL v unique sloupci (NULL != NULL) = možné duplikáty

**Požadovaná oprava:**
```python
code = Column(String(50), unique=True, index=True, nullable=False)
name = Column(String(200), nullable=False)
type = Column(String(50), nullable=False)
quantity = Column(Integer, default=1, nullable=False)
```

---

### P0-004: Batch freeze není atomický

**Závažnost:** KRITICKÁ
**Typ:** Transaction Safety
**Soubor:** `app/routers/batches_router.py` (řádky 112-157)

**Aktuální kód:**
```python
async def freeze_batch(...):
    # Snapshot se vytvoří MIMO transakci
    snapshot = await create_batch_snapshot(batch, ...)

    batch.is_frozen = True
    batch.frozen_at = datetime.utcnow()
    batch.snapshot_data = snapshot

    await db.commit()  # Pokud selže, snapshot je "ztracen"
```

**Požadovaná oprava:**
```python
async def freeze_batch(...):
    try:
        snapshot = await create_batch_snapshot(batch, ...)
        batch.is_frozen = True
        batch.frozen_at = datetime.utcnow()
        batch.snapshot_data = snapshot
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Freeze batch failed: {e}")
        raise HTTPException(500, "Zmrazení dávky selhalo")
```

**Dopad:** Data loss - snapshot vytvořen ale neuložen při selhání commit.

---

### P0-005: scalar_one() bez null check

**Závažnost:** KRITICKÁ
**Typ:** Runtime Error
**Soubor:** `app/services/snapshot_service.py` (řádek 45)

**Aktuální kód:**
```python
result = await db.execute(stmt)
batch = result.scalar_one()  # Vyhodí NoResultFound pokud batch neexistuje!
```

**Požadovaná oprava:**
```python
result = await db.execute(stmt)
batch = result.scalar_one_or_none()
if not batch:
    raise ValueError(f"Batch {batch_id} not found")
```

**Dopad:** Unhandled exception při snapshot neexistujícího batch.

---

### P0-006: Výpočty v JavaScript místo Pythonu

**Závažnost:** KRITICKÁ
**Typ:** Architecture Violation (CLAUDE.md Pravidlo #1)
**Soubor:** `app/templates/parts/edit.html`

**Porušení na řádcích:**
- 318-325: Výpočty procent pro bar chart
- 242: Dělení objemu
- 250: Fallback density
- 856: Součet operation times

**Příklad problému (řádky 318-325):**
```javascript
// Frontend výpočty - PORUŠUJE PRAVIDLO #1!
materialPercent: (batch.material_cost / batch.unit_cost * 100).toFixed(1),
machiningPercent: (batch.machining_cost / batch.unit_cost * 100).toFixed(1),
coopPercent: (batch.coop_cost / batch.unit_cost * 100).toFixed(1),
```

**Požadovaná oprava:**
Backend by měl vracet již vypočtené procenta v response:
```python
# price_calculator.py
class BatchPriceBreakdown(BaseModel):
    material_percent: float
    machining_percent: float
    coop_percent: float
```

**Dopad:** Nekonzistence výpočtů mezi frontendem a backendem, porušení Single Source of Truth.

**✅ VYŘEŠENO (2026-01-26):**
- Přidány `@computed_field` properties v `BatchResponse` (batch.py)
- Percentages nyní vypočítané v Pythonu a vrácené v API response
- Frontend template používá backend hodnoty (`batch.material_percent`)
- Přidány testy v `tests/test_batch_percentages.py` (5 testů, 100% pass)
- See: CHANGELOG.md "Static Bar Charts Fix"

---

### P0-007: Chyba v Soft Delete - sync operace v async kontextu

**Závažnost:** KRITICKÁ
**Typ:** Runtime Error
**Soubor:** `app/routers/materials_router.py` (řádky 245-246)

**Aktuální kód:**
```python
item.deleted_at = db.execute("SELECT CURRENT_TIMESTAMP").scalar_one()
```

**Problém:** Sync `db.execute()` v async kontextu způsobí deadlock nebo runtime error.

**Požadovaná oprava:**
```python
item.deleted_at = datetime.utcnow()
```

---

### P0-008: Chybí Foreign Key na operation.machine_id

**Závažnost:** KRITICKÁ
**Typ:** Data Integrity
**Soubor:** `app/models/operation.py` (řádek 23)

**Aktuální kód:**
```python
machine_id = Column(Integer, nullable=True)  # BEZ ForeignKey!
```

**Požadovaná oprava:**
```python
machine_id = Column(Integer, ForeignKey("machines.id", ondelete="SET NULL"), nullable=True)
```

**Dopad:** Lze uložit ID neexistujícího stroje, porušuje referenční integritu.

---

### P0-009: Double Rounding v kalkulacích

**Závažnost:** VYSOKÁ → KRITICKÁ (při velkých sériích)
**Typ:** Calculation Error
**Soubor:** `app/services/price_calculator.py` (řádky 115-119, 210-214, 276-279)

**Problém:**
```python
result.volume_mm3 = round(volume_mm3, 0)  # Zaokrouhleno
result.weight_kg = round(weight_kg, 3)     # Zaokrouhleno
result.cost = round(cost, 2)               # Zaokrouhleno
# Tyto hodnoty se pak používají k dalším výpočtům!
```

**Dopad:** Akumulace zaokrouhlovacích chyb u velkých sérií (1000+ ks).

**Řešení:** Zaokrouhlovat až na konci, používat Decimal pro finanční výpočty.

---

### P0-010: Negative Inner Radius v TUBE výpočtu

**Závažnost:** KRITICKÁ
**Typ:** Silent Failure
**Soubor:** `app/services/price_calculator.py` (řádky 96-102)

**Aktuální kód:**
```python
r_inner = r_outer - stock_wall_thickness
if r_inner > 0:
    volume_mm3 = math.pi * (r_outer**2 - r_inner**2) * stock_length
# Pokud r_inner <= 0, volume_mm3 zůstává 0 BEZ VAROVÁNÍ!
```

**Požadovaná oprava:**
```python
r_inner = r_outer - stock_wall_thickness
if r_inner <= 0:
    logger.warning(f"Invalid tube geometry: wall_thickness >= radius")
    raise ValueError("Tloušťka stěny nemůže být větší než poloměr")
volume_mm3 = math.pi * (r_outer**2 - r_inner**2) * stock_length
```

---

### P0-011: Race condition v duplicate_part()

**Závažnost:** KRITICKÁ
**Typ:** Concurrency
**Soubor:** `app/routers/parts_router.py` (řádky 160-210)

**Problém:**
```python
while True:
    check = await db.execute(select(Part).where(Part.part_number == new_part_number))
    if not check.scalar_one_or_none():
        break
    counter += 1
    new_part_number = f"{base_number}-COPY-{counter}"

# ... vytvoření dílu ...
await db.commit()  # RACE CONDITION: Jiný request může vytvořit stejný part_number!
```

**Řešení:** Použít `SELECT FOR UPDATE` nebo unique constraint s retry logikou.

---

### P0-012: Reference Loader cache bez thread safety

**Závažnost:** VYSOKÁ
**Typ:** Concurrency
**Soubor:** `app/services/reference_loader.py` (řádky 16-62)

**Problém:**
```python
_machines_cache: List[Dict[str, Any]] = []

async def get_machines() -> List[Dict[str, Any]]:
    global _machines_cache
    if _machines_cache:
        return _machines_cache
    # ... načítání ...
    _machines_cache = [...]  # Bez lock!
```

**Požadovaná oprava:**
```python
import asyncio
_cache_lock = asyncio.Lock()

async def get_machines() -> List[Dict[str, Any]]:
    async with _cache_lock:
        if _machines_cache:
            return _machines_cache
        # ... načítání ...
```

---

## P1 - VYSOKÁ PRIORITA

### P1-001: Veřejné API endpointy bez autentizace

**Soubor:** `app/routers/data_router.py` (řádky 12-24)

**Problém:** Endpointy `/api/data/machines`, `/api/data/feature-types`, `/api/data/materials` nemají `Depends(get_current_user)`.

**Dopad:** Útočník může zmapovat všechny stroje a materiály bez přihlášení.

---

### P1-002: XSS riziko v toast notifikacích

**Soubor:** `app/static/js/gestima.js` (řádek 39)

```javascript
toast.innerHTML = message  // Potenciální XSS
```

**Řešení:** `toast.textContent = message`

---

### P1-003: localStorage bez try/catch

**Soubor:** `app/static/js/gestima.js` (řádky 107-118)

```javascript
const saved = localStorage.getItem('parts_visible_columns');
```

**Problém:** Selhá v private browsing mode nebo když storage je disabled.

---

### P1-004: Error handling chybí v services

**Postižené soubory:**
- `app/services/auth_service.py` - `create_user()` bez try/except
- `app/services/cutting_conditions.py`
- `app/services/reference_loader.py`
- `app/services/snapshot_service.py`
- `app/services/price_calculator.py`

---

### P1-005: Chybí timestamp fields v Response schématech

**Soubory:**
- `app/models/machine.py:125-128` - `MachineResponse` chybí `created_at`, `updated_at`
- `app/models/cutting_condition.py:65-68` - `CuttingConditionResponse` chybí timestamps

---

### P1-006: Untyped dict parameter

**Soubor:** `app/routers/operations_router.py` (řádek 137)

```python
async def change_mode(data: dict, ...):  # Měl by být Pydantic model!
```

---

### P1-007: Chybí Pydantic Field validace

**Postižené modely:**
- `CuttingConditionBase` - 7 polí bez validace
- `MachineBase` - 7 polí bez validace
- `LoginRequest` - slabá validace hesla
- `StockPriceResponse` - 4 pole bez validace

---

### P1-008: Chybí Response Models na 5 endpointech

**Soubory:**
- `data_router.py` - `/machines`, `/materials`, `/feature-types`
- `misc_router.py` - `/fact`, `/weather`

---

### P1-009: Chybí status_code na DELETE

**Postižené soubory:**
- `parts_router.py:205`
- `operations_router.py:108`
- `features_router.py:104`
- `materials_router.py:232`
- `batches_router.py:75`

---

### P1-010: Rate Limiting absence na misc endpointech

**Soubor:** `app/routers/misc_router.py`

Endpointy `/api/misc/fact` a `/api/misc/weather` nemají rate limit - snadný DoS útok na externí API.

---

### P1-011: Cache bez invalidace

**Soubor:** `app/services/reference_loader.py` (řádky 12-22)

Globální cache se NIKDY neinvaliduje. Pokud admin edituje Material, cache bude stará.

---

### P1-012 až P1-023: Další vysoké priority

- Chybí index na `frozen_by_id` v batch modelu
- Duplikace soft delete kódu (batches_router, materials_router)
- Chybí audit helper usage v delete operacích
- Inconsistent transaction handling across routers
- Missing refresh after soft delete
- Deprecated function still used (calculate_material_cost)
- Hardcoded cutting_mode strings místo Enum
- Missing input sanitization v materials_router
- Search optimization issue (subquery count)
- Chybí logging context v price_calculator

---

## P2 - STŘEDNÍ PRIORITA

### P2-001: Chybí Alembic pro DB migrace

Migrační strategie je ad-hoc. Pouze `_migrate_parts_stock_columns()` v `init_db()`.

### P2-002: Console.log statements v produkci

8 míst s console.log v `parts/edit.html` a `gestima.js`.

### P2-003: .env.example má slabý SECRET_KEY

`SECRET_KEY=15adi` - pouze 15 znaků místo minimálních 32.

### P2-004: min-width: 1000px blokuje responsive

CSS a HTML mají hardcoded min-width: 1000px.

### P2-005: Chybí pip-audit

Žádné security scanning dependencies.

### P2-006 až P2-021: Další střední priority

- Operation.seq default 10 místo 1 (design decision?)
- Zastaralé TODO komentáře
- Hardcoded hodnoty v time_calculator
- Dead code (parts/list.html, list_fragment.html)
- Duplicate API calls při inicializaci
- Race condition savePart + loadStockCost
- Alpine.js init bez x-init
- hx-boost="false" anti-pattern
- Chybí validation na numeric inputs
- Nekonzistentní error messages
- Redundantní x-show podmínky
- Příliš mnoho inline stylů
- Chybí accessibility atributy
- Magické číslo v debouncingu
- Chybí loading skeleton

---

## P3 - NÍZKÁ PRIORITA

- Zastaralé dokumenty (NEXT-STEPS.md reference)
- Chybí data type validation na frontendu
- Computed property bez memoization
- Nevalidní HTML struktura
- Nezbytný MaterialDB alias

---

## OWASP Top 10 Hodnocení

| Kategorie | Status | Poznámka |
|-----------|--------|----------|
| A01: Broken Access Control | ⚠️ PROBLÉM | Veřejné endpointy bez auth |
| A02: Cryptographic Failures | ✅ OK | bcrypt, JWT správně |
| A03: Injection | ✅ CHRÁNĚNO | SQLAlchemy ORM |
| A04: Insecure Design | ⚠️ PROBLÉM | Soft delete logic gaps |
| A05: Security Misconfiguration | ⚠️ PROBLÉM | DEBUG mode, missing headers |
| A06: Vulnerable Components | ✅ OK | Aktuální dependencies |
| A07: Auth Failures | ⚠️ PROBLÉM | Hardcoded SECRET_KEY risk |
| A08: Data Integrity Failures | ⚠️ PROBLÉM | Race conditions |
| A09: Logging Failures | ✅ OK | Structured JSON logging |
| A10: SSRF | ✅ CHRÁNĚNO | httpx s timeout |

---

## Security Headers Status

| Hlavička | Status |
|----------|--------|
| X-Frame-Options | ✅ DENY |
| X-Content-Type-Options | ✅ nosniff |
| X-XSS-Protection | ✅ 1; mode=block |
| Referrer-Policy | ✅ strict-origin-when-cross-origin |
| Permissions-Policy | ✅ Implementován |
| Content-Security-Policy | ❌ CHYBÍ |
| Strict-Transport-Security | ❌ CHYBÍ |

---

## Testovací pokrytí

### Existující testy (114)

| Soubor | Počet | Status |
|--------|-------|--------|
| test_authentication.py | ~20 | ✅ Kompletní |
| test_materials.py | ~25 | ✅ Kompletní |
| test_snapshots.py | ~15 | ✅ Kompletní |
| test_health.py | ~10 | ✅ Kompletní |
| test_validations.py | ~15 | ✅ Kompletní |
| test_pricing.py | ~10 | ✅ Kompletní |
| test_audit_infrastructure.py | ~15 | ✅ Kompletní |
| Ostatní | ~4 | ⚠️ Incomplete |

### Chybějící testy (~90)

| Soubor | Počet | Priorita |
|--------|-------|----------|
| test_parts_router.py | 13 | P0 |
| test_operations_router.py | 7 | P0 |
| test_features_router.py | 6 | P0 |
| test_batches_router.py | 5 | P0 |
| test_materials_router.py | 9 | P1 |
| test_data_router.py | 4 | P1 |
| test_misc_router.py | 4 | P2 |
| test_cascade_operations.py | 5 | P1 |
| test_optimistic_locking.py (complete) | 10 | P1 |
| test_auth_advanced.py | 5 | P1 |
| Integration tests | 15-20 | P2 |

---

## Doporučení pro Beta Release

### Fáze 1: Oprava P0 blokerů

| # | Úkol | Odhad |
|---|------|-------|
| 1 | Soft delete filtry ve všech routers | 2h |
| 2 | Division by zero guards | 30m |
| 3 | Nullable constraints v modelech | 30m |
| 4 | Atomický batch freeze | 1h |
| 5 | scalar_one_or_none | 15m |
| 6 | Frontend výpočty → Python | 3h |
| 7 | Sync→async oprava v materials_router | 15m |
| 8 | FK na operation.machine_id | 30m |
| 9 | Double rounding fix | 1h |
| 10 | TUBE geometry validation | 30m |
| 11 | Race condition fixes | 2h |
| 12 | Cache thread safety | 30m |

**Celkem Fáze 1:** ~12 hodin

### Fáze 2: Kritické testy

| # | Úkol | Odhad |
|---|------|-------|
| 1 | test_parts_router.py | 2h |
| 2 | test_operations_router.py | 1.5h |
| 3 | test_features_router.py | 1h |
| 4 | test_batches_router.py | 1h |

**Celkem Fáze 2:** ~6 hodin

### Fáze 3: P1 opravy

Selektivně dle kapacity, minimálně:
- Auth na data_router endpointy
- XSS fix v toast
- Error handling v services

**Celkem Fáze 3:** ~4 hodiny

### Celkový odhad do Beta: ~22 hodin

---

## Checklist pro Beta Release

### Infrastruktura
- [ ] P0 issues opraveny (12 položek)
- [ ] Minimálně 150 testů
- [ ] pytest -v projde bez chyb
- [ ] pip-audit bez kritických zranitelností

### Bezpečnost
- [ ] SECRET_KEY >= 32 znaků v produkci
- [ ] DEBUG=false
- [ ] Všechny endpointy mají auth
- [ ] Security headers aktivní

### Funkčnost
- [ ] Part CRUD funguje
- [ ] Operation CRUD funguje
- [ ] Feature CRUD funguje
- [ ] Batch create/freeze funguje
- [ ] Kalkulace cen funguje
- [ ] Soft delete funguje správně

### Data
- [ ] Materials seeded
- [ ] Machines seeded
- [ ] Cutting conditions seeded

### UI
- [ ] Error messages srozumitelné
- [ ] Loading states na async operacích
- [ ] Žádné console.log v produkci

---

## Závěr

Aplikace GESTIMA má solidní základ s dobře implementovanými:
- Async SQLAlchemy s WAL mode
- Pydantic v2 validace
- JWT autentizace s RBAC
- Audit trail (created/updated/deleted by)
- Optimistic locking

Hlavní slabiny před beta release:
1. **Soft delete logic** - záznamy se vrací i po smazání
2. **Edge cases v kalkulacích** - division by zero, negative radius
3. **Race conditions** - cache, duplicate_part
4. **Atomicita transakcí** - batch freeze
5. **Chybějící testy** - 90 testů na routers

Po opravě P0 blokerů a doplnění kritických testů je aplikace připravena na beta release.

---

**Podpis:**
Claude Opus 4.5
Hloubkový audit kódu
2026-01-26
