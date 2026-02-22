# Backend Rules — Gestima

> Auto-načten při práci na `app/` souborech.
> Globální pravidla (workflow, architektura, git) viz root `CLAUDE.md`.

---

## Data & Architecture Principles

**Tyto principy zajišťují konzistenci dat. Porušení = kaskádové problémy.**

### 1. Single Source of Truth — výpočty POUZE na backendu

```
Backend (PRAVDA)                    Frontend (ZOBRAZENÍ)
├── price_calculator.py             ├── Zobrazí batch.unit_cost
├── material_calculator.py          ├── Zobrazí batch.material_percent
├── feature_calculator.py           ├── Zobrazí formátovanou cenu
├── batch_service.py                └── NIKDY nepočítá ceny/náklady
└── accounting_router.py
```

- **Ceny, náklady, marže, procenta** → počítá POUZE backend (services/)
- **Frontend POUZE zobrazuje** hodnoty z API response
- **Formátování ≠ výpočet** — `formatCurrency(value)` na FE je OK, `price * qty * margin` NENÍ
- **Nová odvozená hodnota** → přidej jako `@computed_field` v Pydantic nebo field v response schema
- **Duplicitní vzorec = bug** — smaž frontend verzi

### 2. Jednosměrný data flow

```
API response → Pinia store → Component → Template
     ↑                                       |
     └──── User action → Store action → API call
```

- **Komponenty NEVOLAJÍ API přímo** — vždy přes store action nebo api/ modul
- **Komponenty NEMUTUJÍ store přímo** — vždy přes store actions
- **Stores si NESLEDUJÍ navzájem** — žádný `watch(otherStore.value)` across stores
- **Props down, events up** — parent → child přes props, child → parent přes emit

### 3. Datová integrita

- **Optimistic locking na KAŽDÉM update** — `version: int` v update schema, kontrola před save
- **Soft delete VŽDY** — `soft_delete()`, nikdy `db.delete()`
- **Audit trail VŽDY** — `AuditMixin` na každém modelu, `set_audit()` na každém write
- **Validace na hranici** — Pydantic schemas validují na vstupu do API
- **Atomic operations** — `safe_commit()` zajistí rollback, žádné partial writes

### 4. Snapshot princip

- **Batch ukládá ceny v momentě výpočtu** — ne reference na aktuální sazby
- **Quote ukládá snapshot cen** — změna sazby nezmění existující nabídku
- **NIKDY automatický přepočet historických dat** — to by zfalšovalo historii

### 5. Konzistentní datové tvary

- **TypeScript typy MUSÍ odpovídat backend schemas** — `frontend/src/types/` = zrcadlo `app/schemas/`
- **Update typy VŽDY mají `version: number`** — bez výjimky
- **Nullable pole** — pokud backend posílá `null`, frontend typ musí mít `| null`
- **Přidáš pole v backendu** → přidej ho i do frontend typu a API modulu

### 6. Fail-safe chování

- **Chybějící data = prázdný stav, ne crash** — `items.value ?? []`, ne `items.value!`
- **API chyba = toast + zachování stavu** — ne bílá obrazovka
- **4 stavy každého modulu:** loading, empty, error, data — vždy řešit všechny

---

## Backend Rules

### Models — ALWAYS

1. **AuditMixin na každém modelu** — provides created_at, updated_at, created_by, updated_by, deleted_at, deleted_by, version
2. **Never hard-delete** — `soft_delete(db, instance, username)` z db_helpers
3. **Audit fields vždy** — `set_audit(instance, username)` pro create, `set_audit(instance, username, is_update=True)` pro update
4. **Optimistic locking** — každý update schema MUSÍ mít `version: int`. Zkontroluj před save.
5. **Number generation** — `NumberGenerator` se správným prefixem:
   - Parts: 10XXXXXX, Materials: 20XXXXXX, Batches: 30XXXXXX
   - BatchSets: 35XXXXXX, Quotes: 50XXXXXX, Partners: 70XXXXXX
   - WorkCenters: 80XXXXXX (sequential, not random)

### Routers — ALWAYS

1. **Auth dependency na každém endpointu:**
   - Read: `current_user: User = Depends(get_current_user)`
   - Write: `current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))`
   - Admin: `current_user: User = Depends(require_role([UserRole.ADMIN]))`
2. **`safe_commit()`** pro všechny DB writes — nikdy raw `db.commit()`
3. **Error pattern:**
   ```python
   except ValueError as e:
       raise HTTPException(status_code=400, detail=str(e))
   except HTTPException:
       raise
   except Exception as e:
       logger.error(f"Error: {e}", exc_info=True)
       raise HTTPException(status_code=500, detail="Interní chyba serveru")
   ```
4. **Pagination pattern:** `skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)`
5. **Nikdy f-strings v SQL** — vždy SQLAlchemy parameterized queries

### Schemas — ALWAYS

1. **Naming:** `XyzCreate`, `XyzUpdate`, `XyzResponse`
2. **XyzUpdate MUSÍ mít:** `version: int`
3. **XyzResponse MUSÍ mít:** `model_config = ConfigDict(from_attributes=True)`
4. **`Field()` constraints** — min_length, max_length, ge, le, pattern

### Services — ALWAYS

1. **Inherit from `BaseCrudService`** kde možné (viz base_service.py)
2. **Business logic patří do services**, ne do routerů
3. **Routery řeší pouze:** HTTP (request parsing, response formatting, status codes)

### NEVER do this (Backend)

- ❌ Hard-delete records
- ❌ Přeskočit version check na updates
- ❌ Přeskočit auth dependency na jakémkoli endpointu
- ❌ Raw SQL nebo f-strings v queries
- ❌ Return 201 pro creation (konvence je 200)
- ❌ Přidat dependency bez kontroly requirements.txt
- ❌ Model bez AuditMixin
- ❌ Swallownout generic Exception bez loggingu

---

## Backend Performance — MANDATORY

**Budgets:**
| Metrika | Limit |
|---|---|
| API response (list endpoints) | < 200ms |
| API response (detail/CRUD) | < 100ms |

**Pravidla:**
1. **Eager loading pro list endpoints** — vždy `selectinload()` nebo `joinedload()`:
   ```python
   # SPRÁVNĚ — prevents N+1
   query = select(Part).options(
       selectinload(Part.operations),
       selectinload(Part.material_inputs).joinedload(MaterialInput.price_category)
   ).where(Part.deleted_at.is_(None))

   # ŠPATNĚ — causes N+1
   query = select(Part).where(Part.deleted_at.is_(None))
   ```
2. **Pagination na VŠECH list endpointech** — `skip` + `limit`, max 500
3. **Žádné blocking operations** — vše async (`await`), žádný `time.sleep()`
4. **Index na frequently queried columns** — `deleted_at`, foreign keys, `created_at`

---

## Database Rules

1. **Migrace přes Alembic** — `alembic revision --autogenerate -m "description"`
2. **SQLite + WAL mode** — async via aiosqlite
3. **Každý query filtruje soft-deleted:** `WHERE deleted_at IS NULL`
4. **Relationships s lazy loading** — použij `selectinload()` nebo `joinedload()` explicitně
5. **Nikdy nedroppuj tabulky** — pouze přidávej sloupce nebo vytvárej nové tabulky

---

## Testing — Backend Patterns

```python
@pytest.mark.asyncio
async def test_create_xyz(client: AsyncClient, admin_headers):
    response = await client.post("/api/xyz", json={...}, headers=admin_headers)
    assert response.status_code == 200
    result = response.json()
    assert result["field"] == expected_value
```

**Kdy psát testy:**
- Nový API endpoint → router test (status codes, auth, validation)
- Nová business logika → service test (výpočty, edge cases)
- Bug fix → regression test který bug reprodukuje
- Každý endpoint: success + 401 + 403 + 400 + 404 + 409 (version) + soft_delete verification

---

## Code Quality Standards

### Import Order (Python)

```python
# 1. Standard library
import logging
from datetime import datetime
from typing import List, Optional

# 2. Third-party
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# 3. Local app
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.db_helpers import set_audit, safe_commit, soft_delete
```

### Naming Conventions

| Context | Convention | Příklad |
|---|---|---|
| Python files | snake_case | `material_parser.py` |
| Python classes | PascalCase | `MaterialInput` |
| Python functions | snake_case | `get_price_per_kg` |
| Vue components | PascalCase | `PartDetailPanel.vue` |
| Vue composables | camelCase `use` | `useDialog.ts` |
| TS types | PascalCase | `PartCreate`, `MaterialResponse` |
| TS functions | camelCase | `fetchParts()` |
| CSS classes | kebab-case | `.btn-primary`, `.panel-header` |
| CSS variables | v2 short names | `--t1`, `--b2`, `--surface`, `--red` |
| API routes | kebab-case plural | `/api/material-inputs` |
| DB tables | snake_case plural | `material_inputs` |
| data-testid | kebab-case | `create-part-button` |

### Error Handling — Complete Pattern

**Backend:**
```python
# Service layer
def validate_quantity(qty: int):
    if qty <= 0:
        raise ValueError("Množství musí být kladné číslo")

# Router layer
@router.post("/")
async def create(data: CreateSchema, db=Depends(get_db), user=Depends(get_current_user)):
    try:
        result = await service.create(db, data, user.username)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chyba: {e}", exc_info=True)
        raise HTTPException(500, "Interní chyba serveru")
```

**Frontend:**
```typescript
async function savePart(data: PartCreate) {
  ui.startLoading()
  try {
    const result = await partsApi.create(data)
    ui.showSuccess('Díl uložen')
    return result
  } catch (error) {
    if (error instanceof OptimisticLockErrorClass) {
      ui.showError('Data byla změněna jiným uživatelem. Obnovte stránku.')
    } else {
      ui.showError('Chyba při ukládání dílu')
    }
    throw error
  } finally {
    ui.stopLoading()  // VŽDY, i při chybě
  }
}
```

### Dead Code Prevention

- Smaž unused imports ihned
- Nikdy comment-out kód "for later" — použij git history
- Pokud odstraníš feature → smaž VEŠKERÝ related kód (model, router, service, schema, test, component, store, api modul, types)

### Dependency Management

- **Python:** Zkontroluj `requirements.txt` před přidáním. Pin versions.
- **Frontend:** Zkontroluj `package.json`. Ptej se uživatele před `npm install`.
- **Size budget:** Žádná nová dependency > 100KB bez explicitního souhlasu

### Accessibility Basics

- Všechny interaktivní elementy jsou focusable
- `:focus-visible` outline při keyboard navigation
- Form inputs mají labels (viditelný nebo `aria-label`)
- Barva není jediný indikátor stavu
