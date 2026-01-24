# CLAUDE.md - Pravidla pro AI Asistenta

## KRITICKÝ PŘÍSTUP

**POVINNOST:** Buď maximálně kritický. Oponuj návrhům (i vlastním). Hledej slabiny. Buď stručný a efektivní./

- Před implementací: "Co se může pokazit?"
- Po návrhu: "Je to nejjednodušší řešení?"
- Vždy: "Neexistuje lepší způsob?"
- **ADR rozhodnutí:** "Je to architektonické rozhodnutí? MUSÍM upozornit!"

**Cíl:** Přímočarý, efektivní kód. Žádné over-engineering. Žádné zbytečnosti.

---

## STACK

| Vrstva | Technologie |
|--------|-------------|
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| Database | SQLite + WAL mode, aiosqlite |
| Frontend | Jinja2, Alpine.js, HTMX |
| Testy | pytest, pytest-asyncio |

**Struktura:**
```
app/
├── models/          # SQLAlchemy modely
├── schemas/         # Pydantic schemas
├── services/        # Business logika (výpočty ZDE)
├── routers/         # API endpoints
├── templates/       # Jinja2 HTML
└── static/          # CSS, JS
```

---

## DB SCHÉMA (klíčové tabulky)

| Tabulka | Účel | Klíčové sloupce |
|---------|------|-----------------|
| parts | Díly | part_number, name, stock_type, material_group |
| operations | Operace na dílu | part_id, operation_type, cutting_mode |
| features | Prvky operace | operation_id, feature_type, diameter, length |
| batches | Výrobní dávky | part_id, quantity, status |
| materials | Materiály | code, name, density, price_per_kg |
| cutting_conditions | Řezné podmínky | material_group, operation_type, vc, f, ap |

**Vztahy:**
- Part → Operations (1:N)
- Operation → Features (1:N)
- Part → Batches (1:N)

**Audit (AuditMixin na všech tabulkách):**
- created_at, updated_at, version
- created_by, updated_by (MUSÍ SE VYPLŇOVAT!)
- deleted_at, deleted_by (soft delete)

---

## KRITICKÁ PRAVIDLA

### 1. Výpočty POUZE v Pythonu
```python
# SPRÁVNĚ: services/price_calculator.py
def calculate_stock_price(...) -> float:
    return volume * density * price_per_kg
```
```javascript
// SPRÁVNĚ: JS pouze zobrazuje
const data = await fetch('/api/stock-price').then(r => r.json());
element.textContent = data.price;
```
**NIKDY:** Výpočty v JavaScriptu.

### 2. Single Source of Truth
- Data: Database → API → Frontend
- Logika: Python (services/) → API response
- **NIKDY:** Duplikace logiky Python + JS

### 3. Kompletní UI update po API
```javascript
// Po API volání aktualizovat VŠE co backend změnil
const response = await fetch('/api/operations/' + id + '/recalculate');
const data = await response.json();
updateOperation(data.operation);
data.features.forEach(f => updateFeature(f));
updateTotals(data.totals);
```

### 4. Zachovat UI stav
```javascript
// Před update: zapamatovat stav
const wasExpanded = isExpanded(id);
// Po update: obnovit stav
if (wasExpanded) expand(id);
```

### 5. Edit, ne Write
- **Edit tool:** Pro změny existujících souborů
- **Write tool:** POUZE pro nové soubory
- **Důvod:** Write = přepsání celého souboru = drahé + riziko ztráty

### 6. Žádné hardcoded hodnoty
```javascript
// SPRÁVNĚ: Data z API
const materials = await fetch('/api/data/materials').then(r => r.json());
```
```html
<!-- NIKDY: Hardcoded options -->
<option value="11xxx">Ocel</option>
```

### 7. Role Hierarchy (RBAC)
```python
# SPRÁVNĚ: Admin >= Operator >= Viewer
@router.put("/api/parts/{id}")
async def update_part(
    current_user: User = Depends(require_role([UserRole.OPERATOR]))
):
    # Admin i Operator mohou editovat (hierarchie)
    pass
```
**NIKDY:** `if user.role == UserRole.OPERATOR` (striktní porovnání)
**VŽDY:** Použít `has_permission()` nebo `require_role()` s hierarchií (viz ADR-006)

### 8. Latency

- **Rychlost:** vždy navrhovat řešení s ohledem maximální odezvy v UI 100 ms

### 9. Business validace v Pydantic modelech (POVINNÉ)

Každý Pydantic model MUSÍ mít Field validace. Při vytváření/úpravě modelu vždy přidat:

```python
# SPRÁVNĚ: Validace pomocí Field()
class PartCreate(BaseModel):
    part_number: str = Field(..., min_length=1, max_length=50)
    quantity: int = Field(1, gt=0)           # gt=0: musí být > 0
    length: float = Field(0.0, ge=0)         # ge=0: nesmí být záporná
    price: float = Field(..., gt=0)          # povinné, > 0
    name: Optional[str] = Field(None, max_length=200)
```

**Validační vzory:**
| Typ hodnoty | Constraint | Příklad |
|-------------|------------|---------|
| ID (FK) | `gt=0` | `part_id: int = Field(..., gt=0)` |
| Množství | `gt=0` | `quantity: int = Field(1, gt=0)` |
| Rozměry | `ge=0` | `length: float = Field(0.0, ge=0)` |
| Ceny | `gt=0` | `price: float = Field(..., gt=0)` |
| Časy | `ge=0` | `time_min: float = Field(0.0, ge=0)` |
| Pořadí | `ge=1` | `seq: int = Field(1, ge=1)` |
| Texty | `max_length` | `name: str = Field("", max_length=200)` |

**NIKDY:** Pydantic model bez Field validací pro číselné/textové hodnoty

---

## PRODUCTION REQUIREMENTS

### P0 - BLOCKER (bez tohoto nelze nasadit)

| Požadavek | Status | Co udělat |
|-----------|--------|-----------|
| **Authentication** | ✅ HOTOVO | OAuth2 + JWT v HttpOnly Cookie (2026-01-23) |
| **Authorization** | ✅ HOTOVO | RBAC: Admin/Operator/Viewer (2026-01-23) |
| **Role Hierarchy** | ✅ HOTOVO | Admin >= Operator >= Viewer (2026-01-23, ADR-006) |
| **HTTPS** | ✅ DOCS | Caddy reverse proxy + SECURE_COOKIE (ADR-007) |
| **DEBUG=False** | ✅ HOTOVO | .env.example vytvořen (2026-01-23) |

### P1 - KRITICKÉ

| Požadavek | Status | Co udělat / Soubor |
|-----------|--------|-----------|
| **Global error handler** | ✅ HOTOVO | app/gestima_app.py (2026-01-23) |
| **Structured logging** | ✅ HOTOVO | app/logging_config.py (2026-01-23) |
| **Transaction error handling** | ✅ HOTOVO | 14 míst v routerech + db_helpers (2026-01-23) |
| **Backup strategie** | ✅ HOTOVO | CLI: backup, backup-list, backup-restore (2026-01-23) |
| **Audit trail vyplňování** | ✅ HOTOVO | Vyplněno ve všech routerech (2026-01-23) |
| **CORS** | ✅ HOTOVO | CORSMiddleware s konfigurovatelným whitelist (2026-01-23) |
| **Rate limiting** | ✅ HOTOVO | slowapi: 100/min API, 10/min auth (2026-01-24) |

### P2 - DŮLEŽITÉ (Implementační plán - viz níže)

| Požadavek | Status | Co udělat |
|-----------|--------|-----------|
| **Optimistic locking** | ✅ HOTOVO | Version check v 4 routerech + 11 testů (ADR-008) - 2026-01-24 |
| **Batch Snapshot (Freeze)** | ✅ HOTOVO | Minimal Snapshot - zmrazení cen v nabídkách (ADR-012) - 2026-01-24 |
| **State Machine** | ❌ NEIMPLEMENTOVÁNO | Part.status není potřeba - freeze je na Batch level (ADR-012) |
| **Business validace** | ✅ HOTOVO | Pydantic Field validace pro všechny modely (2026-01-24) |
| **Health check endpoint** | ✅ HOTOVO | GET /health (2026-01-24) |
| **Graceful shutdown** | ✅ HOTOVO | Lifespan cleanup + DB dispose (2026-01-24) |

---

## IMPLEMENTAČNÍ PLÁN P2 (Prioritizace: Riziko → Architektura)

**Kontext:** Auditní zpráva ([docs/audit.md](docs/audit.md)) identifikovala 3 kritické nálezy:
1. Absence State Machine → nekontrolované změny dat
2. Price Decay → ztráta historické pravdy o cenách
3. Nedostatečný audit trail → nelze rekonstruovat změny

**Prioritizace:** Podle reálného rizika (data loss, price integrity), ne architektonické "krásy".

### Fáze 1: Optimistic Locking (B2) ⭐ NEJVYŠŠÍ PRIORITA

**Riziko:** Dva operátoři editují stejný díl současně → jeden přepíše data druhého = **DATA LOSS**.

**Implementace:**
```python
# Přidat version column do všech editovatelných entit
class Part(Base, AuditMixin):
    version = Column(Integer, default=1, nullable=False)

# Check version při UPDATE (v routerech)
result = await db.execute(
    update(Part)
    .where(Part.id == id, Part.version == data.version)
    .values(**data.dict(), version=Part.version + 1)
)
if result.rowcount == 0:
    raise HTTPException(409, "Data byla změněna jiným uživatelem")
```

**Soubory k úpravě:**
- `app/models/part.py` (přidat version)
- `app/models/operation.py` (přidat version)
- `app/models/feature.py` (přidat version)
- `app/models/batch.py` (přidat version)
- `app/routers/parts_router.py` (version check v PUT)
- `app/routers/operations_router.py` (version check v PUT)
- `app/routers/features_router.py` (version check v PUT)
- `app/routers/batches_router.py` (version check v PUT)
- `tests/test_optimistic_locking.py` (nový soubor)
- `docs/ADR/008-optimistic-locking.md` (nový soubor)

**Kritéria úspěchu:**
- ✅ Souběžný update vrací HTTP 409 "Conflict"
- ✅ Frontend zobrazuje alert "Data změněna jiným uživatelem"
- ✅ Testy: 2 concurrent updates = jeden selže s 409

---

### Fáze 2: State Machine (A1) - MINIMÁLNÍ IMPLEMENTACE

**Riziko:** Part v produkci/fakturaci lze libovolně měnit → **NEKONZISTENCE, AUDIT PROBLÉM**.

**Implementace (MINIMÁLNÍ - jen 2 stavy):**
```python
class PartStatus(str, Enum):
    DRAFT = "draft"    # Lze editovat
    LOCKED = "locked"  # Read-only (v produkci/fakturováno)

# Validace v routerech
if part.status == PartStatus.LOCKED:
    raise HTTPException(403, "Díl je uzamčen pro editaci")

# Nový endpoint pro lock
@router.post("/api/parts/{id}/lock")
async def lock_part(id: int, db: AsyncSession):
    part.status = PartStatus.LOCKED
    await db.commit()
```

**Soubory k úpravě:**
- `app/models/enums.py` (přidat PartStatus enum)
- `app/models/part.py` (přidat status column)
- `app/routers/parts_router.py` (validace + POST /lock endpoint)
- `app/static/main.js` (UI: disable controls pro LOCKED)
- `app/templates/edit.html` (zobrazit status badge)
- `tests/test_state_machine.py` (nový soubor)
- `docs/ADR/009-state-machine.md` (nový soubor)

**Kritéria úspěchu:**
- ✅ LOCKED part nelze editovat (HTTP 403)
- ✅ Endpoint POST /api/parts/{id}/lock funguje
- ✅ UI zobrazuje status + disable edit controls pro LOCKED

**Budoucí rozšíření (POZDĚJI):**
- Více stavů: DRAFT → CALCULATED → OFFERED → ORDERED → LOCKED
- Workflow transitions s validacemi

---

### Fáze 3: Snapshoty (A3) - STABILNÍ CENY

**Riziko:** Změna ceny materiálu → nabídka z minulého měsíce ukazuje jinou cenu = **ZTRÁTA HISTORICKÉ PRAVDY**.

**Implementace:**
```python
# models/part.py
snapshot_data = Column(JSON, nullable=True)

# routers/parts_router.py - při lock vytvořit snapshot
@router.post("/api/parts/{id}/lock")
async def lock_part(id: int, db: AsyncSession):
    # Snapshot zachytí: ceny materiálů, strojů, všechny parametry
    snapshot = await create_snapshot(part, db)  # service
    part.snapshot_data = snapshot
    part.status = PartStatus.LOCKED
    await db.commit()
```

**Soubory k úpravě:**
- `app/models/part.py` (přidat snapshot_data column)
- `app/services/snapshot_service.py` (nový soubor - create_snapshot, compare_snapshot)
- `app/routers/parts_router.py` (použít snapshot_service v /lock)
- `tests/test_snapshots.py` (nový soubor)

**Kritéria úspěchu:**
- ✅ LOCKED part má snapshot_data (JSON s cenami, parametry)
- ✅ Změna ceny materiálu neovlivní cenu v locked part
- ✅ UI může zobrazit "snapshot vs aktuální" porovnání (future)

**Závislost:** Potřebuje State Machine (snapshot se vytváří při přechodu do LOCKED).

---

### Pořadí implementace (STRIKTNÍ)

| Krok | Komponenta | Závislosti | Přínos | ADR |
|------|------------|------------|--------|-----|
| **1** | Optimistic Locking | - | Ochrana před data loss (okamžitě) | ADR-008 |
| **2** | State Machine (min) | - | Workflow + ochrana dat v produkci | ADR-009 |
| **3** | Snapshoty | State Machine (trigger = lock) | Stabilní ceny v nabídkách | ADR-002 ✅ |

**Proč toto pořadí:**
- **B2 první:** Největší riziko (data loss při concurrent edit) → řešíme okamžitě
- **A1 druhý:** Prerekvizita pro A3 (snapshot potřebuje event "lock part")
- **A3 třetí:** Závisí na A1, řeší price decay

---

## VZORY PRO IMPLEMENTACI

### Transaction pattern (POVINNÉ)
```python
async def create_part(db: AsyncSession, data: PartCreate, user_id: int) -> Part:
    try:
        part = Part(**data.model_dump())
        part.created_by = user_id  # AUDIT!
        db.add(part)
        await db.commit()
        await db.refresh(part)
        return part
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(409, "Duplicate part_number")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"DB error: {e}", exc_info=True)
        raise HTTPException(500, "Database error")
```

### Error handler pattern (POVINNÉ)
```python
# V gestima_app.py
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

### Logging pattern (POVINNÉ)
```python
import logging
logger = logging.getLogger(__name__)

# V kódu
logger.info(f"Creating part: {data.part_number}")
logger.error(f"Failed: {e}", exc_info=True)
```

---

## ANTI-PATTERNS (co se pokazilo)

| ID | Problém | Řešení |
|----|---------|--------|
| L-001 | Výpočty v JS | Vše v Python services/ |
| L-002 | Duplikace logiky | Single Source of Truth |
| L-003 | Ztráta UI stavu | Zapamatovat/obnovit expanded |
| L-004 | Write místo Edit | Edit pro změny |
| L-005 | Částečný UI update | Aktualizovat VŠE po API |
| L-006 | Hardcoded data | Načítat z API |
| L-007 | Chybějící audit | Vyplňovat created_by/updated_by |
| L-008 | Žádné try/except | Transaction error handling |
| L-009 | Pydantic bez validací | Vždy Field() s gt/ge/max_length |

---

## WORKFLOW

### Před implementací
1. **Zeptej se:** "Co přesně má být výsledek?"
2. **Oponuj:** "Není jednodušší způsob?"
3. **Identifikuj:** Které soubory změnit
4. **Read:** Přečíst soubory PŘED editací
5. **ADR Check:** Je to architektonické rozhodnutí? (viz níže)

### Kdy vytvořit ADR (POVINNÉ UPOZORNĚNÍ)

**MUSÍŠ upozornit uživatele a vytvořit ADR když:**

| Typ rozhodnutí | Příklad | Akce |
|----------------|---------|------|
| **Auth strategie** | JWT vs Sessions | ⚠️ UPOZORNIT → ADR |
| **Nová závislost** | Přidat Redis, Celery | ⚠️ UPOZORNIT → ADR |
| **DB změna** | Přidat novou tabulku, změnit vztahy | ⚠️ UPOZORNIT → ADR |
| **API design** | REST vs GraphQL, versioning | ⚠️ UPOZORNIT → ADR |
| **Security pattern** | Rate limiting metoda, CORS policy | ⚠️ UPOZORNIT → ADR |
| **Performance trade-off** | Cache vs real-time data | ⚠️ UPOZORNIT → ADR |

**NENÍ ADR:**
- Přidání pole do existující tabulky
- Bug fix
- Refactoring bez změny API

**Formát upozornění:**
```
⚠️ ARCHITEKTONICKÉ ROZHODNUTÍ

Navrhuji: [co]
Důvod: [proč]
Trade-offs:
  + Výhody: [...]
  - Nevýhody: [...]

Alternativy:
1. [jiný způsob]
2. [další způsob]

Doporučuji vytvořit ADR-XXX po schválení.
```

**Po schválení:** Vytvoř ADR do `docs/ADR/XXX-nazev.md`

### Implementace
1. Backend: Service (logika) → Router (API)
2. Frontend: JS update → HTML template
3. Testy: pytest pro business logiku

### Po implementaci - AUTOMATICKY!

**KRITICKÉ:** Po dokončení implementace VŽDY provést tyto kroky **AUTOMATICKY** (bez dotazu uživatele):

#### 1. Testy (POVINNÉ)
```bash
# Spustit existující testy
pytest -v -m critical

# Pokud je implementace KRITICKÁ (P0/P1/security/data integrity), napsat NOVÉ testy
# Příklad: error handling → test_error_handling.py
pytest tests/test_*.py -v
```

**Kdy psát nové testy (automaticky identifikovat):**
- ✅ P0/P1 production requirements
- ✅ Error handling / transaction safety
- ✅ Security features
- ✅ Data integrity / validation
- ✅ Business logika (výpočty, ceny, časy)
- ❌ Triviální změny (typo fix, CSS tweak)

#### 2. Dokumentace (POVINNÉ)
Aktualizovat:
- ✅ **CLAUDE.md** - production requirements checklist
- ✅ **CLAUDE.md** - přidat nové vzory/pravidla pokud relevantní
- ⚠️ **ADR** - pokud je to architektonické rozhodnutí (viz výše)

#### 3. Verifikace
```bash
# Manuální test (rychlý smoke test)
uvicorn app.gestima_app:app --reload
# Otevřít http://localhost:8000
```

**DŮLEŽITÉ:** Toto dělej AUTOMATICKY bez ptání. Pokud něco chybí, uživatel to připomene (jako teď).

### Checklist (před ukončením práce)
- [ ] Výpočty pouze v Python
- [ ] UI update kompletní
- [ ] UI stav zachován
- [ ] Error handling (try/except)
- [ ] Audit vyplněn (created_by/updated_by) - pokud máme auth
- [ ] Žádné hardcoded hodnoty
- [ ] Edit (ne Write) pro změny
- [ ] **VALIDACE:** Pydantic modely mají Field() constrainty? (gt, ge, max_length)
- [ ] **ADR:** Upozornil jsem na architektonické rozhodnutí? (pokud relevantní)
- [ ] **TESTY:** Napsal jsem testy pro kritické změny? (automaticky!)
- [ ] **DOCS:** Aktualizoval jsem dokumentaci? (automaticky!)

---

## AKTUÁLNÍ STAV (2026-01-24)

**Co funguje:**
- CRUD pro parts, operations, features, batches
- Výpočty časů a cen (services/)
- UI s Alpine.js + HTMX
- **P0: Authentication** - OAuth2 + JWT v HttpOnly Cookie (SameSite=strict) ✅
- **P0: Authorization** - RBAC (Admin/Operator/Viewer) ✅
- **P0: Role Hierarchy** - Admin >= Operator >= Viewer (ADR-006) ✅
- **P0: DEBUG** - .env.example vytvořen ✅
- **P0: HTTPS** - Caddy reverse proxy + SECURE_COOKIE (ADR-007) ✅
- **P1: Structured logging** (app/logging_config.py) ✅
- **P1: Global error handler** (app/gestima_app.py) ✅
- **P1: Transaction error handling** (14 míst v routerech + db_helpers) ✅
- **P1: Audit trail** - set_audit() helper (eliminace L-002 duplikace) ✅
- **P1: CORS** - konfigurovatelný whitelist přes CORS_ORIGINS ✅
- **P1: Backup strategie** - CLI: backup, backup-list, backup-restore ✅
- **P1: Rate limiting** - slowapi: 100/min API, 10/min auth ✅
- **P2: Optimistic locking** - Version check v parts/operations/features routers (ADR-008) ✅
- **P2: Material Hierarchy** - Dvoustupňová hierarchie MaterialGroup + MaterialItem (ADR-011) ✅
- **P2: Batch Snapshot** - Minimal Snapshot pro zmrazení cen v nabídkách (ADR-012) ✅
- **P2: Health check** - GET /health (db status, version) ✅
- **P2: Graceful shutdown** - Lifespan cleanup, DB dispose, 503 during shutdown ✅
- **P2: Business validace** - Pydantic Field validace pro Part, Batch, Feature, Operation ✅
- **Testy:** 127/127 tests ✅

**P1 UZAVŘENO** ✅ - Všechny kritické požadavky splněny
**P2 Fáze 1 HOTOVO** ✅ - Optimistic Locking implementován (2026-01-24)
**P2 Fáze A HOTOVO** ✅ - Material Hierarchy implementována (2026-01-24)
**P2 Fáze B HOTOVO** ✅ - Minimal Snapshot implementován (2026-01-24)

---

## PŘÍKAZY

```bash
# Setup
python gestima.py setup

# Vytvoření admin uživatele (first-time)
python gestima.py create-admin

# Spuštění
python gestima.py run
# nebo: uvicorn app.gestima_app:app --reload

# Testy
python gestima.py test
# nebo: pytest -v -m critical

# Backup
python gestima.py backup          # Vytvoř zálohu
python gestima.py backup-list     # Seznam záloh
python gestima.py backup-restore <name>  # Obnov ze zálohy

# API docs
# http://localhost:8000/docs (Swagger)
# http://localhost:8000/redoc (ReDoc)
```

---

## REFERENCE

- **Architektura:** docs/ARCHITECTURE.md - Quick start (5 min)
- **Detailní specifikace:** docs/GESTIMA_1.0_SPEC.md - Kompletní spec
- **ADR:** docs/ADR/*.md - Architektonická rozhodnutí
- **Changelog:** CHANGELOG.md - Historie všech změn
- **API:** http://localhost:8000/docs - Swagger UI
- **Audit:** docs/audit.md - Auditní zpráva

---

**Verze dokumentu:** 2.11 (2026-01-24)
**GESTIMA verze:** 1.0.0
**Účel:** Kompletní pravidla pro efektivní AI vývoj

**Poslední změny dokumentu:**
- 2.11 (2026-01-24): Verzování - oprava inkonzistence app/doc verzí
- 2.10 (2026-01-24): P2 Fáze B uzavřeno (Minimal Snapshot ADR-012)
- ✅ Batch.is_frozen - zmrazení cen v nabídkách (immutable prices)
- ✅ Endpoints: POST /freeze, POST /clone, soft delete pro frozen batches
- ✅ snapshot_service.py - vytváření a načítání snapshotů
- ✅ Part.status ODSTRANĚN - freeze je pouze na Batch level (rozhodnutí)
- ✅ Testy: 8 nových testů pro freeze, clone, immutability, price stability
- ✅ Všechny testy: 98 passed
- ✅ P2 UZAVŘENO - všechny požadavky splněny (2026-01-24)

📋 **Kompletní historie změn:** viz [CHANGELOG.md](CHANGELOG.md)
