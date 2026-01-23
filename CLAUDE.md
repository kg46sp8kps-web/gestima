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

---

## PRODUCTION REQUIREMENTS

### P0 - BLOCKER (bez tohoto nelze nasadit)

| Požadavek | Status | Co udělat |
|-----------|--------|-----------|
| **Authentication** | ✅ HOTOVO | OAuth2 + JWT v HttpOnly Cookie (2026-01-23) |
| **Authorization** | ✅ HOTOVO | RBAC: Admin/Operator/Viewer (2026-01-23) |
| **Role Hierarchy** | ✅ HOTOVO | Admin >= Operator >= Viewer (2026-01-23, ADR-006) |
| **HTTPS** | ⚠️ OPS | TLS certifikát / reverse proxy (viz ADR-005) |
| **DEBUG=False** | ✅ HOTOVO | .env.example vytvořen (2026-01-23) |

### P1 - KRITICKÉ

| Požadavek | Status | Co udělat / Soubor |
|-----------|--------|-----------|
| **Global error handler** | ✅ HOTOVO | app/gestima_app.py (2026-01-23) |
| **Structured logging** | ✅ HOTOVO | app/logging_config.py (2026-01-23) |
| **Transaction error handling** | ✅ HOTOVO | 14 míst v routerech + db_helpers (2026-01-23) |
| **Backup strategie** | ❌ CHYBÍ | Automatický SQLite backup script |
| **Audit trail vyplňování** | ✅ HOTOVO | Vyplněno ve všech routerech (2026-01-23) |
| **CORS** | ❌ CHYBÍ | CORSMiddleware s whitelist |
| **Rate limiting** | ❌ CHYBÍ | slowapi nebo podobné |

### P2 - DŮLEŽITÉ

| Požadavek | Status | Co udělat |
|-----------|--------|-----------|
| **Business validace** | ⚠️ ČÁSTEČNĚ | Validace: quantity > 0, diameter > 0 |
| **Optimistic locking** | ⚠️ ČÁSTEČNĚ | Check version při update |
| **Health check endpoint** | ❌ CHYBÍ | GET /health |
| **Graceful shutdown** | ❌ CHYBÍ | Signal handlers |

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
- [ ] **ADR:** Upozornil jsem na architektonické rozhodnutí? (pokud relevantní)
- [ ] **TESTY:** Napsal jsem testy pro kritické změny? (automaticky!)
- [ ] **DOCS:** Aktualizoval jsem dokumentaci? (automaticky!)

---

## AKTUÁLNÍ STAV (2026-01-23)

**Co funguje:**
- CRUD pro parts, operations, features, batches
- Výpočty časů a cen (services/)
- UI s Alpine.js + HTMX
- **P0: Authentication** - OAuth2 + JWT v HttpOnly Cookie (SameSite=strict) ✅
- **P0: Authorization** - RBAC (Admin/Operator/Viewer) ✅
- **P0: Role Hierarchy** - Admin >= Operator >= Viewer (ADR-006) ✅
- **P0: DEBUG** - .env.example vytvořen ✅
- **P1: Structured logging** (app/logging_config.py) ✅
- **P1: Global error handler** (app/gestima_app.py) ✅
- **P1: Transaction error handling** (14 míst v routerech + db_helpers) ✅
- **P1: Audit trail** - set_audit() helper (eliminace L-002 duplikace) ✅
- **Testy:** 27/27 auth tests (včetně role hierarchy) ✅

**Co chybí (P0/P1):**
- **P0:** HTTPS / TLS (ops task, viz ADR-005)
- **P1:** Backup strategie
- **P1:** CORS
- **P1:** Rate limiting

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

# API docs
# http://localhost:8000/docs (Swagger)
# http://localhost:8000/redoc (ReDoc)
```

---

## REFERENCE

- **Architektura:** docs/ARCHITECTURE.md - Quick start (5 min)
- **Detailní specifikace:** docs/GESTIMA_1.0_SPEC.md - Kompletní spec
- **ADR:** docs/ADR/*.md - Architektonická rozhodnutí
- **API:** http://localhost:8000/docs - Swagger UI

---

**Verze:** 2.2 (2026-01-23)
**Účel:** Kompletní pravidla pro efektivní AI vývoj

**Changelog 2.2:**
- ✅ P0-2: Role Hierarchy implementováno (Admin >= Operator >= Viewer)
- ✅ Přidáno pravidlo #7: Role Hierarchy (RBAC)
- ✅ 9 nových testů pro role hierarchy (27/27 passed)
- ✅ Vytvořen ADR-006-role-hierarchy.md

**Changelog 2.1:**
- ✅ Aktualizován status P1 requirements (error handling + logging HOTOVO)
- ✅ Přidán workflow krok "Po implementaci - AUTOMATICKY!"
- ✅ Rozšířen checklist o testy + dokumentaci
- ✅ Aktualizován AKTUÁLNÍ STAV
- ✅ Vytvořen docs/ARCHITECTURE.md (224 řádků, kompaktní přehled)
