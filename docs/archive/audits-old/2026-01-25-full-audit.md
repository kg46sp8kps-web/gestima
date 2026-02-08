# GESTIMA v1.1.0 - KOMPLETNI AUDIT REPORT

**Datum:** 2026-01-25
**Auditor:** Roy (Claude Code)
**Verze aplikace:** 1.1.0
**Branch:** GESTIMA-v1.0

---

## OBSAH

1. [Executive Summary](#1-executive-summary)
2. [Kriticke problemy (P0)](#2-kriticke-problemy-p0)
3. [Vysoka priorita (P1)](#3-vysoka-priorita-p1)
4. [Stredni priorita (P2)](#4-stredni-priorita-p2)
5. [Nizka priorita (P3)](#5-nizka-priorita-p3)
6. [Detailni audit - Struktura projektu](#6-detailni-audit---struktura-projektu)
7. [Detailni audit - Modely a DB vrstva](#7-detailni-audit---modely-a-db-vrstva)
8. [Detailni audit - Pydantic schemata](#8-detailni-audit---pydantic-schemata)
9. [Detailni audit - Services](#9-detailni-audit---services)
10. [Detailni audit - Routery](#10-detailni-audit---routery)
11. [Detailni audit - Frontend](#11-detailni-audit---frontend)
12. [Detailni audit - Bezpecnost](#12-detailni-audit---bezpecnost)
13. [Detailni audit - Testy](#13-detailni-audit---testy)
14. [Detailni audit - Dokumentace](#14-detailni-audit---dokumentace)
15. [Detailni audit - Technicky dluh](#15-detailni-audit---technicky-dluh)
16. [Analyza modularity](#16-analyza-modularity)
17. [Co je velmi dobre](#17-co-je-velmi-dobre)
18. [Akcni plan](#18-akcni-plan)
19. [Zaver](#19-zaver)

---

## 1. EXECUTIVE SUMMARY

| Oblast | Skore | Status |
|--------|-------|--------|
| **Struktura & Architektura** | 97/100 | VYBORNE |
| **Modely & DB vrstva** | 85/100 | DOBRE (3 FK problemy) |
| **Pydantic schemata** | 70/100 | VYZADUJE POZORNOST |
| **Services** | 52/100 | ERROR HANDLING CHYBI |
| **Routery** | 75/100 | DOBRE (soft delete bug) |
| **Frontend** | 80/100 | DOBRE (1 XSS riziko) |
| **Bezpecnost** | 65/100 | KRITICKE CONFIG PROBLEMY |
| **Testy** | 60/100 | CASTECNE POKRYTI |
| **Dokumentace** | 70/100 | ZASTARALA VS REALITA |
| **Technicky dluh** | 75/100 | ZVLADNUTELNY |
| **Modularita** | 70/100 | CASTECNE MODULARNI |

**CELKOVE SKORE: 73/100** - Solidni zaklad, ale pred produkci nutne opravy

### Statistiky projektu

```
Soubory Python:     39
Soubory HTML:       8
Soubory CSS:        6
Soubory JS:         1
Test soubory:       17
Testy celkem:       138 (99.3% uspesnost)
ADR dokumenty:      10
Radky kodu:         ~8000+
```

---

## 2. KRITICKE PROBLEMY (P0)

> Blocker pro produkci - MUSI se opravit pred deploymentem

### 2.1 BEZPECNOST: Hardcoded SECRET_KEY

**Soubor:** `app/config.py:14`
```python
SECRET_KEY: str = "CHANGE_THIS_IN_PRODUCTION_VIA_ENV"
```

**Dopad:**
- Kdokoliv, kdo zna default hodnotu, muze falsifikovat JWT tokeny
- Kompletni kompromitace autentizace
- CVSS Score: 9.1 (CRITICAL)

**Proof of Concept:**
```python
jwt.encode({"sub": "admin"}, "CHANGE_THIS_IN_PRODUCTION_VIA_ENV", algorithm="HS256")
```

**Reseni:**
```python
# config.py - pridat validaci
@validator('SECRET_KEY')
def validate_secret_key(cls, v):
    if v == "CHANGE_THIS_IN_PRODUCTION_VIA_ENV":
        raise ValueError("SECRET_KEY not configured! Set via .env file.")
    if len(v) < 32:
        raise ValueError("SECRET_KEY must be at least 32 characters")
    return v
```

---

### 2.2 BEZPECNOST: DEBUG=True jako default

**Soubor:** `app/config.py:11`
```python
DEBUG: bool = True
```

**Dopad:**
- Stack traces obsahuji citlive informace (paths, env vars)
- `/docs` endpoint expose cele API schema
- Exception handler vraci detaily chyb
- CVSS Score: 7.5 (HIGH)

**Reseni:**
```python
DEBUG: bool = False  # Zmenit default
```

---

### 2.3 BUG: Sync DB operation v async kontextu

**Soubor:** `app/routers/materials_router.py:245`
```python
item.deleted_at = db.execute("SELECT CURRENT_TIMESTAMP").scalar_one()
item.deleted_by = current_user.username
```

**Dopad:**
- Soft delete selhava
- Mozne deadlocky v async kontextu
- Runtime error pri DELETE operaci

**Porovnani se spravnym kodem:**
```python
# batches_router.py:88 - SPRAVNE
batch.deleted_at = datetime.utcnow()

# materials_router.py:245 - SPATNE
item.deleted_at = db.execute("SELECT CURRENT_TIMESTAMP").scalar_one()
```

**Reseni:**
```python
from datetime import datetime
item.deleted_at = datetime.utcnow()
item.deleted_by = current_user.username
```

---

### 2.4 BEZPECNOST: Chybi Security Headers

**Soubor:** `app/gestima_app.py`

**Chybejici headers:**
- `Content-Security-Policy` (CSP)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY` (CLICKJACKING ochrana)
- `Strict-Transport-Security` (HSTS)
- `Referrer-Policy`
- `X-XSS-Protection: 1; mode=block`

**Dopad:**
- Clickjacking utoky mozne
- MIME type sniffing
- XSS utoky usnadneny
- CVSS Score: 6.1 (MEDIUM)

**Reseni:**
```python
# gestima_app.py - pridat middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

---

### 2.5 VERZOVANI: Nesynchronizovane verze

| Misto | Verze | Status |
|-------|-------|--------|
| `config.py` | 1.0.0 | ZASTARALA |
| `CHANGELOG.md` | 1.1.0 | SPRAVNE |
| `CLAUDE.md` | 1.1.0 | SPRAVNE |
| `README.md` | "GESTIMA 1.0" | ZASTARALA |
| `base.html` | v1.1.0 (hardcoded) | SPRAVNE |

**Reseni:**
1. Aktualizovat `config.py`: `VERSION = "1.1.0"`
2. Aktualizovat `README.md`: zmenit na 1.1.0
3. Idealne: Verze z `config.py` pouzivat vsude (Single Source of Truth)

---

### 2.6 GIT: Untracked soubory v produkci

```
?? app/routers/misc_router.py        # NOVY - External API router
?? app/templates/auth/               # NOVY - Auth templates
?? docs/UI_ROADMAP.md               # NOVY - UI dokumentace
?? gestima.db.backup-*              # Zalohy (melo by byt v .gitignore)
```

**Dopad:**
- `misc_router.py` se importuje v `gestima_app.py:27` ale NENI v gitu
- CI/CD pipeline selze na cistem klonu
- Ostatni vyvojari nemaji pristup k novemu kodu

**Reseni:**
```bash
git add app/routers/misc_router.py
git add app/templates/auth/
git add docs/UI_ROADMAP.md
# Backup soubory pridat do .gitignore
echo "gestima.db.backup-*" >> .gitignore
git commit -m "feat: Add misc_router, auth templates, UI roadmap"
```

---

## 3. VYSOKA PRIORITA (P1)

> Do tohoto sprintu - dulezite pro kvalitu a bezpecnost

### 3.1 Services - Chybi Error Handling

**7 z 9 services NEMA try/except pro DB operace!**

| Service | Funkce | Radek | Problem |
|---------|--------|-------|---------|
| `auth_service.py` | `authenticate_user()` | 92-141 | Zadny try/except na `db.execute()` |
| `auth_service.py` | `get_user_by_username()` | 144-161 | Zadny try/except |
| `auth_service.py` | `create_user()` | 164-223 | **KRITICKE:** `db.add()`, `db.commit()` bez try/except |
| `cutting_conditions.py` | `get_conditions()` | 11-52 | Zadny try/except |
| `reference_loader.py` | `get_machines()` | 16-53 | Zadny try/except |
| `reference_loader.py` | `get_material_groups()` | 56-88 | Zadny try/except |
| `snapshot_service.py` | `create_batch_snapshot()` | 12-66 | Zadny try/except |
| `price_calculator.py` | `calculate_material_cost_from_part()` | 32-122 | Zadny try/except |

**Priklad spatneho kodu (auth_service.py:218-220):**
```python
db.add(user)
await db.commit()
await db.refresh(user)
# ZADNY try/except!
```

**Reseni - pouzit vzor z CLAUDE.md:**
```python
try:
    db.add(entity)
    await db.commit()
except IntegrityError:
    await db.rollback()
    raise HTTPException(409, "Duplicate")
except SQLAlchemyError as e:
    await db.rollback()
    logger.error(f"DB error: {e}", exc_info=True)
    raise HTTPException(500, "Database error")
```

---

### 3.2 Modely - Chybi FK Constraints

**Soubor:** `app/models/operation.py:23`
```python
machine_id = Column(Integer, nullable=True)  # CHYBI ForeignKey!
```

**Dopad:**
- Lze ulozit ID neexistujiciho stroje
- Pri smazani stroje se neaktualizuje
- Porusuje Single Source of Truth (KRITICKE PRAVIDLO #2)

**Dalsi problemy v modelech:**

| Model | Soubor | Radek | Problem |
|-------|--------|-------|---------|
| `MachineDB` | machine.py | 15-17 | `code`, `name`, `type` bez `nullable=False` |
| `CuttingConditionDB` | cutting_condition.py | 17-26 | 7 fieldu bez `nullable=False` |
| `MaterialItem` | material.py | 51 | `stock_available` ma `nullable=True, default=0.0` (redundantni) |

**Reseni pro Operation.machine_id:**
```python
machine_id = Column(Integer, ForeignKey("machines.id", ondelete="SET NULL"), nullable=True)
```

---

### 3.3 Pydantic - Chybi Field validace

**20+ fieldu bez Field() validaci:**

**CuttingConditionBase (app/models/cutting_condition.py:31-43):**
```python
# 7 fieldu BEZ validaci:
material_group: str       # Chybi Field(..., max_length=50)
operation_type: str       # Chybi Field(..., max_length=50)
operation: str            # Chybi Field(..., max_length=50)
mode: str                 # Chybi Field(..., max_length=10)
Vc: float                 # Chybi Field(..., gt=0)
f: float                  # Chybi Field(..., gt=0)
Ap: float                 # Chybi Field(..., gt=0)
```

**MachineBase (app/models/machine.py:53-87):**
```python
# 7 fieldu BEZ validaci:
code: str                 # Chybi Field(..., max_length=50)
name: str                 # Chybi Field(..., max_length=200)
type: str                 # Chybi Field(..., max_length=50)
hourly_rate: float        # Chybi Field(..., gt=0)
setup_base_min: float     # Chybi Field(..., ge=0)
setup_per_tool_min: float # Chybi Field(..., ge=0)
priority: int             # Chybi Field(..., ge=0)
```

**StockPriceResponse (app/routers/data_router.py:27-31):**
```python
# 4 fieldy BEZ validaci:
volume_mm3: float         # Chybi Field(..., ge=0)
weight_kg: float          # Chybi Field(..., ge=0)
price_per_kg: float       # Chybi Field(..., gt=0)
cost: float               # Chybi Field(..., ge=0)
```

**BatchResponse - Chybi 6 freeze fieldu (ADR-012):**
- `is_frozen`
- `frozen_at`
- `frozen_by_id`
- `snapshot_data`
- `unit_price_frozen`
- `total_price_frozen`

**Chybejici Update schemata:**
- `CuttingConditionUpdate` - NEEXISTUJE
- `MachineUpdate` - NEEXISTUJE
- `BatchUpdate` - NEEXISTUJE

---

### 3.4 Frontend - XSS riziko v toast.innerHTML

**Soubor:** `app/static/js/gestima.js:39`
```javascript
toast.innerHTML = `
    <span style="flex: 1;">${message}</span>
    <button onclick="this.parentElement.remove()" ...>×</button>
`;
```

**Dopad:**
- Pokud `message` obsahuje HTML, bude interpretovan
- XSS utok mozny pres: `showToast('❌ <img src=x onerror="alert(1)">', 'error')`
- Aktualne vsechny zpravy jsou hardcoded, ale neni to bezpecne

**Reseni:**
```javascript
const messageSpan = document.createElement('span');
messageSpan.style.flex = '1';
messageSpan.textContent = message;  // BEZPECNE - escapuje HTML

const closeBtn = document.createElement('button');
closeBtn.textContent = '×';
closeBtn.onclick = () => toast.remove();

toast.appendChild(messageSpan);
toast.appendChild(closeBtn);
```

---

### 3.5 Frontend - Vypocty v JS (poruseni pravidla #1)

**Soubor:** `app/templates/parts/edit.html:399`
```javascript
calculateTotalTime() {
    this.totalTime = this.operations.reduce((sum, op) => sum + op.operation_time_min, 0);
}
```

**Dalsi vypocty v JS:**

| Soubor | Radek | Vypocet | Problem |
|--------|-------|---------|---------|
| edit.html | 399 | `totalTime = reduce(sum + operation_time_min)` | Agregace v JS |
| edit.html | 403 | `Math.max()` pro sekvenci | Matematicka operace |
| new.html | 233-256 | Stock price parametry | OK - deleguje na API |

**Reseni:**
```python
# Novy endpoint v operations_router.py
@router.get("/part/{part_id}/total-time")
async def get_total_time(part_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(func.sum(Operation.operation_time_min))
        .where(Operation.part_id == part_id)
    )
    total = result.scalar_one_or_none() or 0.0
    return {"total_time_min": total}
```

---

### 3.6 Routery - Chybejici response_model

**5 endpointu bez response_model:**

| Router | Radek | Endpoint | Vraci |
|--------|-------|----------|-------|
| `data_router.py` | 12-14 | `GET /machines` | `List[Dict[str, Any]]` |
| `data_router.py` | 17-19 | `GET /materials` | `List[Dict[str, Any]]` |
| `data_router.py` | 22-24 | `GET /feature-types` | `List[Dict[str, Any]]` |
| `misc_router.py` | 17-18 | `GET /fact` | `Dict[str, Any]` |
| `misc_router.py` | 61-62 | `GET /weather` | `Dict[str, Any]` |

**Dopad:**
- FastAPI nemuze automaticky validovat vracena data
- Chybi OpenAPI dokumentace
- JSON serialization neni optimalni

**Reseni:**
```python
class MachineListResponse(BaseModel):
    machines: List[MachineResponse]

@router.get("/machines", response_model=MachineListResponse)
async def get_machines():
    ...
```

---

### 3.7 Routery - Chybejici status_code na DELETE

**5 DELETE endpointu bez status_code:**

| Router | Radek | Endpoint |
|--------|-------|----------|
| `parts_router.py` | 205 | `DELETE /{part_id}` |
| `operations_router.py` | 108 | `DELETE /{operation_id}` |
| `features_router.py` | 104 | `DELETE /{feature_id}` |
| `materials_router.py` | 232 | `DELETE /items/{item_id}` |
| `batches_router.py` | 75 | `DELETE /{batch_id}` |

**Reseni:**
```python
@router.delete("/{part_id}", status_code=204)  # nebo 200
async def delete_part(...):
    ...
```

---

### 3.8 Data router - Public endpoints bez auth

**Soubor:** `app/routers/data_router.py:12-24`
```python
@router.get("/machines")
async def get_machines():
    return MACHINES.values()  # BEZ AUTENTIZACE!

@router.get("/feature-types")
async def get_feature_types():
    return FEATURE_TYPES.values()  # BEZ AUTENTIZACE!
```

**Dopad:**
- Utocnik muze zmapovat vsechny stroje a parametry bez prihlaseni
- Informacni disclosure

**Reseni:**
```python
@router.get("/machines")
async def get_machines(current_user: User = Depends(require_role([UserRole.VIEWER]))):
    return MACHINES.values()
```

---

## 4. STREDNI PRIORITA (P2)

> Pristi sprint - zlepseni kvality kodu

### 4.1 Duplikace CRUD try/except pattern

**Pattern se opakuje 5x v routerech:**
- `parts_router.py`
- `operations_router.py`
- `features_router.py`
- `materials_router.py`
- `batches_router.py`

**Reseni - vytvorit decorator:**
```python
# app/decorators.py
from functools import wraps

def db_error_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        db = kwargs.get('db')
        try:
            return await func(*args, **kwargs)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(409, "Conflict - duplicate or constraint violation")
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"DB error in {func.__name__}: {e}", exc_info=True)
            raise HTTPException(500, "Database error")
    return wrapper
```

---

### 4.2 Duplikace soft delete

**2 mista rucne nastavuji deleted_at:**

| Soubor | Radek | Kod |
|--------|-------|-----|
| `batches_router.py` | 88-89 | `batch.deleted_at = datetime.utcnow()` |
| `materials_router.py` | 245-246 | `item.deleted_at = db.execute(...)` (BUG!) |

**Reseni - pouzit soft_delete() z db_helpers:**
```python
from app.db_helpers import soft_delete

# Misto rucniho nastaveni:
await soft_delete(db, item, current_user.username)
```

---

### 4.3 Duplikace version check

**3 routery kontroluji version != data.version:**

| Soubor | Radek |
|--------|-------|
| `parts_router.py` | 131-134 |
| `batches_router.py` | ? |
| `materials_router.py` | 96-99 |

**Reseni - vytvorit check_version() helper:**
```python
# app/db_helpers.py
def check_version(entity, expected_version: int):
    if entity.version != expected_version:
        raise HTTPException(
            status_code=409,
            detail="Data byla zmenena jinym uzivatelem. Obnovte stranku."
        )
```

---

### 4.4 Cache bez invalidace

**Soubor:** `app/services/reference_loader.py:12-13`
```python
_machines_cache: List[Dict[str, Any]] = []  # Globalni cache
_materials_cache: List[Dict[str, Any]] = []

async def get_machines() -> List[Dict[str, Any]]:
    global _machines_cache
    if _machines_cache:
        return _machines_cache  # Nikdy se neinvaliduje!
    # ... nacti z DB
```

**Dopad:**
- Pokud admin edituje Material, cache bude stara
- Race condition pri concurrent cache miss

**Reseni - TTL cache:**
```python
from datetime import datetime, timedelta

_cache_expiry: datetime = None
CACHE_TTL = timedelta(minutes=5)

async def get_machines() -> List[Dict[str, Any]]:
    global _machines_cache, _cache_expiry

    if _machines_cache and _cache_expiry and datetime.utcnow() < _cache_expiry:
        return _machines_cache

    # Refresh cache
    _machines_cache = await _load_machines_from_db()
    _cache_expiry = datetime.utcnow() + CACHE_TTL
    return _machines_cache
```

---

### 4.5 Testy - Chybejici pokryti

**Celkove pokryti: 60%**

**Materials router - 0% pokryti (KRITICKE):**
- 9 endpointu bez testu
- create/update/get/delete groups & items

**GET endpointy - ~50% chybi:**
- `parts`: get_parts, search_parts, get_part, duplicate_part
- `operations`: get_operations, get_operation, create_operation, delete_operation
- `features`: get_features, get_feature, create_feature, delete_feature
- `batches`: get_batches, get_batch, create_batch

**Services bez testu:**
- `reference_loader`: get_machines, get_material_groups, get_feature_types
- `cutting_conditions`: 1 test ale SKIPPED

**Potreba: ~100 novych testu pro 70% pokryti**

---

### 4.6 Deprecated funkce

**Soubor:** `app/services/price_calculator.py:125-187`
```python
async def calculate_material_cost(
    stock_diameter: float,
    ...
) -> MaterialCost:
    """
    DEPRECATED: Pouzij calculate_material_cost_from_part() misto teto funkce.
    """
```

**Ale v data_router.py:50 se STALE POUZIVA:**
```python
result = await calculate_material_cost(
    stock_diameter=stock_diameter,
    ...
)
```

**Reseni:** Smazat deprecated funkci a migrovat data_router.py

---

### 4.7 Dokumentace - Zastarala

**NEXT-STEPS.md:**
- Referovano v CLAUDE.md a ARCHITECTURE.md
- Ale soubor NEEXISTUJE!

**localStorage neni v CLAUDE.md:**
- Rozhodnuti v CHANGELOG (v1.1.0)
- Chybi pravidlo L-012

**Chybi ADR-013:**
- localStorage persistence rozhodnuti neni dokumentovano

**ARCHITECTURE.md:**
- Nezminuje Material Hierarchy
- Nezminuje article_number
- Nezminuje parts_list.html

---

## 5. NIZKA PRIORITA (P3)

> Backlog - kod quality improvements

### 5.1 Zastaraly TODO komentar

**Soubor:** `app/database.py:19`
```python
created_by = Column(String(100), nullable=True)  # TODO: Integrate with auth
```

**Stav:** TODO je uz hotov (set_audit helper existuje), komentar je zastaraly

---

### 5.2 Zbytecny alias

**Soubor:** `app/services/reference_loader.py:8`
```python
from app.models import MaterialGroup as MaterialDB  # Zbytecny alias
```

---

### 5.3 Cache size hardcoded

**Soubor:** `app/database.py:54`
```python
f"PRAGMA cache_size = 64000"  # Melo by byt v config.py
```

---

### 5.4 Rate limit na misc endpointy

**Soubor:** `app/routers/misc_router.py`
```python
@router.get("/fact")      # BEZ RATE LIMIT
@router.get("/weather")   # BEZ RATE LIMIT
```

**Reseni:**
```python
@router.get("/fact")
@limiter.limit("10/minute")
async def get_fact():
    ...
```

---

### 5.5 Fallback hodnoty v reference_loader

**Soubor:** `app/services/reference_loader.py:82-83`
```python
"price_per_kg": 30.0,  # Fallback pro deprecated API
"color": "#999999",
```

**Reseni:** Smazat az se smaze deprecated calculate_material_cost()

---

### 5.6 Nested funkce v misc_router

**Soubor:** `app/routers/misc_router.py:91-117`
```python
def find_hour_index(time_str: str) -> int:
    ...

def get_weather_emoji(code: int) -> str:
    ...
```

**Doporuceni:** Presunout do utils.py nebo nechat (jsou lokalni)

---

## 6. DETAILNI AUDIT - STRUKTURA PROJEKTU

### 6.1 Adresarova struktura

```
GESTIMA/
├── app/                            # Hlavni aplikace
│   ├── __init__.py
│   ├── gestima_app.py              # FastAPI app + routers + global handlers
│   ├── config.py                   # Settings + environment variables
│   ├── database.py                 # SQLAlchemy setup + AuditMixin + Base
│   ├── logging_config.py           # Structured logging (JSON format)
│   ├── rate_limiter.py             # Slowapi rate limiting
│   ├── db_helpers.py               # Soft delete, restore, active_only utilities
│   ├── dependencies.py             # get_current_user, require_role
│   ├── seed_data.py                # Demo data creation
│   ├── seed_materials.py           # Material data seed script
│   │
│   ├── models/                     # SQLAlchemy + Pydantic Schemas (9 souboru)
│   │   ├── __init__.py
│   │   ├── user.py                 # User, UserRole, LoginRequest, TokenResponse
│   │   ├── part.py                 # Part + PartBase/Create/Update/Response
│   │   ├── operation.py            # Operation + schemas
│   │   ├── feature.py              # Feature + FeatureType enum + schemas
│   │   ├── batch.py                # Batch + schemas
│   │   ├── material.py             # MaterialGroup, MaterialItem + schemas
│   │   ├── machine.py              # MachineDB + schemas
│   │   ├── cutting_condition.py    # CuttingCondition + schemas
│   │   └── enums.py                # UserRole, StockShape, CuttingMode, FeatureType
│   │
│   ├── routers/                    # API endpoints (9 routeru)
│   │   ├── __init__.py
│   │   ├── auth_router.py          # POST /api/auth/login, /logout, /me
│   │   ├── parts_router.py         # CRUD /api/parts + search
│   │   ├── operations_router.py    # CRUD /api/operations
│   │   ├── features_router.py      # CRUD /api/features
│   │   ├── batches_router.py       # CRUD /api/batches
│   │   ├── materials_router.py     # GET /api/materials + groups
│   │   ├── data_router.py          # GET /api/data (reference data)
│   │   ├── misc_router.py          # GET /api/misc (weather, facts) - UNTRACKED!
│   │   └── pages_router.py         # GET / (templates)
│   │
│   ├── services/                   # Business Logic (9 souboru)
│   │   ├── __init__.py
│   │   ├── price_calculator.py     # Price calculations + material costs
│   │   ├── time_calculator.py      # Time calculations + machining times
│   │   ├── auth_service.py         # authenticate_user, create_access_token
│   │   ├── backup_service.py       # Database backup/restore
│   │   ├── snapshot_service.py     # Part snapshot management
│   │   ├── cutting_conditions.py   # CuttingCondition loading
│   │   ├── feature_definitions.py  # Feature type definitions
│   │   └── reference_loader.py     # Material, machine, condition references
│   │
│   ├── templates/                  # Jinja2 HTML (8 souboru)
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── parts_list.html
│   │   ├── parts/
│   │   │   ├── list.html           # DEAD CODE
│   │   │   ├── list_fragment.html  # DEAD CODE
│   │   │   ├── new.html
│   │   │   └── edit.html
│   │   ├── auth/
│   │   │   └── login.html          # UNTRACKED!
│   │   └── components/             # Prazdny - pro budouci komponenty
│   │
│   └── static/                     # Frontend assets
│       ├── js/
│       │   └── gestima.js          # Alpine.js + utility functions
│       ├── css/
│       │   ├── variables.css
│       │   ├── base.css
│       │   ├── layout.css
│       │   ├── components.css
│       │   ├── gestima.css
│       │   └── operations.css
│       └── img/
│           └── logo.png
│
├── docs/                           # Dokumentace (53 .md souboru)
│   ├── ARCHITECTURE.md
│   ├── GESTIMA_1.0_SPEC.md
│   ├── NEXT-STEPS.md               # NEEXISTUJE!
│   ├── TESTING.md
│   ├── UI_REFERENCE.md
│   ├── UI_ROADMAP.md               # UNTRACKED!
│   ├── VERSIONING.md
│   ├── ADR/                        # Architektonicka rozhodnuti (10 souboru)
│   │   ├── README.md
│   │   ├── 001-soft-delete-pattern.md
│   │   ├── 003-integer-id-vs-uuid.md
│   │   ├── 004-implementation-notes.md
│   │   ├── 005-authentication-authorization.md
│   │   ├── 006-role-hierarchy.md
│   │   ├── 007-https-caddy.md
│   │   ├── 008-optimistic-locking.md
│   │   ├── 011-material-hierarchy.md
│   │   └── 012-minimal-snapshot.md
│   └── archive/                    # Stare dokumenty
│
├── tests/                          # Pytest testy (17 souboru)
│   ├── conftest.py
│   └── test_*.py (14 souboru)
│
├── scripts/                        # Utility skripty
├── backups/                        # Database backupy
├── data/                           # Data archiv
│
├── gestima.py                      # CLI helper
├── requirements.txt
├── README.md
├── CLAUDE.md
├── CHANGELOG.md
├── pytest.ini
├── .env.example
└── .gitignore
```

### 6.2 Overeni architektury

| Pozadavek | Stav | Poznamka |
|-----------|------|----------|
| app/models/ | OK | 9 modelu + enums |
| app/services/ | OK | 9 service modulu |
| app/routers/ | OK | 9 routeru |
| app/templates/ | OK | 8 HTML sablon |
| app/static/css/ | OK | 6 CSS souboru |
| app/static/js/ | OK | Alpine.js + HTMX |
| docs/ADR/ | OK | 10 ADR souboru |
| tests/ | OK | 17 pytest souboru |

### 6.3 Anti-pattern check

| Anti-pattern | Status | Detail |
|--------------|--------|--------|
| L-001: Vypocty v JS | PORUSENO | edit.html:399 - totalTime agregace |
| L-002: Duplikace logiky | CASTECNE | CRUD pattern 5x, soft delete 2x |
| L-003: Ztrata UI stavu | OK | localStorage implementovano |
| L-004: Write misto Edit | OK | Pouziva Edit pro zmeny |
| L-005: Castecny UI update | OK | HTMX + Alpine.js |
| L-006: Hardcoded data | OK | Vsechna data z API |
| L-007: Chybejici audit | OK | created_by/updated_by vsude |
| L-008: Bez try/except | PORUSENO | 7/9 services bez error handling |
| L-009: Pydantic bez validaci | CASTECNE | 20+ fieldu chybi |
| L-010: Zaplatovani bugu | OK | Cisty kod |
| L-011: CSS conflicts | OK | Login ma inline override |

---

## 7. DETAILNI AUDIT - MODELY A DB VRSTVA

### 7.1 Prehled modelu

| Model | Soubor | Audit fieldy | Indexy | Vztahy |
|-------|--------|--------------|--------|--------|
| User | user.py | OK | 3 | - |
| Part | part.py | OK | 4 | operations, batches, material_item |
| Operation | operation.py | OK | 2 | part, features |
| Feature | feature.py | OK | 2 | operation |
| Batch | batch.py | OK | 4 | part, frozen_by |
| MaterialGroup | material.py | OK | 2 | items |
| MaterialItem | material.py | OK | 2 | group, parts |
| MachineDB | machine.py | OK | 2 | - |
| CuttingConditionDB | cutting_condition.py | OK | 5 | - |

### 7.2 AuditMixin fieldy (database.py:15-27)

```python
created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
created_by = Column(String(100), nullable=True)
updated_by = Column(String(100), nullable=True)
deleted_at = Column(DateTime, nullable=True)
deleted_by = Column(String(100), nullable=True)
version = Column(Integer, default=0, nullable=False)
```

### 7.3 Kriticke nalezy

**C-001: Operation.machine_id chybi FK (KRITICKE)**
- Soubor: operation.py:23
- Reseni: Pridat `ForeignKey("machines.id", ondelete="SET NULL")`

**C-002: MachineDB fieldy bez NOT NULL (VYSOKE)**
- Soubor: machine.py:15-17
- Fieldy: code, name, type
- Reseni: Pridat `nullable=False`

**C-003: CuttingConditionDB bez NOT NULL (VYSOKE)**
- Soubor: cutting_condition.py:17-26
- Fieldy: material_group, operation_type, operation, mode, Vc, f, Ap
- Reseni: Pridat `nullable=False`

**M-001: MaterialItem.stock_available redundance (STREDNI)**
- Soubor: material.py:51
- Problem: `nullable=True, default=0.0`
- Reseni: Zmenit na `nullable=False, default=0.0`

### 7.4 Vztahy a kaskady

Vsechny vztahy jsou spravne nastaveny s `back_populates` a vhodnym kaskadovanim:

| Vztah | Kaskada | Status |
|-------|---------|--------|
| Part → Operations | delete-orphan | OK |
| Part → Batches | delete-orphan | OK |
| Operation → Features | delete-orphan | OK |
| MaterialGroup → Items | delete-orphan | OK |

### 7.5 Indexy

**25 indexu celkem** na kritickych sloupcich:
- Primary keys
- Foreign keys
- Unique columns (username, email, part_number, code)
- Filter columns (material_group, operation_type)

---

## 8. DETAILNI AUDIT - PYDANTIC SCHEMATA

### 8.1 Spravne implementovane validace

```python
# Part (part.py:44-60)
part_number: str = Field(..., min_length=1, max_length=50)  # OK
material_item_id: int = Field(..., gt=0)                      # OK
length: float = Field(0.0, ge=0)                              # OK

# Operation (operation.py:46-57)
seq: int = Field(10, ge=1)                                    # OK
machine_id: Optional[int] = Field(None, gt=0)                 # OK

# Feature (feature.py:55-72)
thread_pitch: Optional[float] = Field(None, gt=0)             # OK
blade_width: float = Field(3.0, gt=0)                         # OK
count: int = Field(1, ge=1)                                   # OK

# Batch (batch.py:50-51)
quantity: int = Field(1, gt=0)                                # OK

# Material (material.py:64-100)
density: float = Field(..., gt=0)                             # OK
price_per_kg: float = Field(..., gt=0)                        # OK
```

### 8.2 Chybejici validace (20+ fieldu)

**CuttingConditionBase:**
```python
# CHYBI:
material_group: str = Field(..., max_length=50)
operation_type: str = Field(..., max_length=50)
Vc: float = Field(..., gt=0)
f: float = Field(..., gt=0)
Ap: float = Field(..., gt=0)
```

**MachineBase:**
```python
# CHYBI:
code: str = Field(..., max_length=50)
hourly_rate: float = Field(..., gt=0)
setup_base_min: float = Field(..., ge=0)
```

**LoginRequest:**
```python
# CHYBI bezpecnostni omezeni:
username: str = Field(..., min_length=3, max_length=50)
password: str = Field(..., min_length=8, max_length=100)
```

### 8.3 Chybejici schemata

- `CuttingConditionUpdate` - NEEXISTUJE
- `MachineUpdate` - NEEXISTUJE
- `BatchUpdate` - NEEXISTUJE

---

## 9. DETAILNI AUDIT - SERVICES

### 9.1 Prehled services

| Service | Error Handling | Async | Logging | Status |
|---------|----------------|-------|---------|--------|
| auth_service.py | CHYBI | OK | OK | FAIL |
| backup_service.py | OK | SYNC | OK | OK |
| cutting_conditions.py | CHYBI | OK | CHYBI | FAIL |
| feature_definitions.py | N/A | N/A | N/A | DATA |
| price_calculator.py | CHYBI | OK | OK | MEDIUM |
| reference_loader.py | CHYBI | OK | CHYBI | FAIL |
| snapshot_service.py | CHYBI | OK | CHYBI | FAIL |
| time_calculator.py | CASTECNE | OK | OK | MEDIUM |

### 9.2 Chybejici error handling

**auth_service.py:218-220 (KRITICKE):**
```python
# SPATNE - zadny try/except:
db.add(user)
await db.commit()
await db.refresh(user)
```

**Spravny vzor z CLAUDE.md:**
```python
try:
    db.add(entity)
    await db.commit()
except IntegrityError:
    await db.rollback()
    raise HTTPException(409, "Duplicate")
except SQLAlchemyError as e:
    await db.rollback()
    logger.error(f"DB error: {e}", exc_info=True)
    raise HTTPException(500, "Database error")
```

### 9.3 Cache race condition

**reference_loader.py:12-22:**
```python
_machines_cache: List[Dict[str, Any]] = []

async def get_machines() -> List[Dict[str, Any]]:
    global _machines_cache
    if _machines_cache:
        return _machines_cache
    # RACE CONDITION: 2 requesty mohou soucasne spustit DB query
```

### 9.4 Hardcoded hodnoty

| Soubor | Radek | Hodnota | Status |
|--------|-------|---------|--------|
| time_calculator.py | 54 | `Vc = ... or 150` | PROBLEM |
| time_calculator.py | 55 | `f = ... or 0.2` | PROBLEM |
| time_calculator.py | 56 | `Ap = ... or 2.0` | PROBLEM |
| time_calculator.py | 22 | `max_rpm: int = 4000` | PROBLEM |
| reference_loader.py | 82 | `price_per_kg: 30.0` | FALLBACK |

---

## 10. DETAILNI AUDIT - ROUTERY

### 10.1 Prehled routeru

| Router | Endpoints | Auth | Response models | Status |
|--------|-----------|------|-----------------|--------|
| auth_router.py | 3 | OK (rate limit) | OK | OK |
| parts_router.py | 7 | OK | OK | OK |
| operations_router.py | 6 | OK | OK | MINOR |
| features_router.py | 5 | OK | OK | OK |
| batches_router.py | 6 | OK | OK | OK |
| materials_router.py | 9 | OK | CHYBI | BUG |
| data_router.py | 4 | CHYBI | CHYBI | PROBLEM |
| misc_router.py | 2 | CHYBI | CHYBI | UNTRACKED |
| pages_router.py | 3 | OK | N/A | OK |

### 10.2 Kriticke nalezy

**L-013: Sync DB v async (materials_router.py:245):**
```python
item.deleted_at = db.execute("SELECT CURRENT_TIMESTAMP").scalar_one()
# MELO BY BYT:
item.deleted_at = datetime.utcnow()
```

**L-016: Business logika v routeru (parts_router.py:169-179):**
```python
# Generovani part_number v routeru - melo by byt v services
base_number = original.part_number
counter = 1
new_part_number = f"{base_number}-COPY-{counter}"
while True:
    check = await db.execute(...)
    ...
```

**L-020: Logging chyba (operations_router.py:96):**
```python
logger.info(f"Updated operation: {operation.type}", ...)
# Pole .type NEEXISTUJE! Spravne je .operation_type
```

### 10.3 Soft delete nekonzistence

| Router | Entita | Strategie |
|--------|--------|-----------|
| materials_router.py | MaterialItem | Soft delete (BUG) |
| batches_router.py | Batch (frozen) | Soft delete (OK) |
| parts_router.py | Part | Hard delete |
| operations_router.py | Operation | Hard delete |
| features_router.py | Feature | Hard delete |

---

## 11. DETAILNI AUDIT - FRONTEND

### 11.1 Bezpecnostni nalezy

**XSS riziko (gestima.js:39):**
```javascript
toast.innerHTML = `<span>${message}</span>`;  // NEBEZPECNE!
```

**CSRF ochrana:**
- SameSite=strict cookie - OK
- Zadne explicitni CSRF tokeny - OK (neni potreba s SameSite)

**Alpine.js x-text:**
- Automaticky escapuje HTML - OK
- Pouzivano spravne vsude

### 11.2 Poruseni pravidla #1 (Vypocty v JS)

| Soubor | Radek | Vypocet | Status |
|--------|-------|---------|--------|
| edit.html | 399 | `totalTime = reduce(...)` | PORUSENI |
| edit.html | 403 | `Math.max(...)` | PORUSENI |
| new.html | 233-256 | Stock price params | OK - API |

### 11.3 CSS L-011 check

**base.css:14,26:**
```css
body { min-width: 1200px; }
.main-content { min-width: 1200px; }
```

**login.html:11 - SPRAVNY FIX:**
```html
<body style="min-width: 0; padding: 20px; ...">
```

### 11.4 localStorage (bez try/catch)

**parts_list.html:183:**
```javascript
this.visibleColumns = JSON.parse(saved);  // BEZ try/catch!
```

### 11.5 Dead code

| Soubor | Status | Poznamka |
|--------|--------|----------|
| parts/list.html | DEAD | Starsi verze, nepouzivana |
| parts/list_fragment.html | DEAD | HTMX fragment pro starou verzi |

---

## 12. DETAILNI AUDIT - BEZPECNOST

### 12.1 OWASP Top 10

| Kategorie | Status | Poznamka |
|-----------|--------|----------|
| A01: SQL Injection | CHRANENO | SQLAlchemy ORM |
| A02: Broken Auth | CASTECNE | SECRET_KEY problem |
| A03: Broken Access Control | CASTECNE | data_router bez auth |
| A04: XSS | CHRANENO | Jinja2 autoescape, x-text |
| A05: Security Misconfiguration | PROBLEM | DEBUG=True default |
| A06: Vulnerable Components | OK | Aktualni dependencies |
| A07: CSRF | CHRANENO | SameSite=strict |
| A08: Insecure Deserialization | N/A | - |
| A09: Logging | OK | Structured JSON |
| A10: SSRF | CHRANENO | httpx s timeout |

### 12.2 JWT implementace

| Aspekt | Status | Poznamka |
|--------|--------|----------|
| Algoritmus | HS256 | Standard |
| Expirace | 30 min default | OK |
| Cookie flags | HttpOnly, SameSite=strict | OK |
| Secret key | PROBLEM | Hardcoded default |

### 12.3 Password hashing

```python
# auth_service.py - SPRAVNE
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

### 12.4 Rate limiting

| Endpoint | Limit | Status |
|----------|-------|--------|
| /api/auth/* | 10/minute | OK |
| /api/* | 100/minute | VYSOKE |
| /api/misc/* | ZADNY | PROBLEM |

### 12.5 Security headers

**CHYBI:**
- Content-Security-Policy
- X-Content-Type-Options
- X-Frame-Options
- Strict-Transport-Security
- Referrer-Policy

### 12.6 Risk Matrix

| Zranitelnost | CVSS | Severity | Priority |
|--------------|------|----------|----------|
| Hardcoded SECRET_KEY | 9.1 | CRITICAL | P0 |
| DEBUG mode enabled | 7.5 | HIGH | P0 |
| Missing security headers | 6.1 | MEDIUM | P1 |
| Public reference endpoints | 5.3 | MEDIUM | P1 |
| High rate limit | 4.5 | LOW | P2 |

---

## 13. DETAILNI AUDIT - TESTY

### 13.1 Statistiky

```
Celkem testu:     138
Uspesnych:        137 (99.3%)
Preskoceno:       1 (test_conditions.py)
Doba behu:        4.39 sekund
```

### 13.2 Pokryti po vrstvach

| Vrstva | Pokryti | Status |
|--------|---------|--------|
| Infrastructure | 95% | VYBORNE |
| Services | 60% | CASTECNE |
| Routers | 40% | NEDOSTATECNE |
| Models | 20% | SLABE |
| Frontend | 0% | N/A |

### 13.3 Testovane services

| Service | Status | Testy |
|---------|--------|-------|
| auth_service | OK | password hash, JWT, user auth |
| price_calculator | OK | material_cost (7 variant), machining_cost |
| time_calculator | OK | calc_rpm, calc_time |
| backup_service | OK | create, restore, cleanup, list |
| snapshot_service | OK | freeze, clone, price stability |
| reference_loader | CHYBI | - |
| cutting_conditions | SKIP | DB nema data |
| feature_definitions | CHYBI | - |

### 13.4 Chybejici testy (kriticke)

**Materials router - 0% pokryti:**
- create_material_group
- update_material_group
- get_material_groups
- get_material_group
- create_material_item
- update_material_item
- get_material_items
- get_material_item
- delete_material_item

**GET endpointy (~50% chybi):**
- parts: get_parts, search_parts, get_part, duplicate_part
- operations: get_operations, get_operation, create_operation, delete_operation
- features: get_features, get_feature, create_feature, delete_feature
- batches: get_batches, get_batch, create_batch

### 13.5 Kvalita testu

| Aspekt | Status |
|--------|--------|
| pytest-asyncio | OK |
| conftest fixtures | OK |
| Async/await | 99 async testu |
| Mocking | 30 testu s mock |
| Error handling | Podrobne testovan |
| Optimistic locking | Podrobne testovan |
| Role hierarchy | Podrobne testovan |

---

## 14. DETAILNI AUDIT - DOKUMENTACE

### 14.1 CLAUDE.md dodrzovani

| Pravidlo | Status | Poznamka |
|----------|--------|----------|
| Vypocty Python | PORUSENO | edit.html:399 |
| Single Source | OK | db_helpers.py |
| Edit ne Write | OK | model_dump(exclude_unset) |
| Zadne hardcoded | OK | Data z API/DB |
| Audit trail | OK | set_audit() vsude |
| Try/except | PORUSENO | 7/9 services |
| Pydantic validace | CASTECNE | 20+ fieldu chybi |

### 14.2 Verzovani

| Misto | Verze | Status |
|-------|-------|--------|
| config.py | 1.0.0 | ZASTARALA |
| CHANGELOG.md | 1.1.0 | SPRAVNE |
| CLAUDE.md | 1.1.0 | SPRAVNE |
| README.md | "1.0" | ZASTARALA |
| base.html | v1.1.0 | SPRAVNE |

### 14.3 ADR implementace

| ADR | Nazev | Status |
|-----|-------|--------|
| ADR-001 | Soft Delete | OK |
| ADR-003 | Integer ID | OK |
| ADR-005 | Auth + JWT | OK |
| ADR-006 | Role Hierarchy | OK |
| ADR-007 | HTTPS Caddy | OK |
| ADR-008 | Optimistic Locking | OK |
| ADR-011 | Material Hierarchy | OK |
| ADR-012 | Minimal Snapshot | OK |

### 14.4 Chybejici dokumentace

| Dokument | Status | Poznamka |
|----------|--------|----------|
| NEXT-STEPS.md | NEEXISTUJE | Referovano ale chybi |
| ADR-013 | CHYBI | localStorage rozhodnuti |
| localStorage v CLAUDE.md | CHYBI | Pravidlo L-012 |
| Material Hierarchy v ARCH | CHYBI | Aktualizovat |

---

## 15. DETAILNI AUDIT - TECHNICKY DLUH

### 15.1 TODO/FIXME komentare

| Soubor | Radek | Komentar | Status |
|--------|-------|----------|--------|
| database.py | 19 | `# TODO: Integrate with auth` | ZASTARALY (uz hotovo) |

### 15.2 Hardcoded hodnoty

| Soubor | Radek | Hodnota | Priorita |
|--------|-------|---------|----------|
| time_calculator.py | 54-56 | Fallback Vc, f, Ap | STREDNI |
| time_calculator.py | 22 | max_rpm: 4000 | NIZKA |
| reference_loader.py | 82-83 | Fallback price, color | NIZKA |
| database.py | 54 | cache_size: 64000 | NIZKA |
| misc_router.py | 68, 72-73 | GPS souradnice | OK (feature) |

### 15.3 Duplikovany kod

| Kategorie | Soubory | Reseni |
|-----------|---------|--------|
| CRUD try/except | 5 routeru | @db_error_handler decorator |
| Soft delete | 2 routery | soft_delete() z db_helpers |
| Version check | 3 routery | check_version() helper |
| Material cost | price_calculator.py | Smazat deprecated funkci |

### 15.4 Deprecated kod

| Soubor | Radek | Polozka | Akce |
|--------|-------|---------|------|
| price_calculator.py | 125-187 | calculate_material_cost() | SMAZAT |
| cutting_conditions.py | 80 | Komentar o smazane funkci | SMAZAT |
| reference_loader.py | 8 | MaterialDB alias | SMAZAT |

### 15.5 Dead code

| Soubor | Status |
|--------|--------|
| templates/parts/list.html | SMAZAT |
| templates/parts/list_fragment.html | SMAZAT |

---

## 16. ANALYZA MODULARITY

### 16.1 Otazka

> Je GESTIMA "modularni" a dobre pripravena na pridavani dalsich modulu?

### 16.2 Co mluvi PRO modularitu

| Aspekt | Implementace | Hodnoceni |
|--------|--------------|-----------|
| Separace vrstev | models → services → routers | VYBORNE |
| Jeden soubor = jeden model | part.py, batch.py, operation.py... | VYBORNE |
| Jeden soubor = jeden router | parts_router.py, batches_router.py... | VYBORNE |
| Services oddelene | price_calculator.py, time_calculator.py | VYBORNE |
| ADR pro rozhodnuti | 10 dokumentu | VYBORNE |
| Dependency injection | FastAPI Depends() | DOBRE |
| Spolecne utility | db_helpers.py, AuditMixin | DOBRE |

### 16.3 Co mluvi PROTI plne modularite

| Aspekt | Problem | Dopad na novy modul |
|--------|---------|---------------------|
| **Modely + Schemata v 1 souboru** | part.py obsahuje Part, PartCreate, PartUpdate, PartResponse | Pri zmene modelu velky soubor |
| **Duplikace CRUD** | Stejny try/except pattern 5x v routerech | Pridani modulu = copy-paste |
| **Chybi BaseRouter/BaseCRUD** | Kazdy router implementuje CRUD od nuly | Novy modul = 150+ radku boilerplate |
| **Business logika v routerech** | parts_router.py:169-179 generuje part_number | Tezssi testovani, duplikace |
| **Services bez jednotneho interface** | Kazdy service ma jinou strukturu | Tezssi predvidat strukturu |
| **Hardcoded zavislosti** | Services primo importuji modely | Tezssi mockovani |

### 16.4 Prakticky test: Pridani noveho modulu "Suppliers"

```
Potrebujes vytvorit:
1. app/models/supplier.py         (~80 radku) - Model + 4 Pydantic schemata
2. app/routers/supplier_router.py (~200 radku) - CRUD endpoints (copy-paste)
3. app/services/supplier_service.py (~50 radku) - Business logika
4. tests/test_supplier.py         (~100 radku) - Testy
5. Upravit __init__.py            (2 soubory)
6. Upravit gestima_app.py         (1 radek - include router)

Celkem: ~430+ radku, z toho ~150 je boilerplate (copy-paste)
```

### 16.5 Skore modularity

| Kriterium | Skore | Poznamka |
|-----------|-------|----------|
| Separace concerns | 95/100 | Vyborne |
| Snadnost pridani modulu | 60/100 | Vyzaduje copy-paste |
| Znovupouzitelnost kodu | 50/100 | Chybi abstrakce |
| Konzistence patterns | 70/100 | Castecna |
| Testovatelnost modulu | 75/100 | Dobra |
| **CELKEM** | **70/100** | **CASTECNE MODULARNI** |

### 16.6 Doporuceni pro plnou modularitu (P3 - budouci refaktoring)

**A) Oddeleni schemat od modelu:**
```
app/
├── models/
│   └── supplier.py      # Pouze SQLAlchemy model
├── schemas/
│   └── supplier.py      # Pouze Pydantic schemata
```

**B) Genericka CRUD trida:**
```python
# app/routers/base_router.py
class BaseCRUDRouter(Generic[ModelType, CreateSchema, UpdateSchema, ResponseSchema]):
    @router.post("/", response_model=ResponseSchema)
    async def create(self, data: CreateSchema, db: AsyncSession = Depends(get_db)):
        # Spolecna logika pro vsechny moduly
        ...
```

**C) Service interface:**
```python
# app/services/base_service.py
class BaseService(ABC):
    @abstractmethod
    async def create(self, db, data): ...
    @abstractmethod
    async def get(self, db, id): ...
    @abstractmethod
    async def update(self, db, id, data): ...
    @abstractmethod
    async def delete(self, db, id): ...
```

### 16.7 Verdikt

**GESTIMA je CASTECNE MODULARNI (70/100)**

> "System ma dobrou architektonickou zakladnu s jasnou separaci vrstev, ale pro skutecnou modularitu by bylo potreba abstrahovat spolecne CRUD patterns a oddelit schemata od modelu."

**Aktualni stav:**
- Pridani noveho modulu je MOZNE a STRAIGHTFORWARD
- Ale vyzaduje ~150 radku boilerplate (copy-paste)
- Riziko nekonzistence pri kopировani

**Priorita refaktoringu:** P3 (Backlog) - neni blocker, ale zlepsilo by DX

---

## 17. CO JE VELMI DOBRE

### 17.1 Architektura

- Cista separace concerns (models → services → routers)
- Single Source of Truth pattern
- Vsechny vypocty v Python (price_calculator, time_calculator)
- 9 modelu s AuditMixin
- 25 indexu na kritickych sloupcich

### 17.2 Bezpecnost (castecna)

- JWT v HttpOnly + SameSite=strict cookies
- bcrypt password hashing
- SQL Injection ochrana (SQLAlchemy ORM)
- XSS ochrana v Jinja2 (autoescape)
- RBAC (Admin >= Operator >= Viewer)
- Rate limiting na auth endpointech

### 17.3 Kvalita kodu

- Pydantic validace s Field() na vetsine mist
- Audit trail (created_by, updated_by)
- Soft delete pattern (ADR-001)
- Optimistic locking (ADR-008)
- Material Hierarchy (ADR-011)
- Batch snapshots (ADR-012)

### 17.4 Testy

- 138 testu, 99.3% uspesnost
- Async testy spravne nastavene
- Error handling podrobne testovan
- Optimistic locking testovan
- Role hierarchy testovana

### 17.5 Dokumentace

- 10 ADR souboru
- CHANGELOG aktualni
- CLAUDE.md komplexni pravidla
- 53 .md souboru celkem

---

## 18. AKCNI PLAN

### P0 - Ihned (2-3 hodiny)

| # | Ukol | Soubor | Odhad |
|---|------|--------|-------|
| 1 | Pridat SECRET_KEY validaci | config.py | 15 min |
| 2 | Zmenit DEBUG default na False | config.py | 2 min |
| 3 | Opravit soft delete bug | materials_router.py:245 | 5 min |
| 4 | Pridat security headers middleware | gestima_app.py | 20 min |
| 5 | Synchronizovat verze | config.py, README.md | 5 min |
| 6 | Git commit untracked souboru | misc_router.py, auth/, UI_ROADMAP.md | 10 min |

### P1 - Dnes (4-6 hodin)

| # | Ukol | Soubor | Odhad |
|---|------|--------|-------|
| 7 | Pridat error handling do services | 7 souboru | 2 hod |
| 8 | Opravit Operation.machine_id FK | operation.py | 15 min |
| 9 | Doplnit Field validace | cutting_condition.py, machine.py, data_router.py | 1 hod |
| 10 | Opravit toast.innerHTML | gestima.js:39 | 15 min |
| 11 | Presunout calculateTotalTime() | edit.html → operations_router.py | 30 min |
| 12 | Pridat response_model na 5 endpointu | data_router.py, misc_router.py | 30 min |
| 13 | Pridat auth na data_router endpointy | data_router.py | 15 min |

### P2 - Tento tyden

| # | Ukol | Odhad |
|---|------|-------|
| 14 | Vytvorit @db_error_handler decorator | 1 hod |
| 15 | Pridat testy pro materials_router (9 testu) | 2 hod |
| 16 | Pridat testy pro GET endpointy (~15 testu) | 3 hod |
| 17 | Implementovat cache invalidaci | 30 min |
| 18 | Vytvorit NEXT-STEPS.md | 30 min |
| 19 | Vytvorit ADR-013 (localStorage) | 20 min |
| 20 | Aktualizovat ARCHITECTURE.md | 30 min |

### P3 - Backlog

| # | Ukol |
|---|------|
| 21 | Smazat deprecated calculate_material_cost() |
| 22 | Smazat dead code (list.html, list_fragment.html) |
| 23 | Odstranit zastaraly TODO komentar |
| 24 | Presunout cache_size do config.py |
| 25 | Pridat rate limit na misc endpointy |
| 26 | Smazat zbytecny MaterialDB alias |
| 27 | **MODULARITA:** Oddelit Pydantic schemata do app/schemas/ |
| 28 | **MODULARITA:** Vytvorit BaseCRUDRouter pro genericke CRUD operace |
| 29 | **MODULARITA:** Vytvorit BaseService interface |

---

## 19. ZAVER

### Celkove hodnoceni

**SKORE: 73/100 - Solidni zaklad s potrebnymi opravami**

### Klicove metriky

| Metrika | Hodnota |
|---------|---------|
| Kritickych problemu (P0) | 6 |
| Vysokych problemu (P1) | 11 |
| Strednich problemu (P2) | 8 |
| Nizkych problemu (P3) | 9 |
| Celkem | 34 |

### Odhad prace

| Priorita | Cas |
|----------|-----|
| P0 | 2-3 hodiny |
| P1 | 4-6 hodin |
| P2 | 8-10 hodin |
| P3 | 6-10 hodin (vcetne refaktoringu modularity) |
| **Celkem** | **20-29 hodin** |

### Doporuceni

1. **Pred produkci:** Opravit vsechny P0 problemy (BLOCKER)
2. **Do tohoto sprintu:** Opravit P1 problemy (bezpecnost, kvalita)
3. **Pristi sprint:** P2 (testy, dokumentace, refaktoring)
4. **Backlog:** P3 (code quality)

### Zaverecne zhodnoceni

> "Have you tried turning it off and on again?" - Ne, tentokrat staci opravit SECRET_KEY a DEBUG.

GESTIMA ma solidni architektonicke zaklady. Hlavni problemy jsou v konfiguraci bezpecnosti a chybejicim error handlingu. Po oprave P0 a P1 bude aplikace pripravena na produkci.

---

**Audit provedl:** Roy (Claude Code)
**Datum:** 2026-01-25
**Verze reportu:** 1.0
**Dalsi planovany audit:** Po implementaci P0+P1 oprav
